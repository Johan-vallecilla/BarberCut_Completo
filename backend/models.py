# ══════════════════════════════════════════════════════
#  models.py — Modelos ORM (tablas en MySQL)
# ══════════════════════════════════════════════════════

from sqlalchemy import Column, Integer, String, Boolean, Date, DateTime, Enum as SAEnum, func
from database import Base


class Barbero(Base):
    __tablename__ = "barberos"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    nombre       = Column(String(100), nullable=False)
    especialidad = Column(String(100), default="")
    telefono     = Column(String(15),  default="")
    activo       = Column(Boolean,     default=True)
    creado_en    = Column(DateTime,    default=func.now())


class Reserva(Base):
    __tablename__ = "reservas"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    nombre        = Column(String(100), nullable=False)
    telefono      = Column(String(15),  nullable=False)
    barbero       = Column(String(100), nullable=False)
    servicio      = Column(String(100), nullable=False)
    precio        = Column(Integer,     default=0)
    fecha         = Column(Date,        nullable=False)
    hora          = Column(String(5),   nullable=False)
    estado        = Column(SAEnum("confirmada", "pendiente", "cancelada"), default="confirmada")
    registrado_en = Column(DateTime,    default=func.now())