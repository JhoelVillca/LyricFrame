# api/spotify_cliente.py
import os
import requests
import base64
import logging
import time # Para manejar reintentos o cache de token simple
import random # Para elegir una canción aleatoria de las recientes

# URLs de la API de Spotify
URL_TOKEN_SPOTIFY = "https://accounts.spotify.com/api/token"
URL_AHORA_ESCUCHANDO = "https://api.spotify.com/v1/me/player/currently-playing"
# Cerca de las otras URLs en spotify_cliente.py
URL_RECIENTE = "https://api.spotify.com/v1/me/player/recently-played" # <-- URL OFICIAL # Pedimos solo el último

# Cargar credenciales desde el entorno (main.py ya debería haber llamado a load_dotenv)
CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SECRET_ID = os.getenv("SPOTIFY_SECRET_ID")
REFRESH_TOKEN = os.getenv("SPOTIFY_REFRESH_TOKEN")

# --- Gestión del Token de Acceso ---
# Guardaremos el token y cuándo expira para reutilizarlo
_token_cache = {
    "token": None,
    "expira_en": 0 # Usaremos time.time() para comparar
}

def _codificar_credenciales_base64():
    """Codifica el Client ID y Secret ID en Base64 para la autenticación."""
    if not CLIENT_ID or not SECRET_ID:
        logging.error("SPOTIFY_CLIENT_ID o SPOTIFY_SECRET_ID no están configurados.")
        return None
    auth_str = f"{CLIENT_ID}:{SECRET_ID}"
    auth_bytes = auth_str.encode('utf-8')
    auth_base64 = base64.b64encode(auth_bytes).decode('utf-8')
    return auth_base64

def _refrescar_token_acceso():
    """Obtiene un nuevo token de acceso usando el refresh token."""
    logging.info("Refrescando token de acceso de Spotify...")
    auth_base64 = _codificar_credenciales_base64()
    if not auth_base64 or not REFRESH_TOKEN:
        logging.error("Faltan credenciales para refrescar el token (ID, Secret o Refresh Token).")
        _token_cache["token"] = None # Invalidar token si falla
        _token_cache["expira_en"] = 0
        return False

    payload = {
        'grant_type': 'refresh_token',
        'refresh_token': REFRESH_TOKEN,
    }
    headers = {
        'Authorization': f'Basic {auth_base64}',
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    try:
        response = requests.post(URL_TOKEN_SPOTIFY, data=payload, headers=headers, timeout=10)
        response.raise_for_status() # Lanza excepción si hay error HTTP

        data = response.json()
        nuevo_token = data.get('access_token')
        # Spotify devuelve 'expires_in' en segundos
        segundos_expiracion = data.get('expires_in', 3600) # Por defecto 1 hora

        if not nuevo_token:
            logging.error("No se recibió access_token en la respuesta de refresco.")
            return False

        _token_cache["token"] = nuevo_token
        # Guardamos el tiempo UNIX futuro en el que expirará (con un margen)
        _token_cache["expira_en"] = time.time() + segundos_expiracion - 60 # Margen de 1 minuto
        logging.info("Token de acceso de Spotify refrescado exitosamente.")
        return True

    except requests.exceptions.RequestException as e:
        logging.error(f"Error de red al refrescar token de Spotify: {e}")
        _token_cache["token"] = None
        _token_cache["expira_en"] = 0
        return False
    except Exception as e:
        logging.error(f"Error inesperado al procesar respuesta de refresco de token: {e}")
        _token_cache["token"] = None
        _token_cache["expira_en"] = 0
        return False


def _obtener_token_valido():
    """Devuelve un token de acceso válido, refrescándolo si es necesario."""
    ahora = time.time()
    # Si no hay token o ya expiró (o está por expirar), refrescamos
    if not _token_cache["token"] or ahora >= _token_cache["expira_en"]:
        if not _refrescar_token_acceso():
            # Si el refresco falla, no podemos continuar
            return None
    return _token_cache["token"]

def _llamar_api_spotify(url_endpoint):
    """Realiza una llamada GET autenticada a un endpoint de la API de Spotify."""
    token = _obtener_token_valido()
    if not token:
        logging.error(f"No se pudo obtener un token válido para llamar a {url_endpoint}")
        return None, 503 # Simular Service Unavailable si no hay token

    headers = {'Authorization': f'Bearer {token}'}

    try:
        response = requests.get(url_endpoint, headers=headers, timeout=10)

        # Caso especial: Token expiró justo antes de la llamada (aunque _obtener_token_valido intentó prevenirlo)
        if response.status_code == 401:
            logging.warning("Recibido 401 (Unauthorized), intentando refrescar token y reintentar...")
            token_refrescado = _refrescar_token_acceso()
            if token_refrescado:
                # Reintentar la llamada con el nuevo token
                token = _token_cache["token"] # Asegurarse de usar el token actualizado
                headers = {'Authorization': f'Bearer {token}'}
                response = requests.get(url_endpoint, headers=headers, timeout=10)
            else:
                logging.error("Fallo al refrescar token después de un 401.")
                return None, 401 # Devolver el 401 original si el refresco falla

        # Manejar otros códigos de estado
        if response.status_code == 204:
            logging.info(f"Recibido 204 (No Content) de {url_endpoint}")
            return None, 204 # Indicar que no hay contenido

        response.raise_for_status() # Lanza excepción para otros errores HTTP (4xx, 5xx)

        # Si todo fue bien (200 OK)
        return response.json(), 200

    except requests.exceptions.Timeout:
        logging.error(f"Timeout al llamar a la API de Spotify: {url_endpoint}")
        return None, 504 # Gateway Timeout
    except requests.exceptions.RequestException as e:
        logging.error(f"Error de red al llamar a API Spotify ({url_endpoint}): {e}")
        # Podríamos devolver el código de estado si está disponible en 'e.response'
        status_code = e.response.status_code if hasattr(e, 'response') and e.response is not None else 500
        return None, status_code
    except Exception as e:
        logging.error(f"Error inesperado procesando respuesta de {url_endpoint}: {e}")
        return None, 500 # Internal Server Error


def _parsear_datos_cancion(item, esta_reproduciendo=True):
    """Extrae y estructura la información relevante de un item/track de Spotify."""
    if not item:
        return None

    try:
        nombre_cancion = item.get('name')
        album = item.get('album', {})
        nombre_album = album.get('name')
        # Escoger la imagen de tamaño medio (índice 1 si existe, si no la más grande o pequeña)
        imagenes = album.get('images', [])
        url_imagen = None
        if len(imagenes) > 1:
            url_imagen = imagenes[1].get('url') # Índice 1 suele ser 300x300
        elif len(imagenes) == 1:
            url_imagen = imagenes[0].get('url') # La única que haya

        # Artista(s) - tomar el primero
        artistas = item.get('artists', [])
        nombre_artista = artistas[0].get('name') if artistas else None
        url_artista_spotify = artistas[0].get('external_urls', {}).get('spotify') if artistas else None

        url_cancion_spotify = item.get('external_urls', {}).get('spotify')

        return {
            "nombre_cancion": nombre_cancion,
            "nombre_artista": nombre_artista,
            "nombre_album": nombre_album,
            "url_album_art": url_imagen,
            "url_cancion_spotify": url_cancion_spotify,
            "url_artista_spotify": url_artista_spotify,
            "esta_reproduciendo": esta_reproduciendo
        }
    except Exception as e:
        logging.error(f"Error al parsear datos de la canción: {item}. Error: {e}")
        return None

def obtener_info_cancion():
    """
    Obtiene la información de la canción actual. Si no hay, obtiene
    una canción aleatoria de las últimas reproducidas recientemente.
    Devuelve un diccionario con los datos o None si falla.
    """
    logging.info("Intentando obtener canción actual...")
    datos_actual, status_actual = _llamar_api_spotify(URL_AHORA_ESCUCHANDO)

    # Si la llamada fue exitosa (200) y está reproduciendo un track válido
    if status_actual == 200 and datos_actual and datos_actual.get('item') and datos_actual.get('is_playing') and datos_actual.get('item', {}).get('type') == 'track':
        info_cancion = _parsear_datos_cancion(datos_actual['item'], esta_reproduciendo=True)
        if info_cancion:
            logging.info(f"Canción actual encontrada: {info_cancion['nombre_cancion']}")
            return info_cancion
        else:
            logging.warning("Recibido estado 'is_playing' pero no se pudo parsear 'item' como track.")

    # --- Si no hay canción reproduciéndose, buscar Aleatoria de Recientes ---
    logging.info("No hay canción reproduciéndose activamente. Buscando Aleatoria de 'Recientes'...")
    try:
        # Pedimos hasta 20 canciones recientes (puedes ajustar el limit)
        params = {'limit': 20}
        url_reciente_con_params = f"{URL_RECIENTE}?{requests.compat.urlencode(params)}"
        datos_reciente, status_reciente = _llamar_api_spotify(url_reciente_con_params)

        if status_reciente == 200 and datos_reciente and datos_reciente.get('items'):
            # Filtrar solo los items que tienen un 'track' válido
            items_validos = [item.get('track') for item in datos_reciente['items'] if item.get('track')]
            if items_validos:
                # Elegir una al azar de las válidas
                item_aleatorio = random.choice(items_validos)
                info_cancion = _parsear_datos_cancion(item_aleatorio, esta_reproduciendo=False)
                if info_cancion:
                    logging.info(f"Canción aleatoria reciente encontrada: {info_cancion['nombre_cancion']}")
                    return info_cancion
                else:
                    logging.warning("Se eligió item reciente aleatorio pero no se pudo parsear.")
            else:
                logging.warning("No se encontraron 'tracks' válidos en la respuesta de recientes.")
        elif status_reciente != 200:
            logging.error(f"Fallo al obtener canciones recientes (Status: {status_reciente})")

    except Exception as e:
        logging.exception(f"Error inesperado al obtener/procesar canción reciente aleatoria: {e}")

    # Si todo falla
    logging.warning("No se pudo obtener información de canción actual ni reciente aleatoria.")
    return None

# Pequeña prueba si se ejecuta el módulo directamente (opcional)
if __name__ == '__main__':
    print("Probando obtener_info_cancion()... (Asegúrate que .env está en la raíz)")
    # Necesitamos cargar .env si ejecutamos esto directamente
    from dotenv import load_dotenv
    # Asumiendo que .env está en el directorio padre si ejecutamos desde api/
    dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    print(f"Buscando .env en: {dotenv_path}")
    load_dotenv(dotenv_path=dotenv_path)
    # Re-leer credenciales después de load_dotenv
    CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
    SECRET_ID = os.getenv("SPOTIFY_SECRET_ID")
    REFRESH_TOKEN = os.getenv("SPOTIFY_REFRESH_TOKEN")

    info = obtener_info_cancion()
    if info:
        print("Información obtenida:")
        import json
        print(json.dumps(info, indent=2, ensure_ascii=False))
    else:
        print("No se pudo obtener información.")