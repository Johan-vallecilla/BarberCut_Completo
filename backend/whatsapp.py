# ══════════════════════════════════════════════════════
#  whatsapp.py — Notificaciones via WhatsApp Business Cloud API (Meta)
#
#  API GRATUITA: Meta ofrece 1,000 conversaciones gratis al mes.
#  Más que suficiente para una barbería.
#
#  Cómo obtener credenciales (gratis):
#  1. Ve a https://developers.facebook.com y crea una app de tipo "Business"
#  2. Agrega el producto "WhatsApp" a tu app
#  3. En WhatsApp > Configuración de API encontrarás:
#       - WHATSAPP_TOKEN       → "Token de acceso temporal" (o permanente con Meta Business)
#       - WHATSAPP_PHONE_ID    → "ID de número de teléfono"
#  4. Para producción, verifica tu empresa en Meta Business Manager
#
#  Requiere en .env:
#    WHATSAPP_TOKEN=EAAxxxxxxxxxxxxxxx
#    WHATSAPP_PHONE_ID=1234567890123456
#    WHATSAPP_COUNTRY_CODE=57              (código país, Colombia por defecto)
# ══════════════════════════════════════════════════════

import os
import logging
import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

WHATSAPP_TOKEN        = os.getenv("WHATSAPP_TOKEN", "")
WHATSAPP_PHONE_ID     = os.getenv("WHATSAPP_PHONE_ID", "")
WHATSAPP_COUNTRY_CODE = os.getenv("WHATSAPP_COUNTRY_CODE", "57")  # Colombia por defecto

_whatsapp_disponible = bool(WHATSAPP_TOKEN and WHATSAPP_PHONE_ID)

# URL base de la Cloud API de Meta (versión estable)
_API_URL = "https://graph.facebook.com/v19.0/{phone_id}/messages"


def _formatear_numero(telefono: str) -> str:
    """
    Convierte un número local (ej: 3001234567) al formato E.164 sin el '+'.
    La Cloud API de Meta espera el número sin '+' pero con código de país.
    Si ya viene con '+' se elimina.
    """
    telefono = telefono.strip()
    if telefono.startswith("+"):
        return telefono[1:]  # Quitar el '+'
    return f"{WHATSAPP_COUNTRY_CODE}{telefono}"


def enviar_whatsapp_cancelacion(
    telefono: str,
    nombre_cliente: str,
    barbero: str,
    fecha: str,
    hora: str,
    servicio: str,
) -> bool:
    """
    Envía un mensaje de WhatsApp al cliente avisando que el barbero canceló su cita.

    Retorna True si el envío fue exitoso, False en caso contrario.
    Si la API no está configurada, imprime el mensaje en consola (modo dev).
    """
    mensaje = (
        f"Hola {nombre_cliente} 👋, te informamos que tu cita en *BarberCut* ha sido *CANCELADA* por el barbero.\n\n"
        f"📅 *Fecha:* {fecha}\n"
        f"🕐 *Hora:* {hora}\n"
        f"✂️ *Servicio:* {servicio} con {barbero}\n\n"
        "Puedes reservar una nueva cita en nuestra página. ¡Disculpa el inconveniente! 🙏"
    )

    if not _whatsapp_disponible:
        # Modo desarrollo: solo loguear
        logger.warning(
            "[WhatsApp — modo dev, API no configurada]\n"
            f"  Para: {telefono}\n"
            f"  Mensaje: {mensaje}"
        )
        print(
            f"\n{'='*55}\n"
            f"  💬 WhatsApp (simulado — configura la API para envío real)\n"
            f"  Para: {telefono}\n"
            f"  {mensaje}\n"
            f"{'='*55}\n"
        )
        return True  # En dev lo tratamos como exitoso

    try:
        numero_destino = _formatear_numero(telefono)
        url = _API_URL.format(phone_id=WHATSAPP_PHONE_ID)

        headers = {
            "Authorization": f"Bearer {WHATSAPP_TOKEN}",
            "Content-Type": "application/json",
        }

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": numero_destino,
            "type": "text",
            "text": {
                "preview_url": False,
                "body": mensaje,
            },
        }

        response = requests.post(url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()

        data = response.json()
        message_id = data.get("messages", [{}])[0].get("id", "N/A")

        logger.info(f"[WhatsApp] Enviado a {numero_destino} — ID: {message_id}")
        print(f"[BarberCut] 💬 WhatsApp enviado a +{numero_destino} (ID: {message_id})")
        return True

    except requests.exceptions.HTTPError as e:
        error_detail = ""
        try:
            error_detail = e.response.json().get("error", {}).get("message", "")
        except Exception:
            pass
        logger.error(f"[WhatsApp] Error HTTP al enviar a {telefono}: {e} — {error_detail}")
        print(f"[BarberCut] ⚠️  Error enviando WhatsApp a {telefono}: {e} — {error_detail}")
        return False

    except Exception as e:
        logger.error(f"[WhatsApp] Error al enviar a {telefono}: {e}")
        print(f"[BarberCut] ⚠️  Error enviando WhatsApp a {telefono}: {e}")
        return False

def enviar_whatsapp_nueva_reserva(
    nombre_cliente: str,
    barbero: str,
    fecha: str,
    hora: str,
    servicio: str,
    telefono_cliente: str,
) -> bool:
    """
    Envía un WhatsApp al admin avisando que hay una nueva reserva.
    """
    admin_tel = os.getenv("WHATSAPP_ADMIN", "")
    
    if not admin_tel:
        logger.warning("[WhatsApp] WHATSAPP_ADMIN no configurado en .env")
        return False

    mensaje = (
        f"🔔 *Nueva reserva en BarberCut*\n\n"
        f"👤 *Cliente:* {nombre_cliente}\n"
        f"📱 *Teléfono:* {telefono_cliente}\n"
        f"✂️ *Servicio:* {servicio}\n"
        f"💈 *Barbero:* {barbero}\n"
        f"📅 *Fecha:* {fecha}\n"
        f"🕐 *Hora:* {hora}\n\n"
        "Entra al dashboard para ver todos los detalles."
    )

    if not _whatsapp_disponible:
        print(f"\n{'='*55}\n💬 WhatsApp admin (simulado)\n{mensaje}\n{'='*55}\n")
        return True

    try:
        numero_destino = _formatear_numero(admin_tel)
        url = _API_URL.format(phone_id=WHATSAPP_PHONE_ID)

        headers = {
            "Authorization": f"Bearer {WHATSAPP_TOKEN}",
            "Content-Type": "application/json",
        }

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": numero_destino,
            "type": "text",
            "text": {
                "preview_url": False,
                "body": mensaje,
            },
        }

        response = requests.post(url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()

        data = response.json()
        message_id = data.get("messages", [{}])[0].get("id", "N/A")
        print(f"[BarberCut] 🔔 WhatsApp admin enviado (ID: {message_id})")
        return True

    except Exception as e:
        logger.error(f"[WhatsApp] Error notificando al admin: {e}")
        return False