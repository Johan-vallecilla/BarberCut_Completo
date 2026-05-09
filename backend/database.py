# ══════════════════════════════════════════════════════
#  database.py — Conexión y configuración de SQLAlchemy
# ══════════════════════════════════════════════════════

import os
import pymysql
from urllib.parse import quote_plus

# Carga automática del archivo .env en desarrollo
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv no instalado — usar variables del sistema
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from typing import Generator

# ── URL de conexión ────────────────────────────────────

def get_database_url() -> str:
    host     = os.environ.get("DB_HOST",  "localhost")
    port     = os.environ.get("DB_PORT",  "3306")
    user     = os.environ.get("DB_USER",  "root")
    password = quote_plus(os.environ.get("DB_PASSWORD", ""))
    db_name  = os.environ.get("DB_NAME",  "barbercut")
    return f"mysql+pymysql://{user}:{password}@{host}:{port}/{db_name}?charset=utf8mb4"

# ── Base y sesión (se inicializan en startup) ──────────

Base = declarative_base()
engine = None
SessionLocal = None

# ── Dependency FastAPI ─────────────────────────────────

def get_db() -> Generator[Session, None, None]:
    """Abre una sesión por request y la cierra al terminar."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ── Inicialización ─────────────────────────────────────

def inicializar_db():
    """
    1. Crea la base de datos MySQL si no existe.
    2. Crea las tablas con SQLAlchemy.
    """
    global engine, SessionLocal

    host     = os.environ.get("DB_HOST",  "localhost")
    port     = int(os.environ.get("DB_PORT", "3306"))
    user     = os.environ.get("DB_USER",  "root")
    password = os.environ.get("DB_PASSWORD", "")
    db_name  = os.environ.get("DB_NAME",  "barbercut")

    # Crear la BD si no existe
    conn = pymysql.connect(host=host, port=port, user=user,
                           password=password, charset="utf8mb4")
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"CREATE DATABASE IF NOT EXISTS `{db_name}` "
                f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
        conn.commit()
    finally:
        conn.close()

    # Crear engine y tablas
    engine = create_engine(
        get_database_url(),
        pool_pre_ping=True,
        pool_recycle=3600,
        echo=False
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # Importar modelos para que Base los registre antes de create_all
    from models import Barbero, Reserva  # noqa: F401
    Base.metadata.create_all(bind=engine)

    print("[BarberCut] ✅ Base de datos MySQL + SQLAlchemy lista.")