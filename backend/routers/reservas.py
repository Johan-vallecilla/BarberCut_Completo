# ══════════════════════════════════════════════════════
#  routers/reservas.py — Rutas de reservas
#  Cliente (públicas) + Admin (protegidas)
#
#  Reglas de cancelación:
#  - Cliente: solo puede cancelar con mínimo 1 hora de anticipación
#  - Admin:   puede cancelar en cualquier momento
#  - Al cancelar desde admin, se notifica al cliente por WhatsApp
# ══════════════════════════════════════════════════════

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from datetime import datetime, date, timedelta

from database import get_db
from models import Reserva
from schemas import ReservaSchema
from excel import registrar_reserva_excel, actualizar_estado_excel
from routers.barberos import admin_requerido
from whatsapp import enviar_whatsapp_cancelacion, enviar_whatsapp_nueva_reserva

router = APIRouter()

# ── Precios de servicios ───────────────────────────────

PRECIOS = {
    "Corte clásico":    15000,
    "Corte + Fade":     25000,
    "Arreglo de barba": 12000,
    "Corte + Barba":    30000,
}

# ── Límite de cancelación para clientes ───────────────
MINUTOS_LIMITE_CANCELACION = 60   # El cliente no puede cancelar con menos de 60 min de anticipación

# ══════════════════════════════════════════════════════
#  RUTAS — CLIENTE (públicas)
# ══════════════════════════════════════════════════════

@router.get("/api/horas-ocupadas", tags=["Cliente"])
async def api_horas_ocupadas(barbero: str, fecha: str, db: Session = Depends(get_db)):
    if not barbero or not fecha:
        raise HTTPException(status_code=400, detail="barbero y fecha son requeridos.")
    try:
        return {"ok": True, "ocupadas": _horas_ocupadas(barbero, fecha, db)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/reservar", status_code=201, tags=["Cliente"])
async def reservar_api(reserva: ReservaSchema, db: Session = Depends(get_db)):
    if not _verificar_disponibilidad(reserva.barbero, reserva.fecha, reserva.hora, db):
        raise HTTPException(
            status_code=409,
            detail=f"{reserva.barbero} ya tiene cita el {reserva.fecha} a las {reserva.hora}. Elige otro horario."
        )
    try:
        nueva = _guardar_reserva(reserva, db)
        print(f"[BarberCut] Reserva #{nueva['id']} — {reserva.nombre} con {reserva.barbero} el {reserva.fecha} a las {reserva.hora}")
        registrar_reserva_excel(nueva)
        enviar_whatsapp_nueva_reserva(
            nombre_cliente   = reserva.nombre,
            barbero          = reserva.barbero,
            fecha            = reserva.fecha,
            hora             = reserva.hora,
            servicio         = reserva.servicio,
            telefono_cliente = reserva.telefono,
        )
        return {"ok": True, "mensaje": "Reserva confirmada.", "id": nueva["id"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/miscita", tags=["Cliente"])
async def api_miscita(telefono: str, db: Session = Depends(get_db)):
    if not telefono or not telefono.isdigit():
        raise HTTPException(status_code=400, detail="Teléfono inválido.")
    try:
        return {"ok": True, "reservas": _buscar_reservas_cliente(telefono, db)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/cancelar-cliente/{reserva_id}", tags=["Cliente"])
async def cancelar_cliente(reserva_id: int, db: Session = Depends(get_db)):
    """
    El cliente cancela su propia cita.
    Solo se permite con mínimo 1 hora de anticipación.
    """
    reserva = db.query(Reserva).filter(
        Reserva.id == reserva_id,
        Reserva.estado != "cancelada"
    ).first()

    if not reserva:
        raise HTTPException(status_code=404, detail="Reserva no encontrada.")

    error = _verificar_tiempo_cancelacion(reserva)
    if error:
        raise HTTPException(status_code=400, detail=error)

    try:
        reserva.estado = "cancelada"
        db.commit()
        actualizar_estado_excel(reserva_id, "cancelada")
        print(f"[BarberCut] Reserva #{reserva_id} cancelada por el cliente.")
        return {"ok": True, "mensaje": "Cita cancelada correctamente."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ══════════════════════════════════════════════════════
#  RUTAS — ADMIN (protegidas)
# ══════════════════════════════════════════════════════

@router.get("/api/reservas", tags=["Admin"])
async def api_reservas(
    db: Session = Depends(get_db),
    token: str = Depends(admin_requerido),
):
    try:
        reservas = _leer_reservas(db)
        return {"ok": True, "reservas": reservas, "total": len(reservas)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/cancelar/{reserva_id}", tags=["Admin"])
async def cancelar_admin(
    reserva_id: int,
    db: Session = Depends(get_db),
    token: str = Depends(admin_requerido),
):
    """
    El barbero/admin cancela una cita.
    - Sin restricción de tiempo — el admin puede cancelar cuando sea necesario.
    - Se envía WhatsApp al cliente notificando la cancelación.
    """
    reserva = db.query(Reserva).filter(
        Reserva.id == reserva_id,
        Reserva.estado != "cancelada"
    ).first()

    if not reserva:
        raise HTTPException(status_code=404, detail="Reserva no encontrada.")

    try:
        datos_reserva = _to_dict(reserva)

        reserva.estado = "cancelada"
        db.commit()
        actualizar_estado_excel(reserva_id, "cancelada")
        print(f"[BarberCut] Reserva #{reserva_id} cancelada por el admin/barbero.")

        # Notificar al cliente por WhatsApp
        enviar_whatsapp_cancelacion(
            telefono       = datos_reserva["telefono"],
            nombre_cliente = datos_reserva["nombre"],
            barbero        = datos_reserva["barbero"],
            fecha          = datos_reserva["fecha"],
            hora           = datos_reserva["hora"],
            servicio       = datos_reserva["servicio"],
        )

        return {"ok": True, "mensaje": "Cita cancelada y cliente notificado por WhatsApp."}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ══════════════════════════════════════════════════════
#  OPERACIONES — base de datos
# ══════════════════════════════════════════════════════

def _leer_reservas(db: Session) -> list[dict]:
    reservas = (
        db.query(Reserva)
        .order_by(Reserva.fecha.desc(), Reserva.hora.asc())
        .all()
    )
    return [_to_dict(r) for r in reservas]


def _guardar_reserva(datos: ReservaSchema, db: Session) -> dict:
    precio = PRECIOS.get(datos.servicio, 0)
    nueva = Reserva(
        nombre   = datos.nombre,
        telefono = datos.telefono,
        barbero  = datos.barbero,
        servicio = datos.servicio,
        precio   = precio,
        fecha    = datetime.strptime(datos.fecha, "%Y-%m-%d").date(),
        hora     = datos.hora,
        estado   = "confirmada",
    )
    db.add(nueva)
    db.commit()
    db.refresh(nueva)
    return _to_dict(nueva)


def _verificar_tiempo_cancelacion(reserva: Reserva):
    """
    Verifica que la cancelación del cliente se haga con al menos
    MINUTOS_LIMITE_CANCELACION minutos de anticipación.

    Retorna:
        None — Cancelación permitida
        str  — Mensaje de error si NO se puede cancelar
    """
    try:
        hora_parts = reserva.hora.split(":")
        hora_cita  = int(hora_parts[0])
        min_cita   = int(hora_parts[1]) if len(hora_parts) > 1 else 0

        fecha_cita = reserva.fecha if isinstance(reserva.fecha, date) else \
                     datetime.strptime(str(reserva.fecha), "%Y-%m-%d").date()

        dt_cita   = datetime(fecha_cita.year, fecha_cita.month, fecha_cita.day, hora_cita, min_cita)
        dt_ahora  = datetime.now()
        dt_limite = dt_cita - timedelta(minutes=MINUTOS_LIMITE_CANCELACION)

        if dt_ahora >= dt_limite:
            minutos_restantes = int((dt_cita - dt_ahora).total_seconds() / 60)

            if minutos_restantes <= 0:
                return "No se puede cancelar: la cita ya pasó o está ocurriendo ahora."

            return (
                f"Solo puedes cancelar con al menos {MINUTOS_LIMITE_CANCELACION} minutos de anticipación. "
                f"Faltan solo {minutos_restantes} minuto(s) para tu cita."
            )
    except Exception:
        pass

    return None  # Cancelación permitida


def _verificar_disponibilidad(barbero: str, fecha: str, hora: str,
                               db: Session, excluir_id: int = None) -> bool:
    q = db.query(Reserva).filter(
        Reserva.barbero == barbero,
        Reserva.fecha   == datetime.strptime(fecha, "%Y-%m-%d").date(),
        Reserva.hora    == hora,
        Reserva.estado.in_(["confirmada", "pendiente"])
    )
    if excluir_id:
        q = q.filter(Reserva.id != excluir_id)
    return q.first() is None


def _horas_ocupadas(barbero: str, fecha: str, db: Session) -> list[str]:
    resultados = db.query(Reserva.hora).filter(
        Reserva.barbero == barbero,
        Reserva.fecha   == datetime.strptime(fecha, "%Y-%m-%d").date(),
        Reserva.estado.in_(["confirmada", "pendiente"])
    ).all()
    return [r.hora for r in resultados]


def _buscar_reservas_cliente(telefono: str, db: Session) -> list[dict]:
    reservas = db.query(Reserva).filter(
        Reserva.telefono == telefono,
        Reserva.estado.in_(["confirmada", "pendiente"])
    ).order_by(Reserva.fecha.asc(), Reserva.hora.asc()).all()
    return [
        {
            "id":       r.id,
            "nombre":   r.nombre,
            "barbero":  r.barbero,
            "servicio": r.servicio,
            "fecha":    str(r.fecha),
            "hora":     r.hora,
            "estado":   r.estado,
        }
        for r in reservas
    ]


def _to_dict(r: Reserva) -> dict:
    return {
        "id":       r.id,
        "nombre":   r.nombre,
        "telefono": r.telefono,
        "barbero":  r.barbero,
        "servicio": r.servicio,
        "precio":   r.precio,
        "fecha":    str(r.fecha),
        "hora":     r.hora,
        "estado":   r.estado,
    }
