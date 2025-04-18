# api/_notificador_privado.py
# IMPORTANTE: Este archivo NO debe subirse a Git. Añadir a .gitignore

import os
import requests
import logging # Usaremos logging para errores

# Configurar un logger básico (si main.py no lo hubiera configurado ya)
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Carga las variables de entorno (asumiendo que main.py ya llamó a load_dotenv)
# Si ejecutas esto de forma aislada, necesitarías llamar a load_dotenv() aquí.
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def enviar_notificacion(mensaje="SVG LyricFrame Cargado"):
    """
    Intenta enviar un mensaje a Telegram si las credenciales están configuradas.
    """
    # Verificar si las credenciales necesarias están presentes
    if not TELEGRAM_BOT_TOKEN:
        # No logueamos error si falta el token, simplemente no podemos notificar.
        # Podríamos loguear un debug o info la primera vez si quisiéramos.
        # logging.info("TELEGRAM_BOT_TOKEN no configurado. No se enviará notificación.")
        return
    if not TELEGRAM_CHAT_ID:
        # logging.info("TELEGRAM_CHAT_ID no configurado. No se enviará notificación.")
        return

    # Construir la URL de la API de Telegram para enviar mensajes
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    # Preparar los datos (payload) para el mensaje
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,  # El ID del chat donde se enviará el mensaje
        "text": mensaje,              # El contenido del mensaje
        "disable_notification": True, # Opcional: True para envío silencioso, False para notificación normal
        "parse_mode": "HTML"          # Opcional: Permite usar tags HTML básicos como <b>, <i>
    }

    try:
        # Realizar la petición POST a la API de Telegram
        # Usar un timeout corto (ej. 3-5 segundos) para no bloquear la respuesta del SVG
        respuesta = requests.post(url, data=payload, timeout=5)

        # Verificar si la API de Telegram devolvió un error (ej. 400, 401, 404)
        respuesta.raise_for_status()

        # Loguear éxito (opcional, puede ser muy verboso)
        # logging.info(f"Notificación enviada a Telegram (Chat ID: {TELEGRAM_CHAT_ID})")

    # Manejar errores específicos de la librería requests
    except requests.exceptions.Timeout:
        logging.warning(f"Timeout al enviar notificación a Telegram (Chat ID: {TELEGRAM_CHAT_ID}).")
    except requests.exceptions.HTTPError as e:
        # Error devuelto por la API de Telegram (ej: chat_id inválido, token inválido)
        logging.error(f"Error HTTP de API Telegram: {e.response.status_code} - {e.response.text}")
    except requests.exceptions.RequestException as e:
        # Otros errores de red/conexión
        logging.error(f"Error de red al enviar notificación a Telegram: {e}")
    # Capturar cualquier otro error inesperado
    except Exception as e:
        logging.error(f"Error inesperado en enviar_notificacion: {e}")

# --- Fin de la función ---

# Puedes añadir una pequeña prueba aquí si quieres ejecutar este archivo directamente
# if __name__ == '__main__':
#     print("Probando enviar_notificacion...")
#     # Necesitarías cargar .env aquí si pruebas de forma aislada
#     # from dotenv import load_dotenv
#     # dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
#     # load_dotenv(dotenv_path=dotenv_path)
#     # TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") # Recargar después de load_dotenv
#     # TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
#     enviar_notificacion("Mensaje de prueba desde _notificador_privado.py")
#     print("Prueba finalizada.")