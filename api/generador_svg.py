# api/generador_svg.py
import os
import requests
import base64
import logging
import random
from io import BytesIO
from colorthief import ColorThief
from flask import render_template # Usaremos el renderizador de plantillas de Flask
import math 

# --- Constantes ---
# Un placeholder simple en Base64 (SVG de 1x1 pixel transparente) - Puedes mejorarlo si quieres
#PLACEHOLDER_IMAGEN_B64 = "data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"
# Opcional: Usar el placeholder largo del proyecto original si lo prefieres
PLACEHOLDER_IMAGEN_B64_ORIGINAL = "data:image/png;base64,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"

NUM_BARRAS_EQ = 84 # Número de barras en el ecualizador visual

def _obtener_y_codificar_imagen_base64(url_imagen):
    """
    Descarga una imagen desde una URL y la codifica en Base64.
    Devuelve la cadena Base64 (con prefijo data:image) y los bytes crudos de la imagen.
    Usa un placeholder si falla o no hay URL.
    """
    if not url_imagen:
        logging.warning("No se proporcionó URL de imagen. Usando placeholder.")
        return PLACEHOLDER_IMAGEN_B64, None

    try:
        respuesta = requests.get(url_imagen, timeout=5)
        respuesta.raise_for_status() # Verificar si hubo errores HTTP

        contenido_bytes = respuesta.content
        tipo_mime = respuesta.headers.get('Content-Type', 'image/jpeg') # Default a jpeg si no se especifica
        imagen_base64 = base64.b64encode(contenido_bytes).decode('utf-8')

        logging.info(f"Imagen descargada y codificada desde: {url_imagen}")
        # Retornar con el prefijo data URI correcto
        return f"data:{tipo_mime};base64,{imagen_base64}", contenido_bytes

    except requests.exceptions.Timeout:
        logging.error(f"Timeout al descargar imagen: {url_imagen}")
        return PLACEHOLDER_IMAGEN_B64, None
    except requests.exceptions.RequestException as e:
        logging.error(f"Error al descargar imagen {url_imagen}: {e}")
        return PLACEHOLDER_IMAGEN_B64, None
    except Exception as e:
        logging.error(f"Error inesperado procesando imagen {url_imagen}: {e}")
        return PLACEHOLDER_IMAGEN_B64, None


def _extraer_paleta_colores(contenido_imagen_bytes, num_colores=4):
    """
    Extrae una paleta de colores de los bytes de una imagen usando ColorThief.
    Devuelve una lista de tuplas RGB o una paleta por defecto si falla.
    """
    # Paleta por defecto (grises) en caso de fallo
    paleta_defecto = [(80, 80, 80), (120, 120, 120), (160, 160, 160), (200, 200, 200)]

    if not contenido_imagen_bytes:
        logging.warning("No hay contenido de imagen para extraer colores. Usando paleta por defecto.")
        return paleta_defecto

    try:
        color_thief = ColorThief(BytesIO(contenido_imagen_bytes))
        # Obtener la paleta (lista de tuplas RGB)
        paleta = color_thief.get_palette(color_count=num_colores)
        logging.info(f"Paleta de colores extraída: {paleta}")
        return paleta
    except Exception as e:
        # ColorThief puede fallar con imágenes corruptas o formatos raros
        logging.error(f"Error al extraer paleta de colores con ColorThief: {e}")
        return paleta_defecto
    
def _mezclar_con_blanco(rgb_color, factor_blanco=0.15):
    """
    Mezcla un color RGB con blanco.
    factor_blanco = 0.0 -> color original
    factor_blanco = 1.0 -> blanco puro
    Asegura que los valores no excedan 255.
    """
    r, g, b = rgb_color
    # Fórmula simple de interpolación lineal hacia el blanco (255, 255, 255)
    nuevo_r = int(r + (255 - r) * factor_blanco)
    nuevo_g = int(g + (255 - g) * factor_blanco)
    nuevo_b = int(b + (255 - b) * factor_blanco)
    # Asegurarse de no pasar de 255
    return (min(255, nuevo_r), min(255, nuevo_g), min(255, nuevo_b))

def _hex_a_rgb(hex_color):
    """Convierte un color hexadecimal (#RRGGBB) a una tupla RGB (r, g, b)."""
    hex_color = hex_color.lstrip('#')
    if len(hex_color) != 6:
        return None # O devolver un color por defecto como (0, 0, 0)
    try:
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    except ValueError:
        return None # Error en conversión

def _es_color_claro(rgb_color, umbral=130):
    """
    Determina si un color RGB es percibido como 'claro' u 'oscuro'.
    Usa una fórmula de luminancia simple (ponderada).
    Compara contra un umbral (valores mayores ~ más claro).
    """
    if not rgb_color:
        return False # Asumir oscuro si no hay color

    r, g, b = rgb_color
    # Fórmula de brillo ponderado (común y simple)
    # Los valores 0.299, 0.587, 0.114 son estándar
    brillo = 0.299 * r + 0.587 * g + 0.114 * b

    # Alternativa: Fórmula de luminancia relativa WCAG (más precisa pero compleja)
    # def srgb_a_lineal(c):
    #     c = c / 255.0
    #     return c / 12.92 if c <= 0.03928 else math.pow((c + 0.055) / 1.055, 2.4)
    # L = 0.2126 * srgb_a_lineal(r) + 0.7152 * srgb_a_lineal(g) + 0.0722 * srgb_a_lineal(b)
    # brillo = L * 255 # Escalar para comparar con umbral ~130, aunque el umbral WCAG es ~0.179 en escala 0-1

    logging.debug(f"Color RGB: {rgb_color}, Brillo calculado: {brillo}, Umbral: {umbral}")
    return brillo > umbral

# Reemplazar en api/generador_svg.py

# Asegúrate de tener estas importaciones al inicio del archivo si no están ya:
# import logging
# from flask import render_template
# Y las funciones helper _hex_a_rgb y _es_color_claro definidas en el mismo archivo

def crear_svg(info_cancion, color_fondo_param="181414", color_borde_param="181414"):
    """
    Función principal para generar el contenido SVG final.
    Toma la información de la canción y los parámetros de color.
    Calcula dinámicamente el color del texto para contraste.
    Devuelve el string del SVG renderizado.
    """
    if not info_cancion:
         logging.error("crear_svg recibió info_cancion como None.")
         return None # O generar SVG de error aquí

    logging.info(f"Generando SVG para: {info_cancion.get('nombre_cancion', 'Desconocido')}")

    # 1. Obtener y codificar imagen
    imagen_base64, contenido_bytes = _obtener_y_codificar_imagen_base64(info_cancion.get('url_album_art'))

    # 2. Extraer colores
    paleta_colores_rgb = [] # Inicializar
    if contenido_bytes:
        paleta_colores_rgb = _extraer_paleta_colores(contenido_bytes, num_colores=4)
    else:
        paleta_colores_rgb = _extraer_paleta_colores(None) # Obtener paleta por defecto

    # 3. Calcular color de fondo final (dinámico o por parámetro)
    color_fondo_final = f"#{color_fondo_param}" # Empezar con el parámetro URL como fallback
    color_mezclado_rgb_para_brillo = _hex_a_rgb(color_fondo_param) # RGB del fallback

    # Solo calcular dinámico si el parámetro es el valor por defecto y tenemos paleta
    if color_fondo_param == "181414" and paleta_colores_rgb:
        try:
            color_dominante_rgb = paleta_colores_rgb[0] # Tomar el primer color (más dominante)
            # Mezclar con blanco (ajusta factor_blanco si es necesario)
            color_mezclado_rgb = _mezclar_con_blanco(color_dominante_rgb, factor_blanco=0.20)
            # Actualizar el color de fondo final y el RGB para cálculo de brillo
            color_fondo_final = "#{:02x}{:02x}{:02x}".format(*color_mezclado_rgb)
            color_mezclado_rgb_para_brillo = color_mezclado_rgb # Usar este para el brillo
            logging.info(f"Color de fondo dinámico calculado: {color_fondo_final}")
        except Exception as e:
            logging.error(f"Error al calcular color de fondo dinámico: {e}")
            # Si falla, nos quedamos con el color_fondo_param por defecto y su RGB
            color_fondo_final = f"#{color_fondo_param}"
            # Asegurarse que color_mezclado_rgb_para_brillo tenga el valor correcto del fallback
            color_mezclado_rgb_para_brillo = _hex_a_rgb(color_fondo_param)

    else:
        logging.info(f"Usando color de fondo del parámetro URL ({color_fondo_final}) o por defecto (no dinámico).")
        # Asegurarse que color_mezclado_rgb_para_brillo tenga el valor correcto
        color_mezclado_rgb_para_brillo = _hex_a_rgb(color_fondo_final.lstrip('#'))


    # 4. Calcular color de texto dinámico basado en el fondo final
    color_texto_contraste = "#FAFAFA" # Color claro por defecto (para fondos oscuros)
    if color_mezclado_rgb_para_brillo:
        # Usamos el umbral (ej. 135) para decidir
        if _es_color_claro(color_mezclado_rgb_para_brillo, umbral=135):
            color_texto_contraste = "#222222" # Fondo claro -> Texto oscuro
            logging.info(f"Fondo ({color_fondo_final}) detectado como claro, usando texto oscuro.")
        else:
            # color_texto_contraste ya es claro por defecto
            logging.info(f"Fondo ({color_fondo_final}) detectado como oscuro, usando texto claro.")
    else:
        logging.warning("No se pudo obtener RGB del fondo final, usando color de texto por defecto (#FAFAFA).")


    # 5. Convertir paleta a formato CSS hex para otros usos (ej. barras)
    paleta_colores_hex = [f"#{r:02x}{g:02x}{b:02x}" for r, g, b in paleta_colores_rgb]

    # 7. Determinar el texto de estado
    estado_actual = "Escuchando ahora:" 

    # 8. Preparar contexto para la plantilla Jinja2
    contexto = {
        "cancion": info_cancion.get('nombre_cancion', 'Desconocido'),
        "artista": info_cancion.get('nombre_artista', 'Desconocido'),
        "album": info_cancion.get('nombre_album', ''),
        "url_cancion": info_cancion.get('url_cancion_spotify'),
        "url_artista": info_cancion.get('url_artista_spotify'),
        "imagen_b64": imagen_base64,
        "estado": estado_actual,
        "color_fondo_final": color_fondo_final,      # Color de fondo final (hex)
        "color_borde": f"#{color_borde_param}",      # Color de borde (hex)
        "color_texto_contraste": color_texto_contraste, # Color de texto calculado (hex)
        "paleta_colores": paleta_colores_hex,        # Paleta para barras u otros usos
        "num_barras": NUM_BARRAS_EQ                  # Número de barras
    
    }

    # 9. Renderizar la plantilla SVG
    try:
        # Asume que esta función se llama desde un contexto de Flask
        # y que las plantillas están en 'api/plantillas/' (definido en main.py)
        svg_renderizado = render_template("lyricframe.html.j2", **contexto)
        logging.info("Plantilla SVG renderizada exitosamente.")
        return svg_renderizado
    except Exception as e:
        logging.exception(f"Error al renderizar la plantilla Jinja2 (lyricframe.html.j2): {e}")
        # Devolver un SVG de error simple
        return f'<svg width="350" height="140" xmlns="http://www.w3.org/2000/svg"><text x="10" y="50" fill="red">Error al generar SVG</text></svg>'