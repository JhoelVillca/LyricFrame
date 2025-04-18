# main.py
import os
from flask import Flask, Response, request
from dotenv import load_dotenv
import logging
from datetime import datetime

# --- Carga de Variables de Entorno ---
# Es crucial hacerlo antes de importar módulos que las usen
load_dotenv()

# --- Importar nuestros módulos ---
# Ahora usamos las funciones que hemos creado
from api import spotify_cliente
from api import generador_svg

# --- Configuración de Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Configuración de la Aplicación Flask ---
# Le indicamos a Flask dónde buscar las plantillas (importante!)
app = Flask(__name__, template_folder='api/plantillas')


@app.route('/')
def generar_svg_spotify():
    """
    Ruta principal que genera y devuelve el SVG de estado de Spotify.
    """
    logging.info("Solicitud recibida en la ruta /")

    # --- 1. Obtener parámetros de personalización ---
    # Usamos .get con valores por defecto si no se proporcionan en la URL
    color_fondo = request.args.get('color_fondo', '181414') # Ejemplo: /?color_fondo=0d1117
    color_borde = request.args.get('color_borde', '181414') # Ejemplo: /?color_borde=ffffff
    logging.info(f"Parámetros recibidos - color_fondo: {color_fondo}, color_borde: {color_borde}")

    # --- 2. Obtener datos de Spotify ---
    # Llamamos a la función principal de nuestro cliente Spotify
    try:
        datos_cancion = spotify_cliente.obtener_info_cancion()
        # Log sólo si tenemos datos para no ser muy verboso
        if datos_cancion:
            logging.info(f"Datos de canción obtenidos: {datos_cancion.get('nombre_cancion', 'N/A')}")
        else:
            logging.info("No se obtuvieron datos válidos de canción de Spotify.")
    except Exception as e:
        # Captura general por si algo inesperado ocurre en el cliente
        logging.exception("Error inesperado al obtener datos de Spotify.")
        datos_cancion = None # Asegurarse que es None si falla

    # --- 3. Generar el SVG ---
    svg_content = None
    if datos_cancion:
        # Si tenemos datos, llamamos al generador de SVG
        try:
            svg_content = generador_svg.crear_svg(datos_cancion, color_fondo, color_borde)
            if not svg_content:
                 logging.error("generador_svg.crear_svg devolvió None a pesar de tener datos.")
        except Exception as e:
             logging.exception("Error inesperado al generar SVG principal.")
             svg_content = None # Fallback al SVG de error/offline

    if not svg_content:
        # Si falló la generación o no había datos de Spotify, crear SVG offline/error
        logging.warning("Generando SVG offline o de error.")
        # (Puedes personalizar este SVG como quieras)
        svg_content = f"""
        <svg width="350" height="140" xmlns="http://www.w3.org/2000/svg">
            <style>.text {{ fill:#cccccc; font-family: system-ui, sans-serif; font-size: 16px; }}</style>
            <rect width="100%" height="100%" rx="8" ry="8" fill="#{color_fondo}" stroke="#{color_borde}" stroke-width="1"/>
            <text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle" class="text">
                Spotify Offline
            </text>
        </svg>
        """

    # --- 4. Intentar enviar notificación (si el módulo privado existe) ---
    # (Esta parte se mantiene como la planeamos)
    try:
        from api import _notificador_privado
        mensaje_notificacion = f"LyricFrame SVG cargado ({request.remote_addr}) - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        _notificador_privado.enviar_notificacion(mensaje_notificacion)
    except ImportError:
        # Silencioso si _notificador_privado.py no existe
        pass
    except Exception as e:
        logging.error(f"Error al intentar usar el notificador privado: {e}")

    # --- 5. Crear y devolver la respuesta SVG ---
    resp = Response(svg_content, mimetype='image/svg+xml')
    # Configurar caché: importante para rendimiento y evitar rate limits
    # s-maxage: para proxies/CDNs (ej Vercel). max-age: para navegador.
    # stale-while-revalidate: permite mostrar versión cacheada mientras se revalida.
    # Valores cortos para reflejar cambios rápido (ej. 60s / 30s / 10s)
    resp.headers['Cache-Control'] = 'public, s-maxage=60, max-age=30, stale-while-revalidate=10'
    logging.info("Respuesta SVG generada y enviada.")

    return resp

# --- Punto de Entrada para Ejecución Local ---
if __name__ == '__main__':
    # Leer el puerto de la variable de entorno PORT, útil para Heroku/Docker, default a 5000
    puerto = int(os.getenv('PORT', 5000))
    # debug=True es útil para desarrollo (recarga automática), pero inseguro en producción
    # host='0.0.0.0' escucha en todas las interfaces de red locales
    app.run(host='0.0.0.0', port=puerto, debug=True)