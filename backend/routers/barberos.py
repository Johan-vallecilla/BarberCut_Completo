# ══════════════════════════════════════════════════════
#  routers/barberos.py — Rutas de barberos + autenticación
# ══════════════════════════════════════════════════════

from fastapi import APIRouter, HTTPException, Depends, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
import secrets
from datetime import datetime

from database import get_db
from models import Barbero
from schemas import LoginSchema, BarberoSchema
from excel import registrar_barbero_excel

router = APIRouter()

# ── Sesiones en memoria ────────────────────────────────
import os
ADMIN_USER = os.environ.get("ADMIN_USER") or "admin"
ADMIN_PASS = os.environ.get("ADMIN_PASS")

if not ADMIN_PASS:
    import warnings
    warnings.warn(
        "ADMIN_PASS no está definida en las variables de entorno. "
        "Define ADMIN_PASS en tu archivo .env antes de hacer deploy.",
        stacklevel=2,
    )
    ADMIN_PASS = "CAMBIA_ESTO"  # fuerza cambio — login fallará si no se configura

sesiones_activas: set[str] = set()

# ══════════════════════════════════════════════════════
#  AUTENTICACIÓN
# ══════════════════════════════════════════════════════

async def admin_requerido(request: Request) -> str:
    """Dependency que protege las rutas de admin."""
    token = request.cookies.get("session_token")
    if not token or token not in sesiones_activas:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autorizado. Inicia sesión primero."
        )
    return token


@router.post("/admin/login", tags=["Auth"])
async def login(datos: LoginSchema):
    if datos.usuario.strip() == ADMIN_USER and datos.password == ADMIN_PASS:
        token = secrets.token_hex(32)
        sesiones_activas.add(token)
        print(f"[BarberCut] 🔐 Login — {datetime.now().strftime('%H:%M:%S')}")
        response = JSONResponse(content={"ok": True})
        response.set_cookie(key="session_token", value=token, httponly=True, samesite="lax")
        return response
    raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos.")


@router.post("/admin/logout", tags=["Auth"])
async def logout(request: Request):
    token = request.cookies.get("session_token")
    sesiones_activas.discard(token)
    response = JSONResponse(content={"ok": True})
    response.delete_cookie("session_token")
    return response


@router.get("/api/sesion", tags=["Auth"])
async def check_sesion(request: Request):
    token = request.cookies.get("session_token")
    return {"activo": bool(token and token in sesiones_activas)}

# ══════════════════════════════════════════════════════
#  RUTAS — CLIENTE (pública)
# ══════════════════════════════════════════════════════

@router.get("/api/barberos-publico", tags=["Cliente"])
async def barberos_publico(db: Session = Depends(get_db)):
    try:
        return {"ok": True, "barberos": _leer_barberos(db)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ══════════════════════════════════════════════════════
#  RUTAS — ADMIN (protegidas)
# ══════════════════════════════════════════════════════

@router.get("/api/barberos", tags=["Admin"])
async def api_barberos_get(db: Session = Depends(get_db), token: str = Depends(admin_requerido)):
    try:
        return {"ok": True, "barberos": _leer_barberos(db)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/barberos", status_code=201, tags=["Admin"])
async def api_barberos_post(datos: BarberoSchema,
                            db: Session = Depends(get_db),
                            token: str = Depends(admin_requerido)):
    if not datos.nombre or not datos.nombre.strip():
        raise HTTPException(status_code=400, detail="El nombre del barbero es requerido.")
    try:
        nuevo = _agregar_barbero(datos, db)
        print(f"[BarberCut] ✂️  Barbero agregado: {datos.nombre}")
        registrar_barbero_excel(nuevo)
        return {"ok": True, "id": nuevo["id"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/api/barberos/{barbero_id}", tags=["Admin"])
async def api_barberos_delete(barbero_id: int,
                              db: Session = Depends(get_db),
                              token: str = Depends(admin_requerido)):
    try:
        if _eliminar_barbero(barbero_id, db):
            return {"ok": True}
        raise HTTPException(status_code=404, detail="Barbero no encontrado.")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ══════════════════════════════════════════════════════
#  OPERACIONES — base de datos
# ══════════════════════════════════════════════════════

def _leer_barberos(db: Session) -> list[dict]:
    barberos = (
        db.query(Barbero)
        .filter(Barbero.activo == True)
        .order_by(Barbero.nombre)
        .all()
    )
    return [_to_dict(b) for b in barberos]


def _agregar_barbero(datos: BarberoSchema, db: Session) -> dict:
    nuevo = Barbero(
        nombre       = datos.nombre.strip(),
        especialidad = datos.especialidad or "",
        telefono     = datos.telefono or "",
    )
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return _to_dict(nuevo)


def _eliminar_barbero(barbero_id: int, db: Session) -> bool:
    barbero = db.query(Barbero).filter(Barbero.id == barbero_id).first()
    if not barbero:
        return False
    barbero.activo = False
    db.commit()
    return True


def _to_dict(b: Barbero) -> dict:
    return {
        "id": b.id, "nombre": b.nombre,
        "especialidad": b.especialidad, "telefono": b.telefono,
    }