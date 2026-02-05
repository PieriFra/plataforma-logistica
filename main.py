from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy import (
    create_engine, Column, Integer, String, Float, ForeignKey
)
from sqlalchemy.orm import sessionmaker, declarative_base

# --------------------------------
# CONFIGURACIÓN GENERAL
# --------------------------------

app = FastAPI(title="Plataforma Logística MVP")

DATABASE_URL = "sqlite:///./database.db"

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

Base = declarative_base()

COMMISSION_PERCENTAGE = 0.10  # 10%

# --------------------------------
# MODELOS (BASE DE DATOS)
# --------------------------------

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String)
    company_name = Column(String)
    cuit = Column(String)

class Trip(Base):
    __tablename__ = "trips"

    id = Column(Integer, primary_key=True)
    creator_user_id = Column(Integer, ForeignKey("users.id"))
    origin = Column(String)
    destination = Column(String)
    load_type = Column(String)
    max_price = Column(Float)
    status = Column(String, default="published")

class Offer(Base):
    __tablename__ = "offers"

    id = Column(Integer, primary_key=True)
    trip_id = Column(Integer, ForeignKey("trips.id"))
    transporter_user_id = Column(Integer, ForeignKey("users.id"))
    price = Column(Float)
    status = Column(String, default="pending")

class Commission(Base):
    __tablename__ = "commissions"

    id = Column(Integer, primary_key=True)
    trip_id = Column(Integer, ForeignKey("trips.id"))
    transporter_user_id = Column(Integer, ForeignKey("users.id"))
    final_price = Column(Float)
    commission_amount = Column(Float)
    status = Column(String, default="pending")

# Crear tablas
Base.metadata.create_all(engine)

# --------------------------------
# ESQUEMAS (ENTRADA / SALIDA API)
# --------------------------------

class UserCreate(BaseModel):
    email: str
    company_name: str
    cuit: str

class TripCreate(BaseModel):
    origin: str
    destination: str
    load_type: str
    max_price: float

class OfferCreate(BaseModel):
    price: float

# --------------------------------
# ENDPOINTS
# --------------------------------

@app.post("/users")
def create_user(user: UserCreate):
    new_user = User(
        email=user.email,
        company_name=user.company_name,
        cuit=user.cuit
    )
    db.add(new_user)
    db.commit()
    return {"message": "Usuario creado", "user_id": new_user.id}

@app.post("/trips")
def create_trip(trip: TripCreate):
    new_trip = Trip(
        creator_user_id=1,  # dador fijo por ahora
        origin=trip.origin,
        destination=trip.destination,
        load_type=trip.load_type,
        max_price=trip.max_price,
        status="published"
    )
    db.add(new_trip)
    db.commit()
    return {"message": "Viaje creado", "trip_id": new_trip.id}

@app.get("/trips")
def list_trips():
    return db.query(Trip).all()

@app.post("/trips/{trip_id}/offer")
def create_offer(trip_id: int, offer: OfferCreate):
    trip = db.query(Trip).filter(Trip.id == trip_id).first()

    if not trip:
        raise HTTPException(status_code=404, detail="Viaje no encontrado")

    if trip.status != "published":
        raise HTTPException(status_code=400, detail="El viaje no acepta ofertas")

    new_offer = Offer(
        trip_id=trip_id,
        transporter_user_id=2,  # transportista fijo
        price=offer.price,
        status="pending"
    )

    trip.status = "offer_received"

    db.add(new_offer)
    db.commit()
    return {
        "message": "Oferta creada",
        "offer_id": new_offer.id,
        "price": new_offer.price
    }

@app.post("/offers/{offer_id}/accept")
def accept_offer(offer_id: int):
    offer = db.query(Offer).filter(Offer.id == offer_id).first()

    if not offer:
        raise HTTPException(status_code=404, detail="Oferta no encontrada")

    if offer.status != "pending":
        raise HTTPException(status_code=400, detail="Oferta inválida")

    trip = db.query(Trip).filter(Trip.id == offer.trip_id).first()

    # Aceptar oferta y cerrar viaje
    offer.status = "accepted"
    trip.status = "accepted"

    # Calcular comisión
    commission_value = offer.price * COMMISSION_PERCENTAGE

    commission = Commission(
        trip_id=trip.id,
        transporter_user_id=offer.transporter_user_id,
        final_price=offer.price,
        commission_amount=commission_value,
        status="pending"
    )

    db.add(commission)
    db.commit()

    return {
        "message": "Oferta aceptada y comisión generada",
        "trip_id": trip.id,
        "precio_final": offer.price,
        "comision": commission_value
    }

@app.get("/commissions")
def list_commissions():
    return db.query(Commission).all()