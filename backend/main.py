# ══════════════════════════════════════════════════════
#  main.py — Punto de entrada de la aplicación
#
#  Ejecutar:
#    cd barbercut/backend
#    uvicorn main:app --reload --port 8000
#
#  Docs automáticas: http://localhost:8000/docs
# ══════════════════════════════════════════════════════

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from database import inicializar_db
from excel import inicializar_excel
from routers import reservas, barberos

# ── Validación de entorno ──────────────────────────────

def _validar_variables_entorno():
    """Advierte si faltan variables de entorno críticas."""
    requeridas = ["DB_PASSWORD", "ADMIN_USER", "ADMIN_PASS"]
    faltantes = [v for v in requeridas if not os.environ.get(v)]
    if faltantes:
        print("=" * 52)
        print("  ⚠️  ADVERTENCIA: variables de entorno no definidas:")
        for v in faltantes:
            print(f"     - {v}")
        print("  Copia .env.example a .env y configura los valores.")
        print("=" * 52)

# ── Lifespan (reemplaza el deprecado @app.on_event) ────

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    _validar_variables_entorno()
    inicializar_db()
    inicializar_excel()
    print("=" * 52)
    print("  BarberCut — FastAPI + SQLAlchemy + MySQL")
    print("  Cliente:  http://localhost:8000")
    print("  Reservas: http://localhost:8000/reservar")
    print("  Admin:    http://localhost:8000/admin/login")
    print("  Docs API: http://localhost:8000/docs")
    print("=" * 52)
    yield
    # Shutdown (aquí va limpieza de recursos si se necesita)

# ── App ────────────────────────────────────────────────

app = FastAPI(
    title="BarberCut API",
    description="Backend para la plataforma de reservas BarberCut",
    version="3.0.0",
    lifespan=lifespan,
)

# ── CORS ───────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Archivos estáticos (frontend) ──────────────────────

FRONTEND = os.path.join(os.path.dirname(__file__), "..", "frontend")

if os.path.exists(os.path.join(FRONTEND, "css")):
    app.mount("/css", StaticFiles(directory=os.path.join(FRONTEND, "css")), name="css")
if os.path.exists(os.path.join(FRONTEND, "js")):
    app.mount("/js",  StaticFiles(directory=os.path.join(FRONTEND, "js")),  name="js")

# ── Routers ────────────────────────────────────────────

app.include_router(reservas.router)
app.include_router(barberos.router)

# ══════════════════════════════════════════════════════
#  RUTAS — PÁGINAS HTML
# ══════════════════════════════════════════════════════

def html(nombre: str) -> str:
    return os.path.join(FRONTEND, nombre)

@app.get("/", tags=["Páginas"])
async def index():
    return FileResponse(html("index.html"))

@app.get("/reservar", tags=["Páginas"])
async def reservar():
    return FileResponse(html("reservar.html"))

@app.get("/miscita", tags=["Páginas"])
async def miscita():
    # La funcionalidad de "Mi cita" está integrada en reservar.html
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/reservar#micita-anchor", status_code=301)

@app.get("/admin/login", tags=["Páginas"])
async def login_page():
    return FileResponse(html("login.html"))

@app.get("/admin/dashboard", tags=["Páginas"])
async def dashboard():
    return FileResponse(html("dashboard.html"))

# ══════════════════════════════════════════════════════
#  ARRANQUE
# ══════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)