# ══════════════════════════════════════════════════════
#  schemas.py — Validación de datos con Pydantic
# ══════════════════════════════════════════════════════

from pydantic import BaseModel, field_validator
from datetime import datetime
from typing import Optional


class LoginSchema(BaseModel):
    usuario: str
    password: str


class ReservaSchema(BaseModel):
    nombre:   str
    telefono: str
    barbero:  str
    servicio: str
    fecha:    str
    hora:     str

    @field_validator("nombre")
    @classmethod
    def nombre_valido(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("El nombre es obligatorio.")
        if not all(c.isalpha() or c.isspace() for c in v):
            raise ValueError("El nombre solo debe contener letras.")
        return v

    @field_validator("telefono")
    @classmethod
    def telefono_valido(cls, v: str) -> str:
        v = v.strip()
        if not v.isdigit() or not (7 <= len(v) <= 10):
            raise ValueError("El teléfono debe tener entre 7 y 10 dígitos.")
        return v

    @field_validator("barbero", "servicio", "hora")
    @classmethod
    def campo_requerido(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Este campo es obligatorio.")
        return v.strip()

    @field_validator("fecha")
    @classmethod
    def fecha_no_pasada(cls, v: str) -> str:
        try:
            fecha = datetime.strptime(v, "%Y-%m-%d").date()
            if fecha < datetime.now().date():
                raise ValueError("La fecha no puede ser en el pasado.")
        except ValueError as e:
            raise e
        return v


class BarberoSchema(BaseModel):
    nombre:       str
    especialidad: Optional[str] = ""
    telefono:     Optional[str] = ""