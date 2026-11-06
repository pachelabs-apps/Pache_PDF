"""Ozone PDF - herramientas PDF que funcionan 100% sin conexión."""
import gc
import os
import queue
import shutil
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from PIL import Image, ImageDraw, ImageTk

try:  # arrastrar y soltar archivos desde el Explorador (opcional)
    from tkinterdnd2 import TkinterDnD, DND_FILES, COPY
except Exception:  # si no está disponible, la app funciona igual con el botón
    TkinterDnD = None

import pdf_core as core

APP_NOMBRE = "Ozone PDF"
APP_MARCA = "Pache Labs"   # familia de herramientas gratuitas de Nicolás Emanuel Pacheco
APP_VERSION = "1.1.0"

# Paletas de colores. Los nombres se usan como variables globales; aplicar_tema() las
# reemplaza y la ventana se reconstruye con los colores nuevos.
#   Paleta roja y blanca, como la hoja PDF del logo: menú lateral rojo (la opción
#   elegida o con el foco, en un rojo más oscuro), botones y acentos rojos. En el tema
#   oscuro el menú es color vino muy oscuro y solo la opción elegida va en rojo.
#   AZUL: color de acento (textos, íconos, líneas)   BOTON: relleno de los botones principales
#   LATERAL: fondo del menú lateral                  BLANCO: texto sobre botones y menú activo
PALETA_CLARA = {
    "AZUL": "#D3261D", "AZUL_ACTIVO": "#E8463D", "AZUL_TEXTO_SUAVE": "#FFD0CC",
    "BOTON": "#D3261D", "BOTON_HOVER": "#A91A13", "BLANCO": "#FFFFFF",
    "LATERAL": "#D3261D", "LATERAL_HOVER": "#B81E16", "LATERAL_ACTIVO": "#8A120C",
    "MENU_TEXTO": "#FFEDEB", "PIE_TEXTO": "#FFC2BD",
    "FONDO": "#F7F7F8", "TARJETA": "#FFFFFF", "BORDE": "#E3E4E8", "TEXTO": "#1C1D22",
    "TEXTO_SUAVE": "#62646E", "OK": "#1E8A5A", "ROJO": "#C62828",
    "CAMPO": "#F6F6F8", "FILA_HOVER": "#FBF6F6", "SEPARADOR": "#EFEFF2", "GRIS_DESACTIVADO": "#ABADB6",
    "SECUNDARIO_HOVER": "#FDEEEC", "SCROLL": "#D6D7DC", "SCROLL_HOVER": "#A5A7B1",
    "INFO_FONDO": "#FDE5E3", "ZONA_INACTIVA": "#CBCCD3", "ZONA_RELLENO": "#FFF5F4", "ASA": "#BBBDC6",
    "BADGE_PDF": "#FDE5E3", "BADGE_PDF_TEXTO": "#C62218", "BADGE_IMG": "#F0F1F4", "ICONO_DESHAB": "#DADBE0",
    "GLOBO": "#24252B", "BUSCADOR": "#FFFFFF", "BUSCADOR_TEXTO": "#1C1D22", "BUSCADOR_SUGERENCIA": "#8A8C96",
    "AVISO_OK": "#E8F6EF", "AVISO_INFO": "#F0F1F4", "SOMBRA": "#D9DADF",
}
PALETA_OSCURA = {
    "AZUL": "#FF8A80", "AZUL_ACTIVO": "#FF8A80", "AZUL_TEXTO_SUAVE": "#B48C89",
    "BOTON": "#D2362C", "BOTON_HOVER": "#E5483D", "BLANCO": "#FFFFFF",
    "LATERAL": "#2A1416", "LATERAL_HOVER": "#3A1C1F", "LATERAL_ACTIVO": "#B3261E",
    "MENU_TEXTO": "#EBD4D2", "PIE_TEXTO": "#8E6C6A",
    "FONDO": "#141416", "TARJETA": "#1E1F23", "BORDE": "#33343A", "TEXTO": "#ECECEF",
    "TEXTO_SUAVE": "#A6A7B0", "OK": "#45C78C", "ROJO": "#F07A7A",
    "CAMPO": "#28292E", "FILA_HOVER": "#26272C", "SEPARADOR": "#2C2D33", "GRIS_DESACTIVADO": "#53555E",
    "SECUNDARIO_HOVER": "#2C2A2D", "SCROLL": "#3D3E45", "SCROLL_HOVER": "#62646E",
    "INFO_FONDO": "#3A2224", "ZONA_INACTIVA": "#4A4B53", "ZONA_RELLENO": "#231D1F", "ASA": "#5A5C65",
    "BADGE_PDF": "#3B2326", "BADGE_PDF_TEXTO": "#F59088", "BADGE_IMG": "#2C2D33", "ICONO_DESHAB": "#3D3E45",
    "GLOBO": "#33343A", "BUSCADOR": "#3B1F22", "BUSCADOR_TEXTO": "#F5E9E8", "BUSCADOR_SUGERENCIA": "#A88583",
    "AVISO_OK": "#173A2B", "AVISO_INFO": "#2A2B31", "SOMBRA": "#08080A",
}
TEMA_OSCURO = False
# nombres de los colores (valores iniciales: tema claro; aplicar_tema() los reemplaza)
AZUL = PALETA_CLARA["AZUL"]
AZUL_ACTIVO = PALETA_CLARA["AZUL_ACTIVO"]
AZUL_TEXTO_SUAVE = PALETA_CLARA["AZUL_TEXTO_SUAVE"]
BOTON = PALETA_CLARA["BOTON"]
BOTON_HOVER = PALETA_CLARA["BOTON_HOVER"]
BLANCO = PALETA_CLARA["BLANCO"]
LATERAL = PALETA_CLARA["LATERAL"]
LATERAL_HOVER = PALETA_CLARA["LATERAL_HOVER"]
LATERAL_ACTIVO = PALETA_CLARA["LATERAL_ACTIVO"]
MENU_TEXTO = PALETA_CLARA["MENU_TEXTO"]
PIE_TEXTO = PALETA_CLARA["PIE_TEXTO"]
FONDO = PALETA_CLARA["FONDO"]
TARJETA = PALETA_CLARA["TARJETA"]
BORDE = PALETA_CLARA["BORDE"]
TEXTO = PALETA_CLARA["TEXTO"]
TEXTO_SUAVE = PALETA_CLARA["TEXTO_SUAVE"]
OK = PALETA_CLARA["OK"]
ROJO = PALETA_CLARA["ROJO"]
CAMPO = PALETA_CLARA["CAMPO"]
FILA_HOVER = PALETA_CLARA["FILA_HOVER"]
SEPARADOR = PALETA_CLARA["SEPARADOR"]
GRIS_DESACTIVADO = PALETA_CLARA["GRIS_DESACTIVADO"]
SECUNDARIO_HOVER = PALETA_CLARA["SECUNDARIO_HOVER"]
SCROLL = PALETA_CLARA["SCROLL"]
SCROLL_HOVER = PALETA_CLARA["SCROLL_HOVER"]
INFO_FONDO = PALETA_CLARA["INFO_FONDO"]
ZONA_INACTIVA = PALETA_CLARA["ZONA_INACTIVA"]
ZONA_RELLENO = PALETA_CLARA["ZONA_RELLENO"]
ASA = PALETA_CLARA["ASA"]
BADGE_PDF = PALETA_CLARA["BADGE_PDF"]
BADGE_PDF_TEXTO = PALETA_CLARA["BADGE_PDF_TEXTO"]
BADGE_IMG = PALETA_CLARA["BADGE_IMG"]
ICONO_DESHAB = PALETA_CLARA["ICONO_DESHAB"]
GLOBO = PALETA_CLARA["GLOBO"]
BUSCADOR = PALETA_CLARA["BUSCADOR"]
BUSCADOR_TEXTO = PALETA_CLARA["BUSCADOR_TEXTO"]
BUSCADOR_SUGERENCIA = PALETA_CLARA["BUSCADOR_SUGERENCIA"]
AVISO_OK = PALETA_CLARA["AVISO_OK"]
AVISO_INFO = PALETA_CLARA["AVISO_INFO"]
SOMBRA = PALETA_CLARA["SOMBRA"]


def aplicar_tema(oscuro):
    """Carga la paleta clara u oscura en las variables globales de colores."""
    global TEMA_OSCURO
    TEMA_OSCURO = bool(oscuro)
    globals().update(PALETA_OSCURA if oscuro else PALETA_CLARA)


aplicar_tema(False)

CLAVE_REGISTRO = r"Software\Ozone PDF"


def leer_preferencia(nombre, defecto=""):
    """Lee una preferencia de la app (HKCU\\Software\\Ozone PDF). Fuera de Windows, el defecto."""
    if sys.platform != "win32":
        return defecto
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, CLAVE_REGISTRO) as k:
            return str(winreg.QueryValueEx(k, nombre)[0])
    except Exception:
        return defecto


def guardar_preferencia(nombre, valor):
    """Guarda una preferencia de la app (tema y casillas). No contiene datos de archivos."""
    if sys.platform != "win32":
        return
    try:
        import winreg
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, CLAVE_REGISTRO) as k:
            winreg.SetValueEx(k, nombre, 0, winreg.REG_SZ, str(valor))
    except Exception:
        pass


def tema_sistema():
    """True si Windows está en modo oscuro (Configuración > Personalización > Colores >
    modo de aplicaciones). Solo lee esa opción de Windows; la app no guarda nada."""
    if sys.platform != "win32":
        return False
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize") as k:
            return winreg.QueryValueEx(k, "AppsUseLightTheme")[0] == 0
    except Exception:
        return False


FUENTE = "Segoe UI" if sys.platform == "win32" else "Helvetica"


def recurso(nombre):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "assets", nombre)


def modo_compilacion():
    """Con qué exclusión de red se armó el ejecutable (lo escribe CREAR_INSTALADOR.bat).
    Desde el código fuente no aplica, aunque haya quedado el archivo de una compilación."""
    if not getattr(sys, "frozen", False):
        return ""
    try:
        with open(archivo_base("compilacion.txt"), encoding="utf-8") as fh:
            return fh.read().strip().lower()
    except OSError:
        return ""


def texto_modo_compilacion():
    m = modo_compilacion()
    if m == "estricta":
        return "Exclusión de red estricta: el programa no incluye socket, asyncio, multiprocessing, HTTP, SSL, correo ni FTP."
    if m == "reducida":
        return "Exclusión de red REDUCIDA: no incluye HTTP, SSL, correo ni FTP, pero sí socket (ver informe de seguridad)."
    return "Ejecución desde el código fuente (sin compilar)."


def archivo_base(nombre):
    """Archivos que viajan junto al programa (AVISO_USO.txt, LICENSE.txt, LICENCIAS.txt)."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, nombre)


EXT_IMAGEN = (".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp")


def abrir_archivo(ruta):
    """Abre un archivo local con el programa predeterminado (ej.: la licencia en el Bloc de notas)."""
    try:
        if sys.platform == "win32":
            os.startfile(ruta)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", ruta])
        else:
            subprocess.Popen(["xdg-open", ruta])
    except Exception:
        pass


def carpetas_sincronizadas():
    """Carpetas que OneDrive sincroniza con la nube: las de las variables de entorno y,
    en Windows, las que OneDrive registra localmente (cuentas personales, de la
    organización y bibliotecas de SharePoint o Teams montadas con "Sincronizar").
    Se leen del registro local; no se usa la red."""
    rutas = [os.environ.get(v) for v in ("OneDrive", "OneDriveCommercial", "OneDriveConsumer")]
    if sys.platform == "win32":
        try:
            import winreg
            base = r"Software\Microsoft\OneDrive\Accounts"
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, base) as cuentas:
                i = 0
                while True:
                    try:
                        cuenta = winreg.EnumKey(cuentas, i)
                    except OSError:
                        break
                    i += 1
                    clave = base + "\\" + cuenta
                    try:
                        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, clave) as k:
                            rutas.append(winreg.QueryValueEx(k, "UserFolder")[0])
                    except OSError:
                        pass
                    # bibliotecas montadas: los valores son las rutas locales
                    try:
                        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, clave + "\\ScopeIdToMountPointPathCache") as k:
                            j = 0
                            while True:
                                try:
                                    rutas.append(winreg.EnumValue(k, j)[1])
                                except OSError:
                                    break
                                j += 1
                    except OSError:
                        pass
                    # carpetas de la organización: los nombres de los valores son las rutas
                    try:
                        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, clave + "\\Tenants") as t:
                            j = 0
                            while True:
                                try:
                                    org = winreg.EnumKey(t, j)
                                except OSError:
                                    break
                                j += 1
                                with winreg.OpenKey(t, org) as k:
                                    m = 0
                                    while True:
                                        try:
                                            rutas.append(winreg.EnumValue(k, m)[0])
                                        except OSError:
                                            break
                                        m += 1
                    except OSError:
                        pass
        except OSError:
            pass
    vistas, salida = set(), []
    for r in rutas:
        if isinstance(r, str) and r.strip() and os.path.isabs(r):
            n = os.path.normcase(os.path.abspath(r))
            if n not in vistas:
                vistas.add(n)
                salida.append(r)
    return salida


def carpeta_onedrive(ruta):
    """Si la ruta está dentro de una carpeta sincronizada con OneDrive/SharePoint, devuelve esa carpeta."""
    destino = os.path.normcase(os.path.abspath(ruta))
    for base in carpetas_sincronizadas():
        if base:
            b = os.path.normcase(os.path.abspath(base))
            if destino == b or destino.startswith(b.rstrip("\\/") + os.sep):
                return base
    return None


def ocultar(ruta, si=True):
    """Marca una carpeta como oculta en Windows (para los parciales) o la vuelve visible."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        FILE_ATTRIBUTE_HIDDEN, FILE_ATTRIBUTE_NORMAL, FILE_ATTRIBUTE_DIRECTORY = 0x2, 0x80, 0x10
        attrs = ctypes.windll.kernel32.GetFileAttributesW(str(ruta))
        if attrs == -1 or attrs == 0xFFFFFFFF:
            return
        nuevos = (attrs | FILE_ATTRIBUTE_HIDDEN) if si else (attrs & ~FILE_ATTRIBUTE_HIDDEN)
        ctypes.windll.kernel32.SetFileAttributesW(str(ruta), nuevos or FILE_ATTRIBUTE_NORMAL)
    except Exception:
        pass


def borrar(ruta):
    """Borra un archivo o carpeta parcial si existe (sin errores si no se puede)."""
    try:
        if os.path.isdir(ruta):
            shutil.rmtree(ruta, ignore_errors=True)
        elif os.path.exists(ruta):
            os.remove(ruta)
    except OSError:
        pass


def traducir_error(e):
    """Mensaje en español y entendible para errores técnicos."""
    texto = str(e) or e.__class__.__name__
    t = texto.lower()
    if isinstance(e, PermissionError) or "permission denied" in t or "errno 13" in t:
        return ("No se pudo escribir el archivo. Puede que esté abierto en otro programa "
                "o que no tengas permiso en esa carpeta.")
    if isinstance(e, FileNotFoundError):
        return "No se encontró uno de los archivos. Puede que se haya movido o borrado."
    if "no space" in t or "errno 28" in t:
        return "No hay espacio suficiente en el disco."
    if "cannot open" in t or "failed to open" in t or "no objects found" in t or "format error" in t:
        return "No se pudo abrir uno de los archivos. Verificá que no esté dañado."
    if "invalid literal" in t or "keyerror" in t:
        return "Hay un dato mal escrito en las opciones. Revisá los campos e intentá de nuevo."
    if "not a pdf" in t or "is no pdf" in t or "not a pdf document" in t:
        return "Uno de los archivos no es un PDF."
    if isinstance(e, ValueError) and texto and texto[0].isupper() and not texto.isascii():
        return texto  # mensajes propios del programa, ya en español
    if isinstance(e, ValueError) and any(p in texto for p in ("Indicá", "Escribí", "Las contraseñas", "No se ")):
        return texto
    return ("Ocurrió un error inesperado al procesar los archivos. Verificá que sean del tipo "
            f"correcto y que no estén dañados.\n\n(Detalle técnico: {texto[:200]})")


def mismo_archivo(a, b):
    """True si a y b son el mismo archivo. En Windows no distingue mayúsculas
    ("Informe.pdf" = "informe.pdf") y también detecta accesos por otra ruta."""
    if os.path.normcase(os.path.abspath(a)) == os.path.normcase(os.path.abspath(b)):
        return True
    try:
        return os.path.exists(a) and os.path.exists(b) and os.path.samefile(a, b)
    except OSError:
        return False


def carpeta_libre(ruta):
    """Si la carpeta ya existe, usa 'nombre (2)', 'nombre (3)'... para no pisar archivos."""
    if not os.path.exists(ruta):
        return ruta
    n = 2
    while os.path.exists(f"{ruta} ({n})"):
        n += 1
    return f"{ruta} ({n})"


# palabras extra para el buscador de herramientas (además del título y la descripción)
CLAVES_BUSQUEDA = {
    "unir": "juntar combinar fusionar agregar merge",
    "dividir": "separar partir cortar mb megas tamaño peso split",
    "comprimir": "reducir achicar peso tamaño mb liviano mail",
    "extraer": "sacar copiar paginas",
    "eliminar": "borrar quitar sacar paginas",
    "reordenar": "mover ordenar orden cambiar",
    "rotar": "girar dar vuelta orientacion",
    "numerar": "numero numeracion foliar",
    "marca": "sello watermark texto confidencial",
    "pdf2img": "jpg jpeg png convertir imagen foto",
    "img2pdf": "jpg jpeg png foto imagen convertir escaneo",
    "camara": "foto fotos camara webcam escanear escaner sacar",
    "proteger": "contraseña clave password cifrar bloquear seguridad",
    "desproteger": "contraseña clave password desbloquear abrir sacar",
    "texto": "copiar word txt extraer letras",
}


def sin_tildes(s):
    """Minúsculas y sin tildes, para buscar sin importar cómo se escriba."""
    import unicodedata
    s = unicodedata.normalize("NFKD", s.lower())
    return "".join(c for c in s if not unicodedata.combining(c))


def texto_busqueda(h):
    return sin_tildes(" ".join([h["titulo"], h["desc"], CLAVES_BUSQUEDA.get(h["id"], "")]))


def limpiar_fotos_viejas():
    """Borra carpetas de fotos de la cámara que hayan quedado de un cierre inesperado
    (más de 12 horas; las de otra ventana del programa abierta ahora no se tocan)."""
    import glob
    import tempfile
    import time
    for d in glob.glob(os.path.join(tempfile.gettempdir(), "OzonePDF_fotos_*")):
        try:
            if time.time() - os.path.getmtime(d) > 12 * 3600:
                shutil.rmtree(d, ignore_errors=True)
        except OSError:
            pass


def tam_legible(b):
    for u in ("B", "KB", "MB", "GB"):
        if b < 1024:
            return f"{b:.0f} {u}" if u == "B" else f"{b:.1f} {u}"
        b /= 1024
    return f"{b:.1f} TB"


# ---------- Definición de herramientas ----------
# entrada: 'multi' (varios PDF), 'pdf' (uno), 'imagenes'
# salida: 'pdf', 'carpeta', 'txt'
HERRAMIENTAS = [
    {"id": "unir", "titulo": "Unir PDF", "desc": "Combiná varios PDF en uno solo, en el orden que elijas.",
     "entrada": "multi", "salida": "pdf", "sufijo": "_unido", "opciones": []},
    {"id": "dividir", "titulo": "Dividir PDF", "desc": "Separá un PDF en varios archivos: cada N páginas, por rangos o por tamaño máximo (MB).",
     "entrada": "pdf", "salida": "carpeta",
     "opciones": [("modo", "Modo", "combo", ["Cada N páginas", "Por rangos", "Por tamaño (MB)"], "Cada N páginas"),
                  ("valor", "Páginas (ej: 2), rangos (ej: 1-3,4-8,9-) o MB (ej: 25)", "texto", None, "1")]},
    {"id": "comprimir", "titulo": "Comprimir PDF", "desc": "Reducí el peso del archivo optimizando imágenes y fuentes.",
     "entrada": "pdf", "salida": "pdf", "sufijo": "_comprimido",
     "opciones": [("nivel", "Nivel de compresión", "combo",
                   ["Baja (mejor calidad)", "Media (recomendada)", "Alta (menor tamaño)"], "Media (recomendada)")]},
    {"id": "extraer", "titulo": "Extraer páginas", "desc": "Creá un PDF nuevo solo con las páginas que necesitás.",
     "entrada": "pdf", "salida": "pdf", "sufijo": "_extracto",
     "opciones": [("rango", "Páginas (ej: 1,3,5-8)", "texto", None, "1")]},
    {"id": "eliminar", "titulo": "Eliminar páginas", "desc": "Quitá páginas que no querés del documento.",
     "entrada": "pdf", "salida": "pdf", "sufijo": "_editado",
     "opciones": [("rango", "Páginas a eliminar (ej: 2,4-6)", "texto", None, "")]},
    {"id": "reordenar", "titulo": "Ordenar páginas", "desc": "Indicá el nuevo orden de las páginas.",
     "entrada": "pdf", "salida": "pdf", "sufijo": "_ordenado",
     "opciones": [("orden", "Nuevo orden (ej: 3,1,2,4-10)", "texto", None, "")]},
    {"id": "rotar", "titulo": "Rotar PDF", "desc": "Girá todas las páginas o solo algunas.",
     "entrada": "pdf", "salida": "pdf", "sufijo": "_rotado",
     "opciones": [("grados", "Giro", "combo", ["90° a la derecha", "180°", "90° a la izquierda"], "90° a la derecha"),
                  ("rango", "Páginas (vacío = todas)", "texto", None, "")]},
    {"id": "numerar", "titulo": "Numerar páginas", "desc": "Agregá números de página al documento.",
     "entrada": "pdf", "salida": "pdf", "sufijo": "_numerado",
     "opciones": [("posicion", "Posición", "combo",
                   ["abajo-centro", "abajo-der", "abajo-izq", "arriba-centro", "arriba-der", "arriba-izq"], "abajo-centro"),
                  ("formato", "Formato ({n} = número, {total} = total)", "texto", None, "{n} / {total}"),
                  ("inicio", "Empezar en", "texto", None, "1")]},
    {"id": "marca", "titulo": "Marca de agua", "desc": "Estampá un texto en diagonal sobre todas las páginas.",
     "entrada": "pdf", "salida": "pdf", "sufijo": "_marca",
     "opciones": [("texto", "Texto", "texto", None, "CONFIDENCIAL"),
                  ("opacidad", "Opacidad", "combo", ["Suave", "Media", "Fuerte"], "Suave")]},
    {"id": "pdf2img", "titulo": "PDF a imagen", "desc": "Convertí cada página en una imagen JPG o PNG.",
     "entrada": "pdf", "salida": "carpeta",
     "opciones": [("formato", "Formato", "combo", ["jpg", "png"], "jpg"),
                  ("dpi", "Resolución", "combo", ["100", "150", "200", "300"], "150")]},
    {"id": "img2pdf", "titulo": "Imagen a PDF", "desc": "Juntá fotos o escaneos (JPG, PNG) en un PDF.",
     "entrada": "imagenes", "salida": "pdf", "sufijo": "_imagenes",
     "opciones": [("tamano", "Tamaño de página", "combo", ["A4", "Carta", "Original"], "A4")]},
    {"id": "camara", "titulo": "Fotos a PDF", "desc": "Sacá fotos con la cámara de la computadora y juntalas en un PDF.",
     "entrada": "imagenes", "salida": "pdf", "sufijo": "", "camara": True,
     "opciones": [("tamano", "Tamaño de página", "combo", ["A4", "Carta", "Original"], "A4"),
                  ("color", "Color", "combo", ["Color", "Escala de grises", "Documento (blanco y negro)"], "Color")]},
    {"id": "proteger", "titulo": "Proteger PDF", "desc": "Poné contraseña al archivo (cifrado AES-256).",
     "entrada": "pdf", "salida": "pdf", "sufijo": "_protegido",
     "opciones": [("password", "Contraseña", "clave", None, ""),
                  ("password2", "Repetir contraseña", "clave", None, "")]},
    {"id": "desproteger", "titulo": "Quitar contraseña", "desc": "Sacá la contraseña de un PDF del que la conocés.",
     "entrada": "pdf", "salida": "pdf", "sufijo": "_sin_clave",
     "opciones": [("password", "Contraseña actual", "clave", None, "")]},
    {"id": "texto", "titulo": "PDF a texto", "desc": "Extraé todo el texto del documento a un archivo .txt.",
     "entrada": "pdf", "salida": "txt", "opciones": []},
]


# Herramientas que solo leen el PDF (no generan otro PDF) y el permiso que necesitan
# si el PDF tiene restricciones. Tampoco afectan firmas digitales.
SOLO_LECTURA = {"texto": core.pymupdf.PDF_PERM_COPY, "pdf2img": core.pymupdf.PDF_PERM_PRINT}


def ejecutar(h, archivos, destino, op, cancelar=None):
    """Llama al motor según la herramienta. Devuelve el mensaje de resultado.
    "cancelar" es un threading.Event que el motor revisa en cada página."""
    hid, a = h["id"], archivos[0] if archivos else None
    c = cancelar
    if hid == "unir":
        core.unir(archivos, destino, cancelar=c)
        return f"Se unieron {len(archivos)} archivos."
    if hid == "dividir":
        if op["modo"].startswith("Por tamaño"):
            partes, grandes = core.dividir_por_tamano(a, destino, op["valor"], cancelar=c)
            msg = f"Se generaron {len(partes)} archivos de hasta {op['valor'].strip()} MB."
            if grandes:
                msg += (f" {grandes} parte{'s' if grandes != 1 else ''} supera{'n' if grandes != 1 else ''} el "
                        "límite porque tiene una sola página más pesada que eso (una página no se puede partir).")
            return msg
        modo = "cada" if op["modo"].startswith("Cada") else "rangos"
        partes = core.dividir(a, destino, modo, op["valor"], cancelar=c)
        return f"Se generaron {len(partes)} archivos."
    if hid == "comprimir":
        nivel = op["nivel"].split()[0].lower()
        antes, despues = core.comprimir(a, destino, nivel, cancelar=c)  # si no achica, lanza SinCambios
        return f"{tam_legible(antes)} → {tam_legible(despues)}  (−{100 - despues * 100 / antes:.0f}%)"
    if hid == "extraer":
        core.extraer_paginas(a, destino, op["rango"], cancelar=c)
    elif hid == "eliminar":
        if not op["rango"].strip():
            raise ValueError("Indicá qué páginas eliminar.")
        core.eliminar_paginas(a, destino, op["rango"], cancelar=c)
    elif hid == "reordenar":
        if not op["orden"].strip():
            raise ValueError("Indicá el nuevo orden de páginas.")
        core.reordenar(a, destino, op["orden"], cancelar=c)
    elif hid == "rotar":
        g = {"90° a la derecha": 90, "180°": 180, "90° a la izquierda": 270}[op["grados"]]
        core.rotar(a, destino, g, op["rango"], cancelar=c)
    elif hid == "numerar":
        core.numerar(a, destino, op["posicion"], op["formato"], int(op["inicio"] or 1), cancelar=c)
    elif hid == "marca":
        if not op["texto"].strip():
            raise ValueError("Escribí el texto de la marca de agua.")
        opac = {"Suave": 0.18, "Media": 0.3, "Fuerte": 0.5}[op["opacidad"]]
        core.marca_agua(a, destino, op["texto"], opac, cancelar=c)
    elif hid == "pdf2img":
        imgs, reducidas = core.pdf_a_imagenes(a, destino, int(op["dpi"]), op["formato"], cancelar=c)
        msg = f"Se generaron {len(imgs)} imágenes."
        if reducidas:
            msg += (f" {reducidas} página{'s' if reducidas != 1 else ''} muy grande{'s' if reducidas != 1 else ''} "
                    "se exportaron con menor resolución para no agotar la memoria.")
        return msg
    elif hid == "img2pdf":
        core.imagenes_a_pdf(archivos, destino, op["tamano"], cancelar=c)
        n = len(archivos)
        return f"Se convirti{'eron' if n != 1 else 'ó'} {n} imagen{'es' if n != 1 else ''}."
    elif hid == "camara":
        modo = {"Escala de grises": "gris", "Documento (blanco y negro)": "documento"}.get(op["color"])
        fotos, temporal = archivos, None
        try:
            if modo:
                import tempfile
                temporal = tempfile.mkdtemp(prefix="OzonePDF_ajuste_")
                fotos = core.ajustar_fotos(archivos, temporal, modo, cancelar=c)
            core.imagenes_a_pdf(fotos, destino, op["tamano"], cancelar=c)
        finally:
            if temporal:
                shutil.rmtree(temporal, ignore_errors=True)
        n = len(archivos)
        return f"Se armó un PDF con {n} foto{'s' if n != 1 else ''}."
    elif hid == "proteger":
        if not op["password"]:
            raise ValueError("Escribí una contraseña.")
        if op["password"] != op["password2"]:
            raise ValueError("Las contraseñas no coinciden.")
        core.proteger(a, destino, op["password"], cancelar=c)
    elif hid == "desproteger":
        r = core.desproteger(a, destino, op["password"], cancelar=c)
        if r.get("restricciones_mantenidas"):
            return ("Se quitó la contraseña de apertura. El PDF tenía restricciones (por ejemplo, no "
                    "modificar) y se mantienen: para quitarlas hace falta la contraseña de propietario.")
        return "Se quitó la contraseña."
    elif hid == "texto":
        core.pdf_a_texto(a, destino, cancelar=c)
    return "Listo."


# =====================================================================
#  INTERFAZ
# =====================================================================
import tkinter.font as tkfont


AYUDA = {
    "unir": "Junta dos o más PDF en un único archivo.\n\n"
            "• Agregá los archivos con el botón \u201cAgregar PDF\u201d (podés elegir varios a la vez).\n"
            "• También podés arrastrarlos desde el escritorio o una carpeta y soltarlos acá.\n"
            "• Para cambiar el orden, arrastrá un archivo a otra posición o usá las flechas ↑ ↓.\n"
            "• El PDF final respeta el orden de la lista y conserva los marcadores (índice).",
    "dividir": "Separa un PDF en varios archivos más chicos.\n\n"
               "• Cada N páginas: con N = 1 obtenés un archivo por página; con N = 5, uno cada 5 páginas.\n"
               "• Por rangos: escribí los grupos separados por coma, por ejemplo 1-3,4-10,11-.\n"
               "  Cada rango genera un archivo. \u201c11-\u201d significa de la 11 hasta el final.\n"
               "• Por tamaño (MB): cada archivo pesa como máximo lo que indiques (por ejemplo 25,\n"
               "  el límite de muchos correos). Se arman con páginas seguidas, todas las que entran.\n"
               "  Si una página sola pesa más que el límite, queda en un archivo aparte.\n"
               "• Los archivos se guardan en una carpeta nueva dentro de la que elijas.",
    "comprimir": "Reduce el peso del PDF para poder enviarlo por mail o subirlo a sistemas con límite de tamaño.\n\n"
                 "• Baja: fotos y escaneos en color o grises a 150 dpi; casi sin pérdida visible.\n"
                 "• Media: buen equilibrio para la mayoría de los casos (110 dpi).\n"
                 "• Alta: máxima reducción (72 dpi); las imágenes pueden perder nitidez.\n"
                 "• Los escaneos en blanco y negro (expedientes) solo se reducen en Alta,\n"
                 "  porque al bajarles la resolución se pierde legibilidad.\n\n"
                 "Funciona mejor en PDF escaneados o con fotos. Los PDF que son solo texto ya suelen ser livianos.\n"
                 "Si el resultado no queda más chico que el original, no se genera ningún archivo.",
    "extraer": "Crea un PDF nuevo solo con las páginas que indiques. El original no se modifica.\n\n"
               "Ejemplos:\n• 3  → solo la página 3\n• 1,4,7  → esas tres páginas\n• 2-5  → de la 2 a la 5\n• 10-  → de la 10 al final",
    "eliminar": "Genera una copia del PDF sin las páginas que indiques. El original no se modifica.\n\n"
                "Ejemplos:\n• 1  → quita la primera página\n• 2,5-7  → quita la 2 y de la 5 a la 7",
    "reordenar": "Cambia el orden de las páginas del documento.\n\n"
                 "Escribí el nuevo orden completo, por ejemplo en un PDF de 5 páginas:\n"
                 "• 5,1-4  → pasa la última página al principio\n• 5-1 no es válido; usá 5,4,3,2,1\n\n"
                 "Las páginas que no incluyas quedan fuera del archivo final.",
    "rotar": "Gira páginas que quedaron de costado o al revés (típico en escaneos).\n\n"
             "• Elegí el sentido del giro.\n"
             "• Dejá el campo de páginas vacío para rotar todo, o indicá cuáles (ej: 2,4-6).",
    "numerar": "Agrega el número de página impreso en cada hoja.\n\n"
               "• Posición: dónde aparece el número (abajo/arriba, izquierda/centro/derecha).\n"
               "• Formato: {n} es el número de página y {total} la cantidad total.\n"
               "  Ejemplos: \u201c{n} / {total}\u201d → 3 / 10   ·   \u201cPágina {n}\u201d → Página 3\n"
               "• Empezar en: útil si el documento es continuación de otro (ej: 21).",
    "marca": "Estampa un texto en diagonal sobre todas las páginas, como \u201cCONFIDENCIAL\u201d, \u201cCOPIA\u201d o \u201cBORRADOR\u201d.\n\n"
             "• Opacidad suave: se lee el contenido sin problema.\n"
             "• Fuerte: la marca se destaca más que el texto.",
    "pdf2img": "Convierte cada página del PDF en una imagen independiente.\n\n"
               "• JPG: archivos más livianos, ideal para compartir.\n"
               "• PNG: mejor calidad para texto y gráficos.\n"
               "• Resolución: 150 alcanza para pantalla; 300 para imprimir.\n"
               "• Las páginas muy grandes (por ejemplo, planos) se exportan con menor resolución\n"
               "  para no agotar la memoria.\n"
               "• Funciona con PDF que tienen restricciones, si permiten imprimir.",
    "img2pdf": "Junta fotos o escaneos (JPG, PNG, BMP, TIFF, WEBP) en un solo PDF, una imagen por página.\n"
               "Las fotos de celular se giran solas según su orientación, y cada página de un TIFF\n"
               "de varias páginas sale como una página del PDF. En GIF o WEBP animados se usa el\n"
               "primer cuadro. Las fotos se insertan sin sus datos ocultos (ubicación GPS, modelo\n"
               "de celular, autor).\n\n"
               "• Podés arrastrar las imágenes (o una carpeta entera) y soltarlas acá.\n"
               "• Para cambiar el orden, arrastrá una imagen a otra posición o usá las flechas ↑ ↓.\n"
               "• A4 / Carta: ajusta cada imagen a la hoja con margen.\n"
               "• Original: cada página toma el tamaño exacto de la imagen.",
    "camara": "Usa la cámara de la computadora (la de la notebook o una webcam) como escáner.\n\n"
              "• Tocá \u201cAbrir cámara\u201d, poné la hoja frente a la cámara y sacá una foto por página\n"
              "  (botón \u201cSacar foto\u201d o la barra espaciadora). Podés sacar todas las que quieras.\n"
              "• Modo \u201cEscanear documento\u201d: detecta la hoja (la marca en verde), la recorta y la\n"
              "  endereza, como una app de escaneo. Funciona mejor con la hoja sobre un fondo oscuro.\n"
              "  Modo \u201cFoto normal\u201d: guarda la foto completa, tal cual.\n"
              "• Las fotos aparecen en la lista: podés cambiarles el orden o quitar las que salieron mal.\n"
              "• Color: \u201cDocumento\u201d deja el papel blanco y el texto oscuro, como un escaneo;\n"
              "  \u201cEscala de grises\u201d mejora el contraste sin color.\n"
              "• Las fotos quedan solo en esta computadora, en una carpeta temporal que se borra al\n"
              "  cerrar el programa. También podés arrastrar fotos que ya tengas.\n\n"
              "Si la cámara no abre: revisá que no la esté usando otro programa (Teams, Zoom) y que\n"
              "Windows permita usarla (Configuración > Privacidad > Cámara > aplicaciones de escritorio).",
    "proteger": "Pone una contraseña para abrir el PDF, con cifrado AES-256.\n\n"
                "• Sin la contraseña nadie puede ver el contenido.\n"
                "• Quien tenga la contraseña puede abrirlo y usarlo completo (imprimir, copiar,\n"
                "  editar), y quitarle la protección con \u201cQuitar contraseña\u201d.\n"
                "• Guardala bien: si la perdés, no hay forma de recuperar el archivo.",
    "desproteger": "Quita la contraseña de un PDF del que ya conocés la clave, para no tener que escribirla cada vez que lo abrís.\n\n"
                   "• Si el PDF pide clave para abrirse: escribí esa clave.\n"
                   "• Si el PDF abre sin clave pero tiene restricciones (no deja imprimir o copiar):\n"
                   "  hace falta la contraseña de propietario.\n"
                   "• Con la clave de apertura se quita la contraseña, pero si el PDF tenía\n"
                   "  restricciones se mantienen. Para quitarlas hace falta la de propietario.\n\n"
                   "No sirve para abrir PDF de los que no tenés la contraseña.",
    "texto": "Extrae todo el texto del PDF a un archivo .txt que podés abrir con el Bloc de notas o pegar en Word.\n\n"
             "Funciona con PDF generados digitalmente. En PDF escaneados (fotos de papel) no hay texto para extraer.\n"
             "Si el PDF tiene restricciones, funciona cuando permiten copiar el texto.",
}

ESCALA = 1.0


def px(n):
    return int(round(n * ESCALA))


def _rgb(c):
    c = c.lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


_cache_img = {}


def redondeado(w, h, r, relleno, borde=None, grosor=1, cache=True, camara=None):
    """Rectángulo redondeado con bordes suavizados (antialias por sobremuestreo).
    camara=(x, tamaño, color): dibuja además el ícono de una cámara en esa posición."""
    w, h = max(2, int(w)), max(2, int(h))
    clave = (w, h, r, relleno, borde, grosor, camara)
    if cache and clave in _cache_img:
        return _cache_img[clave]
    f = 4 if w * h < 120_000 else 2
    im = Image.new("RGBA", (w * f, h * f), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, w * f - 1, h * f - 1), radius=r * f, fill=_rgb(relleno),
                        outline=_rgb(borde) if borde else None, width=grosor * f if borde else 0)
    if camara:
        x, s, color = camara
        x, s, cy = x * f, s * f, h * f / 2
        c = _rgb(color)
        d.rounded_rectangle((x + s * 0.30, cy - s * 0.50, x + s * 0.64, cy - s * 0.25), radius=s * 0.06, fill=c)
        d.rounded_rectangle((x, cy - s * 0.36, x + s, cy + s * 0.42), radius=s * 0.14, fill=c)
        d.ellipse((x + s * 0.27, cy - s * 0.20, x + s * 0.73, cy + s * 0.26), fill=_rgb(relleno))
        d.ellipse((x + s * 0.38, cy - s * 0.09, x + s * 0.62, cy + s * 0.15), fill=c)
    foto = ImageTk.PhotoImage(im.resize((w, h), Image.LANCZOS))
    if cache:
        _cache_img[clave] = foto
    return foto


def circulo_info(d, relleno, color_i):
    """Ícono redondo con una 'i' dibujada (no depende de fuentes)."""
    clave = ("info", d, relleno, color_i)
    if clave in _cache_img:
        return _cache_img[clave]
    f = 6
    D = d * f
    im = Image.new("RGBA", (D, D), (0, 0, 0, 0))
    dr = ImageDraw.Draw(im)
    dr.ellipse((0, 0, D - 1, D - 1), fill=_rgb(relleno))
    c = _rgb(color_i)
    cx = D / 2
    pr = D * 0.075
    dr.ellipse((cx - pr, D * 0.22, cx + pr, D * 0.22 + 2 * pr), fill=c)
    dr.rounded_rectangle((cx - pr, D * 0.42, cx + pr, D * 0.76), radius=pr, fill=c)
    foto = ImageTk.PhotoImage(im.resize((d, d), Image.LANCZOS))
    _cache_img[clave] = foto
    return foto


def fuente(tam, negrita=False):
    return (FUENTE, tam, "bold") if negrita else (FUENTE, tam)


# ---------------------------------------------------------------------
class Boton(tk.Label):
    """Botón con esquinas redondeadas y hover."""
    @staticmethod
    def estilos():
        #             relleno  hover             borde  texto  (se leen del tema actual)
        return {"primario": (BOTON, BOTON_HOVER, None, BLANCO),
                "secundario": (TARJETA, SECUNDARIO_HOVER, BORDE, AZUL)}

    def __init__(self, padre, texto, comando, tipo="primario", grande=False, bg_padre=None, icono=None):
        bg_padre = FONDO if bg_padre is None else bg_padre
        self._f = tkfont.Font(family=FUENTE, size=11 if grande else 10,
                              weight="bold" if tipo == "primario" else "normal")
        self._tipo, self._grande, self._icono = tipo, grande, icono
        self._fg = self.estilos()[tipo][3]
        texto = self._imagenes(texto)
        # takefocus + anillo de foco: se puede llegar con Tab y activar con Enter o espacio
        super().__init__(padre, image=self._img, text=texto, compound="center", fg=self._fg, bg=bg_padre,
                         font=self._f, bd=0, cursor="hand2", takefocus=1, highlightthickness=px(2),
                         highlightbackground=bg_padre, highlightcolor=AZUL_ACTIVO)
        self.activo = True
        self._cmd = comando
        self.bind("<Button-1>", lambda e: self._cmd() if self.activo else None)
        self.bind("<Enter>", lambda e: self.configure(image=self._img_h) if self.activo else None)
        self.bind("<Leave>", lambda e: self.configure(image=self._img) if self.activo else None)
        for tecla in ("<Return>", "<KP_Enter>", "<space>"):
            self.bind(tecla, lambda e: (self._cmd() if self.activo else None, "break")[1])

    def _imagenes(self, texto):
        """Arma las imágenes del botón. Con ícono (por ahora, "camara") se deja lugar con
        espacios al principio del texto y el ícono se dibuja en ese lugar. Devuelve el
        texto a mostrar."""
        g = self._grande
        cam = cam_d = None
        rell, hov, borde, fg = self.estilos()[self._tipo]
        if self._icono:
            s = px(17 if g else 15)
            n = 1
            while self._f.measure(" " * n) < s + px(7):
                n += 1
            texto = " " * n + texto
        w = self._f.measure(texto) + px(44 if g else 30)
        h = self._f.metrics("linespace") + px(22 if g else 14)
        r = px(10 if g else 8)
        if self._icono:
            x = (w - self._f.measure(texto)) / 2
            cam, cam_d = (x, s, fg), (x, s, BLANCO)
        self._img = redondeado(w, h, r, rell, borde, camara=cam)
        self._img_h = redondeado(w, h, r, hov, borde, camara=(cam[0], cam[1], fg) if cam else None)
        self._img_d = redondeado(w, h, r, GRIS_DESACTIVADO, camara=cam_d)
        return texto

    def set_texto(self, texto):
        texto = self._imagenes(texto)
        self.configure(text=texto, image=self._img if self.activo else self._img_d)

    def habilitar(self, si):
        self.activo = si
        self.configure(image=self._img if si else self._img_d, fg=self._fg if si else BLANCO,
                       cursor="hand2" if si else "arrow")


class Casilla(tk.Frame):
    """Casilla de verificación con el estilo de la app (se ve igual en modo claro y oscuro).
    Se marca con clic, o con Tab + espacio/Enter."""

    def __init__(self, padre, texto, valor, al_cambiar=None, bg=None):
        bg = FONDO if bg is None else bg
        super().__init__(padre, bg=bg, cursor="hand2", takefocus=1, highlightthickness=px(1),
                         highlightbackground=bg, highlightcolor=AZUL_ACTIVO)
        self.valor, self.al_cambiar = bool(valor), al_cambiar
        lado = px(16)
        self.caja = tk.Canvas(self, width=lado, height=lado, bg=bg, highlightthickness=0, bd=0)
        self.caja.pack(side="left", padx=(px(2), px(6)), pady=px(2))
        self.txt = tk.Label(self, text=texto, bg=bg, fg=TEXTO_SUAVE, font=fuente(9))
        self.txt.pack(side="left", padx=(0, px(2)))
        self._lado = lado
        self._dibujar()
        for w in (self, self.caja, self.txt):
            w.bind("<Button-1>", lambda e: self.alternar())
        for tecla in ("<space>", "<Return>", "<KP_Enter>"):
            self.bind(tecla, lambda e: (self.alternar(), "break")[1])

    def _dibujar(self):
        c, l = self.caja, self._lado
        c.delete("all")
        if self.valor:
            c.create_image(0, 0, anchor="nw", image=self._img(BOTON, None))
            c.create_line(l * 0.24, l * 0.52, l * 0.43, l * 0.70, l * 0.77, l * 0.30, fill=BLANCO,
                          width=max(2, px(2)), capstyle="round", joinstyle="round")
        else:
            c.create_image(0, 0, anchor="nw", image=self._img(CAMPO, GRIS_DESACTIVADO))
        self.txt.configure(fg=TEXTO if self.valor else TEXTO_SUAVE)

    def _img(self, relleno, borde):
        self._imagen = redondeado(self._lado, self._lado, px(4), relleno, borde)
        return self._imagen

    def alternar(self):
        self.valor = not self.valor
        self._dibujar()
        if self.al_cambiar:
            self.al_cambiar(self.valor)


class Tarjeta(tk.Frame):
    """Contenedor con fondo de esquinas redondeadas que se adapta al tamaño."""

    def __init__(self, padre, relleno=None, borde=None, radio=14, bg_padre=None, **kw):
        relleno = TARJETA if relleno is None else relleno
        borde = BORDE if borde is None else borde
        bg_padre = FONDO if bg_padre is None else bg_padre
        super().__init__(padre, bg=bg_padre, **kw)
        self.relleno, self.borde, self.radio = relleno, borde, radio
        self._fondo = tk.Label(self, bd=0, bg=bg_padre, highlightthickness=0)
        self._fondo.place(x=0, y=0, relwidth=1, relheight=1)
        self._tam = None
        self._pend = None
        self.bind("<Configure>", self._programar)

    def _programar(self, e=None):
        if self._pend:
            self.after_cancel(self._pend)
        self._pend = self.after(15, self._redibujar)

    def _redibujar(self):
        self._pend = None
        w, h = self.winfo_width(), self.winfo_height()
        if w < 6 or h < 6 or self._tam == (w, h, self.borde):
            return
        self._tam = (w, h, self.borde)
        self._img = redondeado(w, h, self.radio, self.relleno, self.borde, cache=False)
        self._fondo.configure(image=self._img)
        self._fondo.lower()

    def set_borde(self, color):
        self.borde = color
        self._redibujar()


class ScrollFino(tk.Canvas):
    """Barra de desplazamiento fina, sin flechas, que se oculta si no hace falta."""

    def __init__(self, padre, comando, bg=None):
        bg = TARJETA if bg is None else bg
        super().__init__(padre, width=px(12), height=1, bg=bg, highlightthickness=0, bd=0)
        self.cmd = comando
        self.ini, self.fin = 0.0, 1.0
        self.color, self.color_h = SCROLL, SCROLL_HOVER
        self.thumb = self.create_line(0, 0, 0, 0, width=px(6), capstyle="round", fill=self.color)
        self.bind("<Configure>", lambda e: self._dibujar())
        self.bind("<Enter>", lambda e: self.itemconfig(self.thumb, fill=self.color_h))
        self.bind("<Leave>", lambda e: self.itemconfig(self.thumb, fill=self.color))
        self.bind("<Button-1>", self._click)
        self.bind("<B1-Motion>", self._arrastrar)

    def set(self, ini, fin):
        self.ini, self.fin = float(ini), float(fin)
        self._dibujar()

    def _dibujar(self):
        h = self.winfo_height()
        cx = self.winfo_width() / 2
        if self.fin - self.ini >= 0.999:
            self.itemconfig(self.thumb, state="hidden")
            return
        m = px(5)
        y0 = m + self.ini * (h - 2 * m)
        y1 = m + self.fin * (h - 2 * m)
        self.coords(self.thumb, cx, y0, cx, max(y0 + px(10), y1))
        self.itemconfig(self.thumb, state="normal")

    def _click(self, e):
        h = max(1, self.winfo_height())
        pos = e.y / h
        if self.ini <= pos <= self.fin:
            self._ancla = (e.y, self.ini)
        else:
            self._ancla = None
            self.cmd("moveto", max(0.0, pos - (self.fin - self.ini) / 2))

    def _arrastrar(self, e):
        if getattr(self, "_ancla", None):
            y, ini = self._ancla
            self.cmd("moveto", ini + (e.y - y) / max(1, self.winfo_height()))


class ItemMenu(tk.Canvas):
    """Opción del menú lateral con resaltado redondeado."""

    def __init__(self, padre, texto, comando, ancho, alto=33):
        h = px(alto)
        super().__init__(padre, width=ancho, height=h, bg=LATERAL, bd=0, cursor="hand2", takefocus=1,
                         highlightthickness=0)
        self._hover = redondeado(ancho, h, px(9), LATERAL_HOVER)
        self._activo_img = redondeado(ancho, h, px(9), LATERAL_ACTIVO)
        self.fondo = self.create_image(0, 0, anchor="nw", image=self._hover, state="hidden")
        self.marca = self.create_line(px(10), px(10), px(10), h - px(10), width=px(3), fill=BLANCO,
                                      capstyle="round", state="hidden")
        self.txt = self.create_text(px(24), h // 2, anchor="w", text=texto, fill=MENU_TEXTO, font=fuente(10))
        self.activo = False
        self.bind("<Button-1>", lambda e: comando())
        for tecla in ("<Return>", "<KP_Enter>", "<space>"):
            self.bind(tecla, lambda e: (comando(), "break")[1])
        self.bind("<Enter>", self._entrar)
        self.bind("<Leave>", self._salir)
        # con el teclado (Tab o flechas) la opción con foco se ve en el rojo más oscuro
        self.bind("<FocusIn>", lambda e: self._entrar(e, foco=True))
        self.bind("<FocusOut>", self._salir)

    def set_activo(self, si):
        self.activo = si
        self.itemconfig(self.fondo, image=self._activo_img, state="normal" if si else "hidden")
        self.itemconfig(self.marca, state="normal" if si else "hidden")
        self.itemconfig(self.txt, fill=BLANCO if si else MENU_TEXTO, font=fuente(10, si))

    def _entrar(self, e, foco=False):
        if not self.activo:
            con_foco = foco or self.focus_get() is self
            self.itemconfig(self.fondo, image=self._activo_img if con_foco else self._hover, state="normal")
            self.itemconfig(self.txt, fill=BLANCO)

    def _salir(self, e):
        if self.activo:
            return
        try:
            con_foco = self.focus_get() is self
        except (KeyError, tk.TclError):
            con_foco = False
        if con_foco and e.type != tk.EventType.FocusOut:
            self.itemconfig(self.fondo, image=self._activo_img, state="normal")
            return
        self.itemconfig(self.fondo, state="hidden")
        self.itemconfig(self.txt, fill=MENU_TEXTO)


class Globo:
    """Globo de ayuda que aparece junto al ícono de información."""

    def __init__(self, widget, texto_fn):
        self.w, self.texto_fn = widget, texto_fn
        self.win = None
        self.fijo = False
        widget.bind("<Enter>", lambda e: self.mostrar())
        widget.bind("<Leave>", lambda e: None if self.fijo else self.ocultar())
        widget.bind("<Button-1>", self._click)
        # con teclado: Tab llega al ícono, Enter o espacio abre/cierra la ayuda, Escape la cierra
        try:
            widget.configure(takefocus=1, highlightthickness=px(2), highlightcolor=AZUL_ACTIVO,
                             highlightbackground=widget.cget("bg"))
        except tk.TclError:
            pass
        for tecla in ("<Return>", "<KP_Enter>", "<space>"):
            widget.bind(tecla, lambda e: (self._click(e), "break")[1])
        widget.bind("<Escape>", lambda e: (setattr(self, "fijo", False), self.ocultar()))
        widget.bind("<FocusOut>", lambda e: (setattr(self, "fijo", False), self.ocultar()))

    def _click(self, e):
        if self.win and self.fijo:
            self.fijo = False
            self.ocultar()
        else:
            self.fijo = True
            self.mostrar()

    def mostrar(self):
        if self.win:
            return
        top = self.w.winfo_toplevel()
        self.win = tk.Toplevel(top)
        self.win.overrideredirect(True)
        self.win.configure(bg=GLOBO)
        try:
            self.win.attributes("-topmost", True)
        except tk.TclError:
            pass
        caja = tk.Frame(self.win, bg=GLOBO, padx=px(16), pady=px(14))
        caja.pack()
        tk.Label(caja, text=self.texto_fn(), bg=GLOBO, fg=BLANCO, font=fuente(10), justify="left",
                 wraplength=px(380)).pack(anchor="w")
        tk.Label(caja, text="Clic en el ícono para fijar o cerrar", bg=GLOBO, fg=AZUL_TEXTO_SUAVE,
                 font=fuente(8)).pack(anchor="w", pady=(px(10), 0))
        self.win.update_idletasks()
        x = self.w.winfo_rootx() + self.w.winfo_width() + px(10)
        y = self.w.winfo_rooty() - px(6)
        # que no se salga de la ventana por la derecha
        limite = top.winfo_rootx() + top.winfo_width() - self.win.winfo_width() - px(12)
        if x > limite:
            x = max(top.winfo_rootx() + px(12), limite)
            y = self.w.winfo_rooty() + self.w.winfo_height() + px(8)
        self.win.geometry(f"+{x}+{y}")
        self.win.bind("<Button-1>", lambda e: (setattr(self, "fijo", False), self.ocultar()))

    def ocultar(self):
        if self.win:
            self.win.destroy()
            self.win = None


# ---------------------------------------------------------------------
def detectar_hoja(img):
    """Busca una hoja (un cuadrilátero claro y grande) en la imagen, como hacen las apps
    de escaneo. Devuelve sus 4 esquinas en coordenadas de la imagen, o None."""
    import cv2
    import numpy as np
    w, h = img.size
    esc = 500.0 / max(w, h)
    gris = np.asarray(img.convert("L").resize((max(1, int(w * esc)), max(1, int(h * esc)))))
    gris = cv2.GaussianBlur(gris, (5, 5), 0)
    area_min = 0.12 * gris.shape[0] * gris.shape[1]
    candidatos = []
    # 1) bordes (sirve con fondos variados); 2) zonas claras (hoja blanca sobre mesa)
    bordes = cv2.dilate(cv2.Canny(gris, 40, 140), np.ones((3, 3), np.uint8))
    candidatos += cv2.findContours(bordes, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)[0]
    _, claro = cv2.threshold(gris, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    candidatos += cv2.findContours(claro, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0]
    mejor, mejor_area = None, area_min
    for c in candidatos:
        area = cv2.contourArea(c)
        if area < mejor_area:
            continue
        aprox = cv2.approxPolyDP(c, 0.02 * cv2.arcLength(c, True), True)
        if len(aprox) == 4 and cv2.isContourConvex(aprox):
            # que no sea el borde de la imagen entera
            x, y, bw, bh = cv2.boundingRect(aprox)
            if bw * bh > 0.97 * gris.shape[0] * gris.shape[1]:
                continue
            mejor, mejor_area = aprox.reshape(4, 2).astype("float32") / esc, area
    return mejor


def _ordenar_esquinas(p):
    """Arriba-izquierda, arriba-derecha, abajo-derecha, abajo-izquierda."""
    import numpy as np
    s, d = p.sum(axis=1), np.diff(p, axis=1).ravel()
    return np.array([p[s.argmin()], p[d.argmin()], p[s.argmax()], p[d.argmax()]], dtype="float32")


def enderezar_hoja(img, esquinas):
    """Recorta la hoja y la endereza (corrige la perspectiva), como un escaneo."""
    import cv2
    import numpy as np
    tl, tr, br, bl = _ordenar_esquinas(esquinas)
    ancho = int(max(np.linalg.norm(br - bl), np.linalg.norm(tr - tl)))
    alto = int(max(np.linalg.norm(tr - br), np.linalg.norm(tl - bl)))
    if ancho < 50 or alto < 50:
        return img
    destino = np.array([[0, 0], [ancho - 1, 0], [ancho - 1, alto - 1], [0, alto - 1]], dtype="float32")
    m = cv2.getPerspectiveTransform(np.array([tl, tr, br, bl]), destino)
    salida = cv2.warpPerspective(np.asarray(img.convert("RGB")), m, (ancho, alto), flags=cv2.INTER_CUBIC)
    return Image.fromarray(salida)


class Camara:
    """Lee la cámara de la computadora con OpenCV en un hilo aparte. Guarda siempre el
    último cuadro; la ventana lo toma cuando lo necesita. OpenCV solo se carga al abrir la
    cámara, así el resto del programa no lo necesita."""

    def __init__(self, indice):
        import cv2
        self.cv2 = cv2
        self.cap = None
        # en Windows DirectShow abre más rápido y deja elegir la resolución; si no anda,
        # Media Foundation
        backends = [cv2.CAP_DSHOW, cv2.CAP_MSMF] if sys.platform == "win32" else [cv2.CAP_ANY]
        for b in backends:
            cap = cv2.VideoCapture(indice, b)
            if cap is not None and cap.isOpened():
                self.cap = cap
                break
            if cap is not None:
                cap.release()
        if self.cap is None:
            raise RuntimeError("no hay cámara")
        # se pide la mayor resolución habitual; la cámara usa la más cercana que tenga
        self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
        ok, cuadro = False, None
        for _ in range(15):  # algunas cámaras tardan unos cuadros en entregar imagen
            ok, cuadro = self.cap.read()
            if ok and cuadro is not None:
                break
        if not ok or cuadro is None:
            self.cap.release()
            raise RuntimeError("la cámara no entrega imagen")
        self._cuadro = cuadro
        self._lock = threading.Lock()
        self._parar = threading.Event()
        self._hilo = threading.Thread(target=self._leer, daemon=True)
        self._hilo.start()

    def _leer(self):
        try:
            while not self._parar.is_set():
                ok, cuadro = self.cap.read()
                if ok and cuadro is not None:
                    with self._lock:
                        self._cuadro = cuadro
                else:
                    self._parar.wait(0.03)
        finally:
            self.cap.release()  # se libera en el mismo hilo que la usa

    def imagen(self):
        """Último cuadro como imagen de Pillow (RGB), o None."""
        with self._lock:
            cuadro = self._cuadro
        if cuadro is None:
            return None
        return Image.fromarray(self.cv2.cvtColor(cuadro, self.cv2.COLOR_BGR2RGB))

    def cerrar(self):
        self._parar.set()


class VentanaCamara(tk.Toplevel):
    """Ventana con la vista de la cámara para sacar varias fotos seguidas. Cada foto se
    agrega a la lista de la herramienta "Fotos a PDF"."""

    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.cam = None
        self.giro = 0
        self.n_fotos = 0
        self._vista = None
        self._miniaturas = []
        self._abriendo = False
        self._tarea = None
        self._esquinas = None       # hoja detectada en la vista (modo escanear)
        self._cuadros = 0
        self.title(f"Cámara · {APP_NOMBRE}")
        self.configure(bg=FONDO)
        self.minsize(px(640), px(520))
        try:
            if sys.platform == "win32":
                self.iconbitmap(recurso("icono.ico"))
        except Exception:
            pass
        self.protocol("WM_DELETE_WINDOW", self.cerrar)

        cont = tk.Frame(self, bg=FONDO)
        cont.pack(fill="both", expand=True, padx=px(18), pady=px(16))
        self.lienzo = tk.Canvas(cont, bg="#000000", highlightthickness=0, bd=0,
                                width=px(720), height=px(405))
        self.lienzo.pack(fill="both", expand=True)
        self.lienzo.bind("<Configure>", lambda e: self._mensaje_si_no_hay())
        self._img_item = self.lienzo.create_image(0, 0, anchor="center")
        self._texto = self.lienzo.create_text(0, 0, text="", fill="#FFFFFF", font=fuente(12, True),
                                              justify="center")
        self._contorno = self.lienzo.create_polygon(0, 0, 0, 0, fill="", outline="#3DDC84",
                                                    width=max(2, px(3)), state="hidden")

        self.tira = tk.Frame(cont, bg=FONDO, height=px(64))
        self.tira.pack(fill="x", pady=(px(10), 0))

        barra = tk.Frame(cont, bg=FONDO)
        barra.pack(fill="x", pady=(px(10), 0))
        tk.Label(barra, text="Cámara", bg=FONDO, fg=TEXTO_SUAVE, font=fuente(9)).pack(side="left")
        self.var_cam = tk.StringVar(value="Cámara 1")
        combo = ttk.Combobox(barra, textvariable=self.var_cam, state="readonly", width=10,
                             values=[f"Cámara {i}" for i in range(1, 5)], font=fuente(10),
                             style="Campo.TCombobox")
        combo.pack(side="left", padx=(px(8), px(10)))
        combo.bind("<<ComboboxSelected>>", lambda e: (combo.selection_clear(), self.abrir()))
        tk.Label(barra, text="Modo", bg=FONDO, fg=TEXTO_SUAVE, font=fuente(9)).pack(side="left")
        modo = leer_preferencia("ModoCamara", "escanear")
        self.var_modo = tk.StringVar(value="Foto normal" if modo == "normal" else "Escanear documento")
        cmodo = ttk.Combobox(barra, textvariable=self.var_modo, state="readonly", width=18,
                             values=["Escanear documento", "Foto normal"], font=fuente(10),
                             style="Campo.TCombobox")
        cmodo.pack(side="left", padx=(px(8), px(10)))

        def cambio_modo(e=None):
            cmodo.selection_clear()
            self._esquinas = None
            guardar_preferencia("ModoCamara", "normal" if self.var_modo.get() == "Foto normal" else "escanear")
        cmodo.bind("<<ComboboxSelected>>", cambio_modo)
        Boton(barra, "↻  Girar", self.girar, tipo="secundario").pack(side="left")
        self.btn_listo = Boton(barra, "Listo", self.cerrar, tipo="secundario")
        self.btn_listo.pack(side="right")
        self.btn_foto = Boton(barra, "Sacar foto", self.sacar_foto, grande=True, icono="camara")
        self.btn_foto.pack(side="right", padx=(0, px(10)))
        self.lbl_cuenta = tk.Label(barra, text="", bg=FONDO, fg=TEXTO_SUAVE, font=fuente(10))
        self.lbl_cuenta.pack(side="right", padx=(0, px(14)))
        tk.Label(cont, text="Escanear documento: la hoja se recorta y endereza sola (borde verde = hoja detectada). "
                            "Barra espaciadora: sacar foto · Escape: cerrar.",
                 bg=FONDO, fg=TEXTO_SUAVE, font=fuente(8)).pack(anchor="w", pady=(px(8), 0))
        self.bind("<space>", lambda e: (self.sacar_foto(), "break")[1])
        self.bind("<Return>", lambda e: (self.sacar_foto(), "break")[1])
        self.bind("<Escape>", lambda e: self.cerrar())

        self.update_idletasks()
        x = app.winfo_rootx() + (app.winfo_width() - self.winfo_width()) // 2
        y = app.winfo_rooty() + (app.winfo_height() - self.winfo_height()) // 3
        self.geometry(f"+{max(0, x)}+{max(0, y)}")
        self.focus_set()
        self.abrir()

    # --- cámara ---
    def abrir(self):
        """Abre (o cambia) la cámara en un hilo: puede tardar un par de segundos."""
        if self._abriendo:
            return
        self._abriendo = True
        if self.cam is not None:
            self.cam.cerrar()
            self.cam = None
        self._mostrar_texto("Abriendo la cámara…")
        self.btn_foto.habilitar(False)
        indice = int(self.var_cam.get().split()[-1]) - 1
        resultado = queue.Queue()

        def trabajo():
            try:
                resultado.put(("ok", Camara(indice)))
            except ImportError:
                resultado.put(("error", "Falta el componente de cámara (OpenCV). Reinstalá el programa."))
            except Exception:
                resultado.put(("error", "No se pudo abrir la cámara.\n\n"
                               "Revisá que esté conectada, que no la use otro programa (Teams, Zoom)\n"
                               "y que Windows permita usarla: Configuración > Privacidad y seguridad >\n"
                               "Cámara > Permitir que las aplicaciones de escritorio accedan a la cámara.\n\n"
                               "Si tenés más de una, probá elegir otra en “Cámara”."))

        def esperar():
            try:
                estado, valor = resultado.get_nowait()
            except queue.Empty:
                self.after(60, esperar)
                return
            self._abriendo = False
            if not self.winfo_exists() or getattr(self, "_cerrada", False):
                if estado == "ok":
                    valor.cerrar()
                return
            if estado == "ok":
                self.cam = valor
                self._mostrar_texto("")
                self.btn_foto.habilitar(True)
                self._refrescar()
            else:
                self._mostrar_texto(valor)

        threading.Thread(target=trabajo, daemon=True).start()
        self.after(60, esperar)

    def _mostrar_texto(self, texto):
        self._mensaje = texto
        self._mensaje_si_no_hay()

    def _mensaje_si_no_hay(self):
        w, h = self.lienzo.winfo_width(), self.lienzo.winfo_height()
        self.lienzo.coords(self._texto, w / 2, h / 2)
        self.lienzo.coords(self._img_item, w / 2, h / 2)
        self.lienzo.itemconfigure(self._texto, text=getattr(self, "_mensaje", ""))
        if getattr(self, "_mensaje", ""):
            self.lienzo.itemconfigure(self._img_item, state="hidden")
        self.lienzo.tag_raise(self._texto)

    def _girada(self, img):
        return img.rotate(-self.giro, expand=True) if self.giro else img

    def _refrescar(self):
        """Muestra el último cuadro (unas 25 veces por segundo)."""
        if self.cam is None or not self.winfo_exists():
            return
        img = self.cam.imagen()
        if img is not None:
            img = self._girada(img)
            iw, ih = img.size
            w = max(1, self.lienzo.winfo_width())
            h = max(1, self.lienzo.winfo_height())
            img.thumbnail((w, h), Image.BILINEAR)
            self._vista = ImageTk.PhotoImage(img)
            self.lienzo.itemconfigure(self._img_item, image=self._vista, state="normal")
            self.lienzo.coords(self._img_item, w / 2, h / 2)
            # modo escanear: se busca la hoja unas 6 veces por segundo y se marca en verde
            self._cuadros += 1
            if self._escanear() and self._cuadros % 4 == 0:
                try:
                    self._esquinas = detectar_hoja(img)
                except Exception:
                    self._esquinas = None
                if self._esquinas is not None:
                    self._esquinas = self._esquinas * (iw / img.size[0])
            if self._escanear() and self._esquinas is not None:
                k = img.size[0] / iw
                x0, y0 = (w - img.size[0]) / 2, (h - img.size[1]) / 2
                puntos = [v for x, y in _ordenar_esquinas(self._esquinas) for v in (x0 + x * k, y0 + y * k)]
                self.lienzo.coords(self._contorno, *puntos)
                self.lienzo.itemconfigure(self._contorno, state="normal")
                self.lienzo.tag_raise(self._contorno)
            else:
                self.lienzo.itemconfigure(self._contorno, state="hidden")
        self._tarea = self.after(40, self._refrescar)

    def _escanear(self):
        return self.var_modo.get() != "Foto normal"

    def girar(self):
        self.giro = (self.giro + 90) % 360

    def sacar_foto(self):
        if self.cam is None or self.app._en_curso:
            return
        img = self.cam.imagen()
        if img is None:
            return
        img = self._girada(img)
        if self._escanear():
            # se vuelve a buscar la hoja en la foto a resolución completa
            try:
                esquinas = detectar_hoja(img)
                if esquinas is not None:
                    img = enderezar_hoja(img, esquinas)
            except Exception:
                pass  # si falla, queda la foto entera
        ruta = self.app._guardar_foto(img)
        if not ruta:
            return
        self.n_fotos += 1
        self.lbl_cuenta.configure(text=f"{self.n_fotos} foto{'s' if self.n_fotos != 1 else ''}")
        # destello blanco: confirma que se sacó la foto
        destello = self.lienzo.create_rectangle(0, 0, self.lienzo.winfo_width(), self.lienzo.winfo_height(),
                                                fill="#FFFFFF", outline="")
        self.after(90, lambda: self.lienzo.delete(destello))
        # miniatura en la tira (las últimas 8)
        with Image.open(ruta) as m:
            mini = m.copy()
        mini.thumbnail((px(96), px(56)))
        foto = ImageTk.PhotoImage(mini)
        self._miniaturas.append(foto)
        tk.Label(self.tira, image=foto, bg=FONDO, bd=0).pack(side="left", padx=(0, px(6)))
        hijos = self.tira.winfo_children()
        if len(hijos) > 8:
            hijos[0].destroy()
            self._miniaturas.pop(0)

    def cerrar(self):
        self._cerrada = True
        if self.app._camara is self:
            self.app._camara = None
        if self._tarea:
            try:
                self.after_cancel(self._tarea)
            except Exception:
                pass
        if self.cam is not None:
            self.cam.cerrar()
            self.cam = None
        try:
            self.destroy()
        except tk.TclError:
            pass


class Presentacion(tk.Canvas):
    """Presentación de Pache Labs al abrir el programa (como la del sitio): fondo negro, el
    frasco entra girando, aparece "Pache.Labs" letra por letra y la pantalla sube como una
    cortina. Dura menos de 2 segundos y se saltea con un clic o una tecla."""

    FONDO = "#0E0F12"

    def __init__(self, app):
        super().__init__(app, bg=self.FONDO, highlightthickness=0, bd=0, cursor="hand2")
        self.app = app
        self.place(x=0, y=0, relwidth=1, relheight=1)
        tk.Misc.lift(self)  # (en un Canvas, lift() mueve dibujos, no el widget)
        self._tareas = []
        self._fin = False
        lado = px(150)
        base = Image.open(recurso("pachelabs.png")).convert("RGBA").resize((lado, lado), Image.LANCZOS)
        fondo = Image.new("RGBA", (lado * 2, lado * 2), _rgb(self.FONDO) + (255,))
        # cuadros del frasco: crece con un pequeño rebote, gira y aparece
        self._cuadros = []
        n = 12
        for i in range(1, n + 1):
            p = i / n
            s = 1 + 2.2 * (p - 1) ** 3 + 1.2 * (p - 1) ** 2      # sube un poco de 1 y vuelve
            escala = 0.4 + 0.6 * s
            img = base.rotate(-25 * (1 - p), resample=Image.BICUBIC, expand=False)
            img = img.resize((max(1, int(lado * escala)), max(1, int(lado * escala))), Image.LANCZOS)
            alfa = img.split()[3].point(lambda v, p=p: int(v * min(1, p * 1.6)))
            img.putalpha(alfa)
            cuadro = fondo.copy()
            cuadro.alpha_composite(img, ((cuadro.width - img.width) // 2, (cuadro.height - img.height) // 2))
            self._cuadros.append(ImageTk.PhotoImage(cuadro))
        self._avatar = self.create_image(0, 0, image=self._cuadros[0])
        self._letras = []
        f = tkfont.Font(family=FUENTE, size=26, weight="bold")
        self._fuente = f
        texto = "Pache.Labs"
        ancho = sum(f.measure(c) for c in texto)
        self._ancho_texto = ancho
        x = -ancho / 2
        for c in texto:
            item = self.create_text(0, 0, text=c, anchor="w", font=f,
                                    fill="#D3261D" if c == "." else "#FFFFFF", state="hidden")
            self._letras.append((item, x))
            x += f.measure(c)
        self.bind("<Configure>", lambda e: self._ubicar())
        self.bind("<Button-1>", lambda e: self.terminar())
        self.bind("<Key>", lambda e: self.terminar())
        self.focus_set()
        self._ubicar()
        for i in range(len(self._cuadros)):
            self._despues(40 * i, lambda i=i: self.itemconfigure(self._avatar, image=self._cuadros[i]))
        for k, (item, _) in enumerate(self._letras):
            self._despues(560 + 45 * k, lambda item=item: self.itemconfigure(item, state="normal"))
        self._despues(1450, self._salir)

    def _despues(self, ms, f):
        self._tareas.append(self.after(ms, f))

    def _ubicar(self):
        w, h = self.winfo_width(), self.winfo_height()
        cy = h / 2 - px(20)
        self.coords(self._avatar, w / 2, cy)
        for item, dx in self._letras:
            self.coords(item, w / 2 + dx, cy + px(120))

    def _salir(self, paso=0):
        """La pantalla negra sube como una cortina (unos 350 ms)."""
        if self._fin:
            return
        pasos = 14
        if paso > pasos:
            self.terminar()
            return
        t = paso / pasos
        t = t * t * (3 - 2 * t)  # suave al empezar y al terminar
        self.place_configure(y=-int(self.winfo_height() * t))
        self._despues(25, lambda: self._salir(paso + 1))

    def terminar(self):
        if self._fin:
            return
        self._fin = True
        for tarea in self._tareas:
            try:
                self.after_cancel(tarea)
            except tk.TclError:
                pass
        self.destroy()


class App(tk.Tk):
    def __init__(self, presentacion=False):
        super().__init__()
        self.dnd = False
        if TkinterDnD is not None:
            try:
                TkinterDnD._require(self)
                self.dnd = True
            except Exception:
                self.dnd = False
        self.zona_vacia = None
        self._pend_salida = None
        self._en_curso = False      # hay una operación procesándose
        self._cancelar = False      # se pidió cerrar la app durante una operación
        self._evento_cancelar = threading.Event()  # el motor lo revisa en cada página
        self._info_cache = {}       # (ruta, fecha, tamaño) -> páginas/cifrado
        self._foco_fila = None      # (botón, fila) que recibe el foco al redibujar la lista
        # casillas "Abrir al terminar" y "Limpiar la lista al terminar": tildadas la
        # primera vez; después se recuerda lo que eligió el usuario
        self.pref_abrir = leer_preferencia("AbrirAlTerminar", "1") == "1"
        self.pref_limpiar = leer_preferencia("LimpiarAlTerminar", "1") == "1"
        self._aviso_w = None
        self._camara = None         # ventana de la cámara (herramienta "Fotos a PDF")
        self._dir_fotos = None      # carpeta temporal con las fotos sacadas
        self._n_foto = 0
        limpiar_fotos_viejas()
        self.protocol("WM_DELETE_WINDOW", self._al_cerrar)
        self._panel_id = 0          # identifica el panel que lanzó la operación
        global ESCALA
        try:
            ESCALA = max(1.0, self.winfo_fpixels("1i") / 96.0)
        except Exception:
            ESCALA = 1.0
        # tema: "sistema" (sigue a Windows, es lo inicial), "claro" u "oscuro"; se recuerda
        self.modo_tema = leer_preferencia("ModoTema", "sistema")
        if self.modo_tema not in ("sistema", "claro", "oscuro"):
            self.modo_tema = "sistema"
        aplicar_tema(tema_sistema() if self.modo_tema == "sistema" else self.modo_tema == "oscuro")
        self.title(APP_NOMBRE)
        self.geometry(f"{px(1060)}x{px(720)}")
        self.minsize(px(900), px(680))
        self.configure(bg=FONDO)
        self._icono()
        self._estilos()

        self.archivos = []
        self.items_menu = {}
        self.herr_actual = None
        self.ultimo_destino = None
        self.globo = None
        self.menu_colapsado = leer_preferencia("MenuColapsado", "0") == "1"

        self._sidebar()
        for atajo in ("<Control-f>", "<Control-F>", "<Control-k>", "<Control-K>"):
            self.bind(atajo, lambda e: (self.alternar_menu(buscar=True), "break")[1])
        self.main = tk.Frame(self, bg=FONDO)
        self.main.pack(side="left", fill="both", expand=True)
        self.seleccionar(HERRAMIENTAS[0])
        self._ajustar_tamano()
        self._barra_titulo()
        self.after(5000, self._vigilar_tema)
        if presentacion:
            try:
                Presentacion(self)
            except Exception:
                # la presentación es un adorno: si falla, se quita y el programa se abre igual
                for w in self.winfo_children():
                    if isinstance(w, Presentacion):
                        w.destroy()

    def _alto_menu(self):
        """Alto que necesita el menú lateral (tiene tamaño fijo, pack_propagate apagado):
        lo que pide cada elemento más sus márgenes, y un pequeño respiro."""
        self.update_idletasks()
        necesita = px(16)
        for w in self.side.winfo_children():
            pady = w.pack_info().get("pady", 0)
            if isinstance(pady, (tuple, list)):
                margen = sum(int(v) for v in pady)
            else:
                partes = [int(float(v)) for v in str(pady).replace("{", "").replace("}", "").split()]
                margen = sum(partes) if len(partes) > 1 else 2 * (partes[0] if partes else 0)
            necesita += w.winfo_reqheight() + margen
        return necesita

    def _ajustar_tamano(self):
        """Abre la ventana con la altura justa para que el menú lateral entre completo
        (con escalado de pantalla de 125 % o 150 % el menú necesita más alto). Si la
        pantalla no alcanza, usa el menú compacto y, si hace falta, abre maximizada. La
        ventana no deja achicarse a menos de lo que necesita el menú."""
        try:
            disponible = self.winfo_screenheight() - px(90)   # barra de tareas y título
            necesita = self._alto_menu()
            if necesita > disponible:
                actual = self.herr_actual
                self.side.destroy()
                self.items_menu = {}
                self._sidebar(compacto=True)
                if actual is not None and actual["id"] in self.items_menu:
                    self.items_menu[actual["id"]].set_activo(True)
                necesita = self._alto_menu()
            ancho = max(px(1060), self.winfo_width())
            alto = max(px(720), necesita)
            self.minsize(px(900), min(max(px(680), necesita), disponible))
            if alto > disponible:
                if sys.platform == "win32":
                    self.state("zoomed")
                    return
                alto = disponible
            x = max(0, (self.winfo_screenwidth() - ancho) // 2)
            y = max(0, (disponible - alto) // 2)
            self.geometry(f"{ancho}x{alto}+{x}+{y}")
        except Exception:
            pass  # si algo falla, queda el tamaño por defecto

    # ---------- apariencia ----------
    def _icono(self):
        try:
            if sys.platform == "win32":
                self.iconbitmap(recurso("icono.ico"))
            else:
                self._ico = ImageTk.PhotoImage(Image.open(recurso("icono.png")))
                self.iconphoto(True, self._ico)
        except Exception:
            pass

    def _estilos(self):
        s = ttk.Style(self)
        s.theme_use("clam")
        # Combobox que se funde con el campo redondeado que lo contiene
        s.configure("Campo.TCombobox", fieldbackground=CAMPO, background=CAMPO, foreground=TEXTO,
                    bordercolor=CAMPO, lightcolor=CAMPO, darkcolor=CAMPO, arrowcolor=TEXTO_SUAVE,
                    arrowsize=px(13), padding=(px(2), px(4)), relief="flat", borderwidth=0)
        s.map("Campo.TCombobox",
              # el tema "clam" pinta el texto con el color de selección (blanco) cuando
              # el desplegable tiene el foco; se fuerza el color de texto normal
              foreground=[("readonly", "focus", TEXTO), ("readonly", TEXTO), ("focus", TEXTO), ("disabled", GRIS_DESACTIVADO)],
              fieldbackground=[("readonly", "focus", CAMPO), ("readonly", CAMPO)], background=[("active", CAMPO), ("pressed", CAMPO), ("readonly", CAMPO)],
              bordercolor=[("focus", CAMPO)], lightcolor=[("focus", CAMPO)], darkcolor=[("focus", CAMPO)],
              selectbackground=[("readonly", "focus", CAMPO), ("readonly", CAMPO), ("focus", CAMPO)],
              selectforeground=[("readonly", "focus", TEXTO), ("readonly", TEXTO), ("focus", TEXTO)],
              arrowcolor=[("active", AZUL)])
        self.option_add("*TCombobox*Listbox.background", TARJETA)
        self.option_add("*TCombobox*Listbox.foreground", TEXTO)
        self.option_add("*TCombobox*Listbox.selectBackground", BOTON)
        self.option_add("*TCombobox*Listbox.selectForeground", BLANCO)
        self.option_add("*TCombobox*Listbox.font", fuente(10))
        self.option_add("*TCombobox*Listbox.relief", "flat")
        self.option_add("*TCombobox*Listbox.borderWidth", 0)
        s.configure("Fina.Horizontal.TProgressbar", troughcolor=BORDE, background=AZUL, thickness=px(5),
                    bordercolor=BORDE, lightcolor=AZUL, darkcolor=AZUL, borderwidth=0)

    def _logo_img(self, ancho):
        """Logo de la app (PNG con fondo transparente) al tamaño pedido. En el tema claro
        (menú rojo) lleva un borde blanco parejo y redondeado alrededor de la silueta, tipo
        calco, para que la hoja roja no se pierda; en el oscuro, una sombra suave."""
        from PIL import ImageFilter
        base = Image.open(recurso("logo.png")).convert("RGBA")
        m = max(3, ancho // 10)                       # margen para el borde o la sombra
        lado = ancho + 2 * m
        if TEMA_OSCURO:
            img = base.resize((ancho, ancho), Image.LANCZOS)
            lienzo = Image.new("RGBA", (lado, lado), _rgb(LATERAL) + (255,))
            sombra = Image.new("RGBA", img.size, (0, 0, 0, 255))
            sombra.putalpha(img.split()[3].point(lambda v: v * 0.55))
            capa = Image.new("RGBA", lienzo.size, (0, 0, 0, 0))
            capa.paste(sombra, (m, m + max(1, m // 2)))
            lienzo.alpha_composite(capa.filter(ImageFilter.GaussianBlur(m * 0.6)))
            lienzo.alpha_composite(img, (m, m))
            return ImageTk.PhotoImage(lienzo)
        # todo se arma a 4 veces el tamaño y se achica al final (bordes suaves)
        f = 4
        L, A, M = lado * f, ancho * f, m * f
        grande = base.resize((A, A), Image.LANCZOS)
        silueta = Image.new("L", (L, L), 0)
        silueta.paste(grande.split()[3].point(lambda v: 255 if v > 128 else 0), (M, M))
        # dilatación redonda: desenfoque + umbral (sin las esquinas cuadradas de un filtro
        # de máximo) y un segundo desenfoque corto para el antialias
        g = max(2, ancho // 20) * f
        borde = silueta.filter(ImageFilter.GaussianBlur(g * 0.55)).point(lambda v: 255 if v > 12 else 0)
        borde = borde.filter(ImageFilter.GaussianBlur(f * 0.6))
        lienzo = Image.new("RGBA", (L, L), _rgb(LATERAL) + (255,))
        blanco = Image.new("RGBA", (L, L), (255, 255, 255, 255))
        blanco.putalpha(borde)
        lienzo.alpha_composite(blanco)
        lienzo.alpha_composite(grande, (M, M))
        return ImageTk.PhotoImage(lienzo.resize((lado, lado), Image.LANCZOS))

    def _boton_lateral(self, padre, dibujar, comando):
        """Botón cuadrado con un ícono dibujado (menú, lupa) para el menú lateral."""
        t = px(34)
        c = tk.Canvas(padre, width=t, height=t, bg=LATERAL, highlightthickness=0, bd=0,
                      cursor="hand2", takefocus=1)
        c._hov = redondeado(t, t, px(8), LATERAL_HOVER)
        c._foc = redondeado(t, t, px(8), LATERAL_ACTIVO)
        fondo = c.create_image(0, 0, anchor="nw", image=c._hov, state="hidden")
        dibujar(c, t)
        c.bind("<Enter>", lambda e: c.itemconfigure(fondo, image=c._hov, state="normal"))
        c.bind("<Leave>", lambda e: c.itemconfigure(fondo, state="normal" if c.focus_get() is c else "hidden",
                                                    image=c._foc))
        c.bind("<FocusIn>", lambda e: c.itemconfigure(fondo, image=c._foc, state="normal"))
        c.bind("<FocusOut>", lambda e: c.itemconfigure(fondo, state="hidden"))
        c.bind("<Button-1>", lambda e: comando())
        for tecla in ("<Return>", "<KP_Enter>", "<space>"):
            c.bind(tecla, lambda e: (comando(), "break")[1])
        return c

    @staticmethod
    def _dibujar_menu(c, t, abierto):
        """Ícono de tres rayas (menú cerrado) o de flecha hacia la izquierda (cerrar menú)."""
        g = max(2, px(2))
        if abierto:
            c.create_line(t * 0.62, t * 0.30, t * 0.42, t * 0.50, t * 0.62, t * 0.70, fill=MENU_TEXTO,
                          width=g, capstyle="round", joinstyle="round")
        else:
            for y in (0.34, 0.50, 0.66):
                c.create_line(t * 0.28, t * y, t * 0.72, t * y, fill=MENU_TEXTO, width=g, capstyle="round")

    @staticmethod
    def _dibujar_lupa(c, t):
        g = max(2, px(2))
        c.create_oval(t * 0.28, t * 0.28, t * 0.58, t * 0.58, outline=MENU_TEXTO, width=g)
        c.create_line(t * 0.55, t * 0.55, t * 0.72, t * 0.72, fill=MENU_TEXTO, width=g, capstyle="round")

    def alternar_menu(self, buscar=False):
        """Colapsa o expande el menú lateral (se recuerda). Con buscar=True lo expande y
        pone el cursor en el buscador."""
        if buscar and not self.menu_colapsado:
            self._campo_buscar.focus_set()
            return
        self.menu_colapsado = not self.menu_colapsado
        guardar_preferencia("MenuColapsado", "1" if self.menu_colapsado else "0")
        compacto = getattr(self, "_compacto", False)
        self.side.destroy()
        self.items_menu = {}
        self._sidebar(compacto=compacto)
        if not self.menu_colapsado and not compacto and self._alto_menu() > self.winfo_height():
            self.side.destroy()   # en pantallas bajas, el menú expandido va compacto
            self.items_menu = {}
            self._sidebar(compacto=True)
        if self.herr_actual and self.herr_actual["id"] in self.items_menu:
            self.items_menu[self.herr_actual["id"]].set_activo(True)
        if buscar and not self.menu_colapsado:
            self._campo_buscar.focus_set()

    def _sidebar_colapsado(self):
        """Menú colapsado: una franja angosta con el botón para expandirlo, el logo y la
        lupa del buscador. Deja más lugar para la lista de archivos."""
        side = tk.Frame(self, bg=LATERAL, width=px(64))
        if getattr(self, "main", None) is not None:
            side.pack(side="left", fill="y", before=self.main)
        else:
            side.pack(side="left", fill="y")
        self.side = side
        side.pack_propagate(False)
        self._btn_menu = self._boton_lateral(side, lambda c, t: self._dibujar_menu(c, t, False),
                                             self.alternar_menu)
        self._btn_menu.pack(pady=(px(14), px(10)))
        self._logo = self._logo_img(px(40))
        tk.Label(side, image=self._logo, bg=LATERAL, bd=0).pack(pady=(0, px(10)))
        self._boton_lateral(side, self._dibujar_lupa, lambda: self.alternar_menu(buscar=True)).pack()


    def _enlace_lateral(self, padre, texto, comando, negrita=True):
        """Texto del pie del menú que funciona como botón (mouse y teclado)."""
        l = tk.Label(padre, text=texto, bg=LATERAL, fg=AZUL_TEXTO_SUAVE, font=fuente(8, negrita),
                     cursor="hand2", takefocus=1, highlightthickness=px(1), highlightbackground=LATERAL,
                     highlightcolor=BLANCO)
        l.bind("<Button-1>", lambda e: comando())
        for tecla in ("<Return>", "<KP_Enter>", "<space>"):
            l.bind(tecla, lambda e: (comando(), "break")[1])
        l.bind("<Enter>", lambda e: l.configure(fg=BLANCO))
        l.bind("<Leave>", lambda e: l.configure(fg=AZUL_TEXTO_SUAVE))
        return l

    def _buscador(self, side, compacto):
        """Campo para buscar una herramienta por nombre o por lo que hace ("juntar",
        "contraseña", "foto"...). Enter abre la primera que coincide; Escape lo vacía."""
        caja = Tarjeta(side, relleno=BUSCADOR, borde=BUSCADOR, radio=px(10), bg_padre=LATERAL)
        caja.pack(fill="x", padx=px(14), pady=(0, px(8 if compacto else 12)))
        fila = tk.Frame(caja, bg=BUSCADOR)
        fila.pack(fill="x", padx=px(10), pady=px(5 if compacto else 7))
        d = px(16)
        lupa = tk.Canvas(fila, width=d, height=d, bg=BUSCADOR, highlightthickness=0, bd=0)
        lupa.pack(side="left")
        lupa.create_oval(px(1), px(1), d * 0.68, d * 0.68, outline=BUSCADOR_SUGERENCIA, width=max(2, px(2)))
        lupa.create_line(d * 0.62, d * 0.62, d - px(1), d - px(1), fill=BUSCADOR_SUGERENCIA,
                         width=max(2, px(2)), capstyle="round")
        self.var_buscar = tk.StringVar()
        campo = tk.Entry(fila, textvariable=self.var_buscar, bd=0, relief="flat", bg=BUSCADOR,
                         fg=BUSCADOR_TEXTO, insertbackground=BUSCADOR_TEXTO, font=fuente(10),
                         highlightthickness=0, disabledbackground=BUSCADOR)
        campo.pack(side="left", fill="x", expand=True, padx=(px(8), 0))
        sugerencia = tk.Label(fila, text="Buscar herramienta", bg=BUSCADOR, fg=BUSCADOR_SUGERENCIA,
                              font=fuente(10), cursor="xterm")
        sugerencia.place(in_=campo, x=0, rely=0.5, anchor="w")
        sugerencia.bind("<Button-1>", lambda e: campo.focus_set())
        lupa.bind("<Button-1>", lambda e: campo.focus_set())
        self._campo_buscar = campo

        def cambio(*a):
            if self.var_buscar.get():
                sugerencia.place_forget()
            else:
                sugerencia.place(in_=campo, x=0, rely=0.5, anchor="w")
            self._filtrar_menu()

        self.var_buscar.trace_add("write", cambio)
        campo.bind("<Return>", lambda e: self._abrir_primera())
        campo.bind("<KP_Enter>", lambda e: self._abrir_primera())
        campo.bind("<Down>", lambda e: self._enfocar_primera())
        campo.bind("<Escape>", lambda e: self.var_buscar.set(""))

    def _visibles_menu(self):
        q = sin_tildes(self.var_buscar.get()).split() if getattr(self, "var_buscar", None) else []
        return [h for h in HERRAMIENTAS if all(p in texto_busqueda(h) for p in q)]

    def _filtrar_menu(self):
        visibles = self._visibles_menu()
        for h in HERRAMIENTAS:
            self.items_menu[h["id"]].pack_forget()
        self._sin_resultados.pack_forget()
        for h in visibles:
            self.items_menu[h["id"]].pack(pady=self._pady_item)
        if not visibles:
            self._sin_resultados.pack(pady=px(10))

    def _abrir_primera(self):
        visibles = self._visibles_menu()
        if visibles:
            self.seleccionar(visibles[0])
            self.items_menu[visibles[0]["id"]].focus_set()
        return "break"

    def _enfocar_primera(self):
        visibles = self._visibles_menu()
        if visibles:
            self.items_menu[visibles[0]["id"]].focus_set()
        return "break"

    def _mover_menu(self, h, paso):
        """Flechas arriba/abajo en el menú: pasa a la herramienta anterior o siguiente (de
        las que muestra el buscador). Desde la primera, flecha arriba vuelve al buscador."""
        visibles = self._visibles_menu()
        if h not in visibles:
            return "break"
        i = visibles.index(h) + paso
        if i < 0:
            self._campo_buscar.focus_set()
        elif i < len(visibles):
            self.items_menu[visibles[i]["id"]].focus_set()
        return "break"

    def _sidebar(self, compacto=False):
        """Menú lateral. En modo compacto (pantallas con poco alto, por ejemplo 1080 píxeles
        con escalado de 150 %) usa logo y opciones más bajos para que entre completo."""
        self._compacto = compacto
        if self.menu_colapsado:
            self._sidebar_colapsado()
            return
        ancho = px(244)
        side = tk.Frame(self, bg=LATERAL, width=ancho)
        if getattr(self, "main", None) is not None:
            side.pack(side="left", fill="y", before=self.main)
        else:
            side.pack(side="left", fill="y")
        self.side = side
        side.pack_propagate(False)

        marca = tk.Frame(side, bg=LATERAL)
        marca.pack(fill="x", padx=(px(12), px(8)), pady=(px(8), px(6)) if compacto else (px(16), px(12)))
        self._logo = self._logo_img(px(40 if compacto else 48))
        tk.Label(marca, image=self._logo, bg=LATERAL, bd=0).pack(side="left")
        self._btn_menu = self._boton_lateral(marca, lambda c, t: self._dibujar_menu(c, t, True),
                                             self.alternar_menu)
        self._btn_menu.pack(side="right")
        textos = tk.Frame(marca, bg=LATERAL)
        textos.pack(side="left", padx=(px(6), 0))
        tk.Label(textos, text=APP_NOMBRE, bg=LATERAL, fg=BLANCO,
                 font=fuente(14 if compacto else 16, True)).pack(anchor="w")
        tk.Label(textos, text="DE " + APP_MARCA.upper(), bg=LATERAL, fg=AZUL_TEXTO_SUAVE,
                 font=fuente(7, True)).pack(anchor="w")

        self._buscador(side, compacto)

        lista = tk.Frame(side, bg=LATERAL)
        lista.pack(fill="x", padx=px(12))
        self._pady_item = 0 if compacto else px(1)
        for h in HERRAMIENTAS:
            it = ItemMenu(lista, h["titulo"], lambda h=h: self.seleccionar(h), ancho - px(24),
                          alto=27 if compacto else 33)
            it.pack(pady=self._pady_item)
            it.bind("<Down>", lambda e, h=h: self._mover_menu(h, 1))
            it.bind("<Up>", lambda e, h=h: self._mover_menu(h, -1))
            self.items_menu[h["id"]] = it
        self._sin_resultados = tk.Label(lista, text="No hay herramientas con ese nombre",
                                        bg=LATERAL, fg=AZUL_TEXTO_SUAVE, font=fuente(9))

        pie_side = tk.Frame(side, bg=LATERAL)
        pie_side.pack(side="bottom", fill="x", pady=(0, px(6 if compacto else 12)), padx=px(20))
        try:  # mini sello de Pache Labs
            self._mini_pachelabs = ImageTk.PhotoImage(
                Image.open(recurso("pachelabs.png")).convert("RGBA").resize((px(18), px(18)), Image.LANCZOS))
            tk.Label(pie_side, image=self._mini_pachelabs, bg=LATERAL, bd=0).pack(side="left", padx=(0, px(6)))
        except Exception:
            pass
        tk.Label(pie_side, text=f"Versión {APP_VERSION}", bg=LATERAL, fg=PIE_TEXTO,
                 font=fuente(8)).pack(side="left")
        tk.Label(pie_side, text="  ·  ", bg=LATERAL, fg=PIE_TEXTO, font=fuente(8)).pack(side="left")
        self._enlace_lateral(pie_side, "Acerca de", self.acerca_de).pack(side="left")
        tema = tk.Frame(side, bg=LATERAL)
        tema.pack(side="bottom", fill="x", pady=(0, px(6)), padx=px(20))
        texto_tema = {"sistema": "◐  Tema: automático (Windows)", "claro": "☀  Tema: claro",
                      "oscuro": "☾  Tema: oscuro"}[getattr(self, "modo_tema", "sistema")]
        self._enlace_lateral(tema, texto_tema, self.cambiar_tema, negrita=False).pack(side="left")
        tk.Label(side, text="🔒  Sin conexión · tus archivos nunca\n     salen de esta computadora",
                 bg=LATERAL, fg=AZUL_TEXTO_SUAVE, font=fuente(8), justify="left").pack(
            side="bottom", pady=(0, px(4)), padx=px(20), anchor="w")

    # ---------- tema claro / oscuro ----------
    def cambiar_tema(self):
        if self._en_curso:
            try:
                self.estado.configure(text="Esperá a que termine la operación en curso.", fg=ROJO)
            except Exception:
                pass
            return
        # Automático (Windows) → Claro → Oscuro → Automático...
        self.modo_tema = {"sistema": "claro", "claro": "oscuro", "oscuro": "sistema"}[self.modo_tema]
        guardar_preferencia("ModoTema", self.modo_tema)
        aplicar_tema(tema_sistema() if self.modo_tema == "sistema" else self.modo_tema == "oscuro")
        self._reconstruir()

    def _vigilar_tema(self):
        """Con el tema en Automático, si se cambia el modo claro/oscuro de Windows con la app
        abierta, la app lo sigue (salvo que haya una operación en curso)."""
        try:
            if self.modo_tema == "sistema" and not self._en_curso and tema_sistema() != TEMA_OSCURO:
                aplicar_tema(tema_sistema())
                self._reconstruir()
        except Exception:
            pass
        self.after(5000, self._vigilar_tema)

    def _reconstruir(self):
        """Vuelve a armar la ventana con los colores del tema actual. Conserva la
        herramienta elegida y la lista de archivos."""
        h, archivos = self.herr_actual, list(self.archivos)
        camara_abierta = self._camara is not None
        self._cerrar_camara()
        if self.globo:
            self.globo.ocultar()
        for w in self.winfo_children():
            try:
                w.destroy()
            except tk.TclError:
                pass
        self.main, self.items_menu, self.herr_actual, self.globo = None, {}, None, None
        self.configure(bg=FONDO)
        self._estilos()
        self._sidebar(compacto=getattr(self, "_compacto", False))
        self.main = tk.Frame(self, bg=FONDO)
        self.main.pack(side="left", fill="both", expand=True)
        self.seleccionar(h or HERRAMIENTAS[0])
        self.archivos = archivos
        self._refrescar_lista()
        self._barra_titulo()
        if camara_abierta and self.herr_actual.get("camara"):
            self.after(200, self.abrir_camara)  # se vuelve a abrir con los colores nuevos
        try:  # que el menú siga entrando completo con los textos del tema nuevo
            necesita = self._alto_menu()
            disponible = self.winfo_screenheight() - px(90)
            self.minsize(px(900), min(max(px(680), necesita), disponible))
            if self.state() == "normal" and self.winfo_height() < necesita:
                self.geometry(f"{self.winfo_width()}x{min(necesita, disponible)}")
        except Exception:
            pass

    def _barra_titulo(self):
        """En Windows 10/11 pinta la barra de título oscura en modo oscuro."""
        if sys.platform != "win32":
            return
        try:
            import ctypes
            self.update_idletasks()
            hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
            valor = ctypes.c_int(1 if TEMA_OSCURO else 0)
            for atributo in (20, 19):  # DWMWA_USE_IMMERSIVE_DARK_MODE (Windows 11 / 10 viejos)
                if ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, atributo, ctypes.byref(valor),
                                                              ctypes.sizeof(valor)) == 0:
                    break
        except Exception:
            pass

    # ---------- Acerca de ----------
    def acerca_de(self):
        if getattr(self, "_acerca", None) is not None and self._acerca.winfo_exists():
            self._acerca.lift()
            return
        win = tk.Toplevel(self)
        self._acerca = win
        win.title(f"Acerca de {APP_NOMBRE}")
        win.configure(bg=FONDO)
        win.resizable(False, False)
        win.transient(self)
        try:
            if sys.platform == "win32":
                win.iconbitmap(recurso("icono.ico"))
        except Exception:
            pass
        caja = tk.Frame(win, bg=FONDO, padx=px(28), pady=px(22))
        caja.pack(fill="both", expand=True)
        cabeza = tk.Frame(caja, bg=FONDO)
        cabeza.pack(fill="x", pady=(0, px(14)))
        titulos = tk.Frame(cabeza, bg=FONDO)
        titulos.pack(side="left", anchor="n")
        tk.Label(titulos, text=APP_NOMBRE, bg=FONDO, fg=TEXTO, font=fuente(18, True)).pack(anchor="w")
        tk.Label(titulos, text=f"Versión {APP_VERSION}  ·  Herramientas PDF que funcionan sin conexión",
                 bg=FONDO, fg=TEXTO_SUAVE, font=fuente(10)).pack(anchor="w", pady=(px(2), 0))
        # sello de Pache Labs (el frasco con lentes) con el nombre
        sello = tk.Frame(cabeza, bg=FONDO)
        sello.pack(side="right", anchor="n", padx=(px(20), 0))
        try:
            self._img_pachelabs = ImageTk.PhotoImage(
                Image.open(recurso("pachelabs.png")).convert("RGBA").resize((px(56), px(56)), Image.LANCZOS))
            tk.Label(sello, image=self._img_pachelabs, bg=FONDO, bd=0).pack(side="left")
        except Exception:
            pass
        nombre = tk.Frame(sello, bg=FONDO)
        nombre.pack(side="left", padx=(px(8), 0))
        for parte, color in (("Pache", TEXTO), (".", BOTON), ("Labs", TEXTO)):
            tk.Label(nombre, text=parte, bg=FONDO, fg=color, font=fuente(13, True), bd=0, padx=0).pack(side="left")
        filas = [
            ("Hecho por", "Nicolás Emanuel Pacheco (Pache), " + APP_MARCA),
            ("Licencia", "Gratis y de código abierto (GNU AGPL-3.0). Se entrega sin garantía; "
                         "el texto completo está en LICENSE.txt."),
            ("Código fuente", "Disponible para cada versión en la página del proyecto."),
            ("Contacto", "pache.labs@gmail.com: errores, ideas y sugerencias."),
            ("Componentes", "PyMuPDF / MuPDF (AGPL-3.0) · Pillow (MIT-CMU) · OpenCV (Apache-2.0) · "
                            "NumPy (BSD) · tkinterdnd2 (MIT) · Python (PSF) · Tcl/Tk (BSD)"),
            ("Privacidad", "No usa internet. Ojo: si guardás en una carpeta sincronizada con OneDrive, "
                           "OneDrive sí la sube a la nube."),
            ("Compilación", texto_modo_compilacion()),
        ]
        tabla = tk.Frame(caja, bg=FONDO)
        tabla.pack(fill="x")
        for i, (k, v) in enumerate(filas):
            tk.Label(tabla, text=k, bg=FONDO, fg=TEXTO_SUAVE, font=fuente(9, True), anchor="nw",
                     justify="left").grid(row=i, column=0, sticky="nw", padx=(0, px(14)), pady=px(4))
            tk.Label(tabla, text=v, bg=FONDO, fg=TEXTO, font=fuente(10), anchor="w", justify="left",
                     wraplength=px(400)).grid(row=i, column=1, sticky="w", pady=px(4))
        botones = tk.Frame(caja, bg=FONDO)
        botones.pack(fill="x", pady=(px(18), 0))
        Boton(botones, "Cerrar", win.destroy).pack(side="right")
        # abre la página de Cafecito en el navegador (el programa en sí no se conecta)
        Boton(botones, "☕  Invitame un cafecito", lambda: abrir_archivo("https://cafecito.app/pachelabs"),
              tipo="secundario").pack(side="left")
        Boton(botones, "Licencia", lambda: abrir_archivo(archivo_base("LICENSE.txt")),
              tipo="secundario").pack(side="right", padx=(0, px(10)))
        Boton(botones, "Licencias de terceros", lambda: abrir_archivo(archivo_base("LICENCIAS_TERCEROS.txt")),
              tipo="secundario").pack(side="right", padx=(0, px(10)))
        win.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() - win.winfo_width()) // 2
        y = self.winfo_rooty() + (self.winfo_height() - win.winfo_height()) // 3
        win.geometry(f"+{max(0, x)}+{max(0, y)}")
        win.bind("<Escape>", lambda e: win.destroy())
        win.grab_set()

    # ---------- panel de herramienta ----------
    def seleccionar(self, h):
        if self._en_curso:
            # una operación a la vez: no se cambia de herramienta hasta que termine
            try:
                self.estado.configure(text="Esperá a que termine la operación en curso.", fg=ROJO)
            except Exception:
                pass
            return
        self._panel_id += 1
        self._cerrar_camara()
        if self.globo:
            self.globo.ocultar()
        if self.herr_actual and self.herr_actual["id"] in self.items_menu:
            self.items_menu[self.herr_actual["id"]].set_activo(False)
        self._cerrar_aviso()
        self.herr_actual = h
        if h["id"] in self.items_menu:
            self.items_menu[h["id"]].set_activo(True)
        self.archivos = []
        self.ultimo_destino = None
        for w in self.main.winfo_children():
            w.destroy()
        self._panel(h)

    def _panel(self, h):
        cont = tk.Frame(self.main, bg=FONDO)
        cont.pack(fill="both", expand=True, padx=px(34), pady=(px(26), px(24)))

        # título + ícono de información
        cab = tk.Frame(cont, bg=FONDO)
        cab.pack(anchor="w", fill="x")
        tk.Label(cab, text=h["titulo"], bg=FONDO, fg=TEXTO, font=fuente(20, True)).pack(side="left")
        d = px(22)
        info = tk.Label(cab, image=circulo_info(d, INFO_FONDO, AZUL), bg=FONDO, bd=0, cursor="hand2")
        info.pack(side="left", padx=(px(12), 0), pady=(px(4), 0))
        self.globo = Globo(info, lambda: AYUDA.get(h["id"], h["desc"]))
        # re-enganchar el hover del color después de que Globo definió los suyos
        info.bind("<Enter>", lambda e: info.configure(image=circulo_info(d, BOTON, BLANCO)), add="+")
        info.bind("<Leave>", lambda e: info.configure(image=circulo_info(d, INFO_FONDO, AZUL)), add="+")
        opciones = tk.Frame(cab, bg=FONDO)
        opciones.pack(side="right", pady=(px(6), 0))
        Casilla(opciones, "Limpiar la lista al terminar", self.pref_limpiar,
                lambda v: self._cambiar_pref("limpiar", v)).pack(side="right", padx=(px(14), 0))
        Casilla(opciones, "Abrir al terminar", self.pref_abrir,
                lambda v: self._cambiar_pref("abrir", v)).pack(side="right")

        tk.Label(cont, text=h["desc"], bg=FONDO, fg=TEXTO_SUAVE, font=fuente(10)).pack(anchor="w", pady=(px(2), px(16)))

        multi = h["entrada"] in ("multi", "imagenes")

        # --- tarjeta de archivos ---
        card = Tarjeta(cont)
        self.card_archivos = card
        card.pack(fill="both", expand=multi)
        barra = tk.Frame(card, bg=TARJETA)
        barra.pack(fill="x", padx=px(18), pady=(px(16), px(10)))
        txt = {"multi": "＋  Agregar PDF", "pdf": "Elegir PDF", "imagenes": "＋  Agregar imágenes"}[h["entrada"]]
        self.btn_agregar = Boton(barra, "Abrir cámara" if h.get("camara") else txt, self.agregar,
                                 bg_padre=TARJETA, icono="camara" if h.get("camara") else None)
        self.btn_agregar.pack(side="left")
        self.btn_limpiar = Boton(barra, "Quitar todos", self.limpiar, tipo="secundario", bg_padre=TARJETA)
        self.lbl_cuenta = tk.Label(barra, text="", bg=TARJETA, fg=TEXTO_SUAVE, font=fuente(9))
        self.lbl_cuenta.pack(side="right")
        tk.Frame(card, bg=SEPARADOR, height=1).pack(fill="x", padx=px(18))

        zona = tk.Frame(card, bg=TARJETA)
        zona.pack(fill="both", expand=True, padx=(px(18), px(8)), pady=(px(4), px(14)))
        self.lienzo = tk.Canvas(zona, bg=TARJETA, highlightthickness=0, bd=0,
                                height=px(260) if multi else px(66))
        self.scroll = ScrollFino(zona, self.lienzo.yview)
        self.scroll.pack(side="right", fill="y")
        self.lienzo.pack(side="left", fill="both", expand=True)
        self.lienzo.configure(yscrollcommand=self.scroll.set)
        self.filas = tk.Frame(self.lienzo, bg=TARJETA)
        self._ventana = self.lienzo.create_window(0, 0, anchor="nw", window=self.filas)
        self.filas.bind("<Configure>", lambda e: self.lienzo.configure(scrollregion=self.lienzo.bbox("all")))
        self.lienzo.bind("<Configure>", lambda e: self.lienzo.itemconfigure(self._ventana, width=e.width))
        self._rueda(self.lienzo)
        self._refrescar_lista()

        # --- opciones ---
        self.vars = {}
        if h["opciones"]:
            op = Tarjeta(cont)
            op.pack(fill="x", pady=(px(14), 0))
            grid = tk.Frame(op, bg=TARJETA)
            grid.pack(fill="x", padx=px(18), pady=px(16))
            for i, (clave, etiqueta, tipo, valores, defecto) in enumerate(h["opciones"]):
                col, fila = i % 2, i // 2
                celda = tk.Frame(grid, bg=TARJETA)
                celda.grid(row=fila, column=col, sticky="ew", padx=(0 if col == 0 else px(18), 0), pady=px(5))
                grid.columnconfigure(col, weight=1, uniform="op")
                tk.Label(celda, text=etiqueta, bg=TARJETA, fg=TEXTO_SUAVE, font=fuente(9)).pack(anchor="w", pady=(0, px(4)))
                campo = Tarjeta(celda, relleno=CAMPO, borde=BORDE, radio=px(8), bg_padre=TARJETA)
                campo.pack(fill="x")
                v = tk.StringVar(value=defecto)
                if tipo == "combo":
                    w = ttk.Combobox(campo, textvariable=v, values=valores, state="readonly",
                                     font=fuente(10), style="Campo.TCombobox")
                    w.pack(fill="x", padx=(px(8), px(6)), pady=px(5))
                    w.bind("<<ComboboxSelected>>", lambda e, w=w: w.selection_clear())
                    if h["id"] == "dividir" and clave == "modo":
                        ejemplos = {"Cada N páginas": "1", "Por rangos": "1-3,4-", "Por tamaño (MB)": "25"}
                        w.bind("<<ComboboxSelected>>",
                               lambda e, v=v: self.vars["valor"].set(ejemplos.get(v.get(), "")), add="+")
                else:
                    w = tk.Entry(campo, textvariable=v, font=fuente(10), relief="flat", bd=0, bg=CAMPO, fg=TEXTO,
                                 insertbackground=TEXTO, highlightthickness=0, show="•" if tipo == "clave" else "")
                    w.pack(fill="x", padx=px(12), pady=px(9))
                w.bind("<FocusIn>", lambda e, c=campo: c.set_borde(AZUL))
                w.bind("<FocusOut>", lambda e, c=campo: c.set_borde(BORDE))
                self.vars[clave] = v

        # --- acción ---
        pie = tk.Frame(cont, bg=FONDO)
        pie.pack(fill="x", side="bottom" if not multi else "top", pady=(px(16), 0))
        self.btn_ejecutar = Boton(pie, h["titulo"], self.procesar, grande=True)
        self.btn_ejecutar.pack(side="right")
        self.btn_abrir = Boton(pie, "Abrir carpeta", self.abrir_destino, tipo="secundario")
        self._apoyo(pie)
        self.estado = tk.Label(pie, text="", bg=FONDO, fg=TEXTO_SUAVE, font=fuente(10), anchor="w",
                               justify="left", wraplength=px(330), width=1)
        self.estado.pack(side="left", fill="x", expand=True)
        # el resultado usa el ancho que quede libre y baja de renglón si no entra
        self.estado.bind("<Configure>", lambda e: e.widget.configure(wraplength=max(px(80), e.width - px(4))))
        self.progreso = ttk.Progressbar(pie, mode="indeterminate", length=px(150), style="Fina.Horizontal.TProgressbar")
        self._preparar_soltar()

    def _apoyo(self, pie):
        """Bloque chico de donaciones abajo a la izquierda (Cafecito y GitHub Sponsors).
        Solo abre la página en el navegador: el programa en sí no se conecta a internet."""
        caja = tk.Frame(pie, bg=FONDO)
        caja.pack(side="left", padx=(0, px(16)))
        tk.Label(caja, text="¿Te sirvió? Apoyá a Pache Labs", bg=FONDO, fg=TEXTO_SUAVE,
                 font=fuente(9), anchor="w").pack(anchor="w")
        enlaces = tk.Frame(caja, bg=FONDO)
        enlaces.pack(anchor="w", pady=(px(2), 0))
        opciones = [("☕ Cafecito", "https://cafecito.app/pachelabs"),          # Argentina (Mercado Pago)
                    ("♥ GitHub Sponsors", "https://github.com/sponsors/pachelabs-apps")]  # exterior
        for i, (texto, url) in enumerate(opciones):
            if i:
                tk.Label(enlaces, text="·", bg=FONDO, fg=TEXTO_SUAVE, font=fuente(10, True)).pack(side="left", padx=px(6))
            enl = tk.Label(enlaces, text=texto, bg=FONDO, fg=ROJO, font=fuente(10, True), cursor="hand2")
            enl.pack(side="left")
            enl.bind("<Button-1>", lambda e, u=url: abrir_archivo(u))
            enl.bind("<Enter>", lambda e, w=enl: w.configure(font=(FUENTE, 10, "bold underline")))
            enl.bind("<Leave>", lambda e, w=enl: w.configure(font=fuente(10, True)))
        # separador fino entre las donaciones y el resultado
        tk.Frame(pie, bg=BORDE, width=1).pack(side="left", fill="y", padx=(0, px(14)), pady=px(4))

    def _rueda(self, lienzo):
        def mover(e):
            if self.scroll.fin - self.scroll.ini >= 0.999:
                return
            if getattr(e, "num", None) == 4:
                lienzo.yview_scroll(-2, "units")
            elif getattr(e, "num", None) == 5:
                lienzo.yview_scroll(2, "units")
            else:
                lienzo.yview_scroll(int(-e.delta / 40) or (-1 if e.delta > 0 else 1), "units")

        def activar(e):
            self.bind_all("<MouseWheel>", mover)
            self.bind_all("<Button-4>", mover)
            self.bind_all("<Button-5>", mover)

        def desactivar(e):
            self.unbind_all("<MouseWheel>")
            self.unbind_all("<Button-4>")
            self.unbind_all("<Button-5>")

        lienzo.bind("<Enter>", activar)
        lienzo.bind("<Leave>", desactivar)

    # ---------- lista de archivos ----------
    def _refrescar_lista(self):
        for w in self.filas.winfo_children():
            w.destroy()
        h = self.herr_actual
        multi = h["entrada"] in ("multi", "imagenes")
        n = len(self.archivos)

        self.zona_vacia = None
        self._filas_w = []
        if not multi:
            self.lienzo.configure(height=px(132) if n == 0 else px(66))
        if n == 0:
            zona = tk.Canvas(self.filas, height=px(212) if multi else px(116), bg=TARJETA,
                             highlightthickness=0, bd=0, cursor="hand2")
            zona.pack(fill="x", pady=(px(8), px(4)), padx=(0, px(6)))
            zona.bind("<Configure>", lambda e: self._dibujar_zona())
            zona.bind("<Button-1>", lambda e: self.agregar())
            self.zona_vacia = zona
        for i, f in enumerate(self.archivos):
            self._fila(i, f, multi)

        self.lbl_cuenta.configure(text=(f"{n} archivo" + ("s" if n != 1 else "")) if multi and n else "")
        if multi and n:
            self.btn_limpiar.pack(side="left", padx=(px(10), 0))
        else:
            self.btn_limpiar.pack_forget()
        if not multi:
            self.btn_agregar.set_texto("Cambiar PDF" if n else "Elegir PDF")
        self.lienzo.yview_moveto(0)
        self._preparar_soltar()

    # ---------- arrastrar y soltar ----------
    def _dibujar_zona(self, activo=False):
        z = self.zona_vacia
        if z is None or not z.winfo_exists():
            return
        z.delete("all")
        w, hgt = z.winfo_width(), int(z.cget("height"))
        if w < 40:
            return
        col = AZUL if activo else ZONA_INACTIVA
        r, m = px(12), 2
        x0, y0, x1, y1 = m, m, w - m, hgt - m
        if activo:  # fondo suave al arrastrar encima
            pts = [x0 + r, y0, x1 - r, y0, x1, y0, x1, y0 + r, x1, y1 - r, x1, y1, x1 - r, y1,
                   x0 + r, y1, x0, y1, x0, y1 - r, x0, y0 + r, x0, y0]
            z.create_polygon(pts, smooth=True, fill=ZONA_RELLENO, outline="")
        trazo = dict(fill=col, width=px(1.5) or 1, dash=(6, 4))
        z.create_line(x0 + r, y0, x1 - r, y0, **trazo)
        z.create_line(x0 + r, y1, x1 - r, y1, **trazo)
        z.create_line(x0, y0 + r, x0, y1 - r, **trazo)
        z.create_line(x1, y0 + r, x1, y1 - r, **trazo)
        arco = dict(style="arc", outline=col, width=px(1.5) or 1, dash=(6, 4))
        z.create_arc(x0, y0, x0 + 2 * r, y0 + 2 * r, start=90, extent=90, **arco)
        z.create_arc(x1 - 2 * r, y0, x1, y0 + 2 * r, start=0, extent=90, **arco)
        z.create_arc(x0, y1 - 2 * r, x0 + 2 * r, y1, start=180, extent=90, **arco)
        z.create_arc(x1 - 2 * r, y1 - 2 * r, x1, y1, start=270, extent=90, **arco)
        cx, cy = w / 2, hgt / 2 - px(16)
        ic = AZUL if activo else TEXTO_SUAVE
        h = self.herr_actual
        if h.get("camara") and not activo:
            # cámara de fotos
            z.create_rectangle(cx - px(6), cy - px(25), cx + px(6), cy - px(20), fill=ic, outline=ic)
            z.create_rectangle(cx - px(17), cy - px(20), cx + px(17), cy + px(4), outline=ic, width=px(2))
            z.create_oval(cx - px(7), cy - px(15), cx + px(7), cy - px(1), outline=ic, width=px(2))
        else:
            z.create_line(cx, cy - px(24), cx, cy - px(2), fill=ic, width=px(2.5), arrow="last",
                          arrowshape=(px(9), px(10), px(4)))
            z.create_line(cx - px(15), cy - px(8), cx - px(15), cy + px(4), cx + px(15), cy + px(4),
                          cx + px(15), cy - px(8), fill=ic, width=px(2), joinstyle="round", capstyle="round")
        boton = {"multi": "Agregar PDF", "pdf": "Elegir PDF", "imagenes": "Agregar imágenes"}[h["entrada"]]
        tipo = "imágenes" if h["entrada"] == "imagenes" else ("PDF" if h["entrada"] == "multi" else "PDF")
        if activo:
            principal, segunda = "Soltá para agregarlos", ""
        elif h.get("camara"):
            principal = "Hacé clic para abrir la cámara"
            segunda = "También podés arrastrar fotos que ya tengas" if self.dnd else ""
        elif self.dnd:
            principal = f"Arrastrá tus {tipo} acá" if h["entrada"] != "pdf" else "Arrastrá tu PDF acá"
            segunda = "o hacé clic para buscarlos" if h["entrada"] != "pdf" else "o hacé clic para buscarlo"
        else:
            principal, segunda = "Todavía no elegiste archivos", f"Usá el botón \u201c{boton}\u201d para empezar"
        z.create_text(cx, cy + px(26), text=principal, fill=AZUL if activo else TEXTO, font=fuente(11, True))
        if segunda:
            z.create_text(cx, cy + px(46), text=segunda, fill=TEXTO_SUAVE, font=fuente(9))

    def _preparar_soltar(self):
        """Permite soltar archivos en cualquier parte del panel de la herramienta."""
        if not self.dnd:
            return
        for w in [self.main] + self._descendientes(self.main):
            if getattr(w, "_soltar_ok", False):
                continue
            try:
                w.drop_target_register(DND_FILES)
                w.dnd_bind("<<DropEnter>>", self._soltar_entra)
                w.dnd_bind("<<DropPosition>>", lambda e: COPY)
                w.dnd_bind("<<DropLeave>>", self._soltar_sale)
                w.dnd_bind("<<Drop>>", self._soltar)
                w._soltar_ok = True
            except Exception:
                pass

    def _resaltar(self, si):
        try:
            self.card_archivos.set_borde(AZUL if si else BORDE)
        except Exception:
            pass
        self._dibujar_zona(si)

    def _soltar_entra(self, e):
        if self._pend_salida:
            self.after_cancel(self._pend_salida)
            self._pend_salida = None
        self._resaltar(True)
        return COPY

    def _soltar_sale(self, e):
        # al pasar de un elemento a otro llega "sale" y enseguida "entra": se espera un instante
        if self._pend_salida:
            self.after_cancel(self._pend_salida)
        self._pend_salida = self.after(90, lambda: self._resaltar(False))
        return e.action

    def _soltar(self, e):
        if self._pend_salida:
            self.after_cancel(self._pend_salida)
            self._pend_salida = None
        self._resaltar(False)
        try:
            rutas = list(self.tk.splitlist(e.data))
        except Exception:
            rutas = []
        self._agregar_rutas(rutas)
        return COPY

    def _agregar_rutas(self, rutas):
        if self._bloqueado():
            return
        h = self.herr_actual
        imagenes = h["entrada"] == "imagenes"
        exts = EXT_IMAGEN if imagenes else (".pdf",)
        validas, ignoradas = [], 0
        for r in rutas:
            if os.path.isdir(r):  # una carpeta: se toman sus archivos del tipo correcto
                try:
                    nombres = sorted(os.listdir(r), key=str.lower)
                except OSError:
                    nombres = []
                for n in nombres:
                    p = os.path.join(r, n)
                    if os.path.isfile(p) and p.lower().endswith(exts):
                        validas.append(p)
            elif os.path.isfile(r) and r.lower().endswith(exts):
                validas.append(r)
            else:
                ignoradas += 1
        avisos = []
        if h["entrada"] == "pdf":
            if validas:
                self.archivos = [validas[0]]
                if len(validas) > 1:
                    avisos.append("Esta herramienta usa un PDF a la vez: se tomó el primero.")
        else:
            self.archivos.extend(v for v in validas if v not in self.archivos)
        if ignoradas:
            tipo = ("imágenes" if ignoradas != 1 else "una imagen") if imagenes else "PDF"
            if ignoradas == 1:
                avisos.append(f"Se ignoró 1 archivo que no es {tipo}.")
            else:
                avisos.append(f"Se ignoraron {ignoradas} archivos que no son {tipo}.")
        self._refrescar_lista()
        if hasattr(self, "estado"):
            self.estado.configure(text="  ".join(avisos), fg=TEXTO_SUAVE)

    def _fila(self, i, f, multi):
        fila = tk.Frame(self.filas, bg=TARJETA)
        fila.pack(fill="x")
        if i > 0:
            tk.Frame(fila, bg=SEPARADOR, height=1).pack(fill="x")
        cuerpo = tk.Frame(fila, bg=TARJETA)
        cuerpo.pack(fill="x", pady=px(8))

        self._filas_w.append(fila)
        if multi:
            tk.Label(cuerpo, text="\u2261", bg=TARJETA, fg=ASA, font=fuente(14),
                     cursor="fleur").pack(side="left", padx=(px(2), 0))
            tk.Label(cuerpo, text=f"{i + 1}", bg=TARJETA, fg=GRIS_DESACTIVADO, font=fuente(9, True),
                     width=3).pack(side="left")
        ext = (os.path.splitext(f)[1].lstrip(".").upper() or "?")[:4]
        es_pdf = ext == "PDF"
        badge = redondeado(px(40), px(40), px(9), BADGE_PDF if es_pdf else BADGE_IMG)
        tk.Label(cuerpo, image=badge, text=ext, compound="center", bg=TARJETA,
                 fg=BADGE_PDF_TEXTO if es_pdf else AZUL, font=fuente(8, True), bd=0).pack(side="left", padx=(0, px(12)))

        textos = tk.Frame(cuerpo, bg=TARJETA)
        textos.pack(side="left", fill="x", expand=True)
        try:
            meta = tam_legible(os.path.getsize(f))
            if es_pdf:
                inf = self._info(f)
                if inf is None:
                    raise ValueError
                meta = f"{inf['paginas']} página{'s' if inf['paginas'] != 1 else ''}  ·  {meta}" + \
                       {"clave": "  ·  🔒 con contraseña", "restringido": "  ·  🔒 con restricciones"}.get(
                           inf["seguridad"], "") + {"valida": "  ·  con firma digital",
                            "alterada": "  ·  firma digital NO válida (copia modificada)"}.get(inf.get("firma"), "")
        except Exception:
            meta = "No se pudo leer el archivo"
        tk.Label(textos, text=os.path.basename(f), bg=TARJETA, fg=TEXTO, font=fuente(10, True),
                 anchor="w").pack(fill="x")
        tk.Label(textos, text=meta, bg=TARJETA, fg=TEXTO_SUAVE, font=fuente(9), anchor="w").pack(fill="x")

        acciones = tk.Frame(cuerpo, bg=TARJETA)
        acciones.pack(side="right", padx=(0, px(6)))
        botones = []
        if multi:
            botones += [("↑", lambda: self.mover(i, -1), AZUL, i > 0),
                        ("↓", lambda: self.mover(i, 1), AZUL, i < len(self.archivos) - 1)]
        botones.append(("✕", lambda: self.quitar(i), ROJO, True))
        widgets_accion = {acciones}
        for simbolo, cmd, color, habil in botones:
            b = tk.Label(acciones, text=simbolo, bg=TARJETA, fg=TEXTO_SUAVE if habil else ICONO_DESHAB,
                         font=fuente(12), width=2, cursor="hand2" if habil else "arrow",
                         takefocus=1 if habil else 0, highlightthickness=px(2), highlightbackground=TARJETA,
                         highlightcolor=AZUL_ACTIVO)
            b.pack(side="left", padx=px(2))
            widgets_accion.add(b)
            if habil:
                b.bind("<Button-1>", lambda e, c=cmd: c())
                # con teclado: Enter o espacio; después de mover, el foco sigue al archivo
                for tecla in ("<Return>", "<KP_Enter>", "<space>"):
                    b.bind(tecla, lambda e, c=cmd: (c(), "break")[1])
                b.bind("<FocusIn>", lambda e, fl=fila: self._mostrar_fila(fl), add="+")
                if self._foco_fila == (simbolo, i):
                    self._foco_fila = None
                    self.after_idle(lambda b=b: b.winfo_exists() and b.focus_set())
                b.bind("<Enter>", lambda e, b=b, c=color: b.configure(fg=c), add="+")
                b.bind("<Leave>", lambda e, b=b: b.configure(fg=TEXTO_SUAVE), add="+")

        # resaltado de la fila al pasar el mouse
        def pintar(color, w=cuerpo):
            for x in [w] + self._descendientes(w):
                try:
                    x.configure(bg=color)
                except tk.TclError:
                    pass

        for x in [cuerpo] + self._descendientes(cuerpo):
            x.bind("<Enter>", lambda e: pintar(FILA_HOVER), add="+")
            x.bind("<Leave>", lambda e: pintar(TARJETA), add="+")
        # reordenar arrastrando la fila (solo herramientas con varios archivos)
        if multi:
            for x in [cuerpo] + self._descendientes(cuerpo):
                if x in widgets_accion:
                    continue
                x.bind("<ButtonPress-1>", lambda e, i=i: self._arr_ini(e, i), add="+")
                x.bind("<B1-Motion>", self._arr_mover, add="+")
                x.bind("<ButtonRelease-1>", self._arr_fin, add="+")
                if x is not cuerpo and str(x.cget("cursor")) == "":
                    x.configure(cursor="hand2")
            cuerpo.configure(cursor="hand2")
        self._rueda_hijos(fila)

    # ---------- reordenar arrastrando ----------
    def _arr_ini(self, e, i):
        if self._en_curso:
            self._arrastre = None
            return
        self._arrastre = {"i": i, "y0": e.y_root, "activo": False, "destino": i}

    def _arr_destino(self, y_root):
        y = y_root - self.filas.winfo_rooty()
        for idx, f in enumerate(self._filas_w):
            if y < f.winfo_y() + f.winfo_height() / 2:
                return idx
        return len(self._filas_w)

    def _arr_mover(self, e):
        a = getattr(self, "_arrastre", None)
        if not a or len(self._filas_w) < 2:
            return
        if not a["activo"]:
            if abs(e.y_root - a["y0"]) < px(6):
                return
            a["activo"] = True
            self.configure(cursor="fleur")
            self._linea = tk.Frame(self.filas, bg=AZUL, height=px(3))
        # desplazar la lista si se arrastra cerca de los bordes
        ly = e.y_root - self.lienzo.winfo_rooty()
        if self.scroll.fin - self.scroll.ini >= 0.999:
            pass  # la lista entra entera: no hay nada que desplazar
        elif ly < px(24):
            self.lienzo.yview_scroll(-1, "units")
        elif ly > self.lienzo.winfo_height() - px(24):
            self.lienzo.yview_scroll(1, "units")
        destino = self._arr_destino(e.y_root)
        a["destino"] = destino
        if destino < len(self._filas_w):
            y = self._filas_w[destino].winfo_y()
        else:
            ult = self._filas_w[-1]
            y = ult.winfo_y() + ult.winfo_height() - px(3)
        self._linea.place(x=0, y=max(0, y - 1), relwidth=1)
        self._linea.lift()

    def _arr_fin(self, e):
        a = getattr(self, "_arrastre", None)
        self._arrastre = None
        if not a or not a["activo"]:
            return
        self.configure(cursor="")
        try:
            self._linea.destroy()
        except Exception:
            pass
        i, destino = a["i"], a["destino"]
        if destino > i:
            destino -= 1
        if destino != i and 0 <= i < len(self.archivos):
            self.archivos.insert(destino, self.archivos.pop(i))
            pos = self.lienzo.yview()[0]
            self._refrescar_lista()
            self.lienzo.yview_moveto(pos)

    def _descendientes(self, w):
        r = []
        for c in w.winfo_children():
            r.append(c)
            r.extend(self._descendientes(c))
        return r

    def _rueda_hijos(self, w):
        # que la rueda del mouse funcione también sobre las filas
        for x in [w] + self._descendientes(w):
            x.bind("<Enter>", lambda e: self.lienzo.event_generate("<Enter>"), add="+")

    def _bloqueado(self):
        """Durante una operación no se toca la lista (evita abrir PDF desde dos hilos a la vez)."""
        if self._en_curso:
            try:
                self.estado.configure(text="Esperá a que termine la operación en curso.", fg=ROJO)
            except Exception:
                pass
            return True
        return False

    def agregar(self):
        if self._bloqueado():
            return
        h = self.herr_actual
        if h.get("camara"):
            self.abrir_camara()
            return
        if h["entrada"] == "imagenes":
            tipos = [("Imágenes", "*.jpg *.jpeg *.png *.bmp *.tif *.tiff *.webp")]
        else:
            tipos = [("Archivos PDF", "*.pdf")]
        if h["entrada"] == "pdf":
            f = filedialog.askopenfilename(title="Elegir PDF", filetypes=tipos)
            elegidos = [f] if f else []
        else:
            elegidos = list(filedialog.askopenfilenames(title="Agregar archivos", filetypes=tipos))
        if elegidos:
            # mismo filtro que al arrastrar: se ignoran (con aviso) los de otro tipo
            self._agregar_rutas(elegidos)

    def _mostrar_fila(self, fila):
        """Desplaza la lista para que se vea la fila que tiene el foco del teclado."""
        try:
            self.update_idletasks()
            alto_total = max(1, self.filas.winfo_height())
            alto_vista = self.lienzo.winfo_height()
            y0, y1 = fila.winfo_y(), fila.winfo_y() + fila.winfo_height()
            arriba = self.lienzo.canvasy(0)
            if y0 < arriba:
                self.lienzo.yview_moveto(y0 / alto_total)
            elif y1 > arriba + alto_vista:
                self.lienzo.yview_moveto(max(0, y1 - alto_vista) / alto_total)
        except tk.TclError:
            pass

    def mover(self, i, d):
        if self._bloqueado():
            return
        j = i + d
        if 0 <= j < len(self.archivos):
            self.archivos[i], self.archivos[j] = self.archivos[j], self.archivos[i]
            # si se usó el teclado, el foco queda en la misma flecha del archivo movido
            # (o en la otra flecha si llegó al extremo de la lista)
            simbolo = "↑" if d < 0 else "↓"
            if (d < 0 and j == 0) or (d > 0 and j == len(self.archivos) - 1):
                simbolo = "↓" if d < 0 else "↑"
            self._foco_fila = (simbolo, j)
            self._refrescar_lista()

    def quitar(self, i):
        if self._bloqueado():
            return
        del self.archivos[i]
        if self.archivos:
            self._foco_fila = ("✕", min(i, len(self.archivos) - 1))
        self._refrescar_lista()

    def limpiar(self):
        if self._bloqueado():
            return
        self.archivos = []
        self._refrescar_lista()

    # ---------- cámara ----------
    def abrir_camara(self):
        if self._bloqueado():
            return
        if self._camara is not None and self._camara.winfo_exists():
            self._camara.deiconify()
            self._camara.lift()
            self._camara.focus_set()
            return
        self._camara = VentanaCamara(self)

    def _cerrar_camara(self):
        cam, self._camara = self._camara, None
        if cam is not None:
            try:
                cam.cerrar()
            except Exception:
                pass

    def _guardar_foto(self, img):
        """Guarda la foto en la carpeta temporal y la agrega a la lista. Devuelve la ruta."""
        import tempfile
        try:
            if not self._dir_fotos or not os.path.isdir(self._dir_fotos):
                self._dir_fotos = tempfile.mkdtemp(prefix="OzonePDF_fotos_")
            self._n_foto += 1
            ruta = os.path.join(self._dir_fotos, f"Foto {self._n_foto:03d}.jpg")
            img.convert("RGB").save(ruta, format="JPEG", quality=92)
        except OSError as e:
            messagebox.showerror(APP_NOMBRE, f"No se pudo guardar la foto:\n\n{traducir_error(e)}")
            return None
        if self.herr_actual and self.herr_actual.get("camara"):
            self.archivos.append(ruta)
            self._refrescar_lista()
            try:  # que se vea la última foto
                self.lienzo.yview_moveto(1.0)
            except tk.TclError:
                pass
        return ruta

    def _borrar_fotos(self):
        if self._dir_fotos:
            shutil.rmtree(self._dir_fotos, ignore_errors=True)
            self._dir_fotos = None

    # ---------- proceso ----------
    def _pedir_destino(self, h):
        primero = self.archivos[0]
        carpeta = os.path.dirname(primero)
        base = os.path.splitext(os.path.basename(primero))[0]
        if h.get("camara"):
            # las fotos están en una carpeta temporal: se propone Documentos y un nombre con fecha
            import time
            docs = os.path.join(os.path.expanduser("~"), "Documents")
            carpeta = docs if os.path.isdir(docs) else os.path.expanduser("~")
            base = time.strftime("Fotos_%Y-%m-%d_%H%M")
        if h["salida"] == "carpeta":
            d = filedialog.askdirectory(title="Elegí dónde guardar", initialdir=carpeta)
            return os.path.join(d, f"{base}_{h['id']}") if d else None
        if h["salida"] == "txt":
            return filedialog.asksaveasfilename(title="Guardar como", initialdir=carpeta,
                                                initialfile=f"{base}.txt", defaultextension=".txt",
                                                filetypes=[("Texto", "*.txt")])
        return filedialog.asksaveasfilename(title="Guardar como", initialdir=carpeta,
                                            initialfile=f"{base}{h.get('sufijo', '')}.pdf",
                                            defaultextension=".pdf", filetypes=[("Archivos PDF", "*.pdf")])

    def procesar(self):
        if self._en_curso:
            return
        h = self.herr_actual
        # se trabaja sobre una copia: lo que se revisa es exactamente lo que se procesa
        archivos = list(self.archivos)
        if not archivos:
            messagebox.showinfo(APP_NOMBRE, "Primero elegí los archivos.")
            return
        if h["id"] == "unir" and len(archivos) < 2:
            messagebox.showinfo(APP_NOMBRE, "Agregá al menos dos PDF para unir.")
            return
        opciones = {k: v.get() for k, v in self.vars.items()}
        try:
            confirmar = self._validar(h, archivos, opciones)
        except ValueError as e:
            messagebox.showwarning(APP_NOMBRE, str(e))
            return
        if confirmar and not messagebox.askyesno(APP_NOMBRE, confirmar):
            return
        destino = self._pedir_destino(h)
        if not destino:
            return
        if any(mismo_archivo(destino, a) for a in archivos):
            messagebox.showwarning(APP_NOMBRE, "Elegí un nombre distinto al archivo original.")
            return
        od = carpeta_onedrive(destino)
        if od and not messagebox.askyesno(
                APP_NOMBRE, "La carpeta elegida está sincronizada con OneDrive:\n" + od +
                "\n\nOneDrive va a subir el resultado a la nube. Ozone PDF no usa internet, pero OneDrive sí."
                "\n\n¿Querés guardar ahí igual?"):
            return
        if h["salida"] == "carpeta":
            destino = carpeta_libre(destino)
        self._en_curso = True
        panel = self._panel_id
        self._ocupado(True)

        carpeta_dest, nombre_dest = os.path.split(destino)
        parcial = os.path.join(carpeta_dest, f".~{nombre_dest}.parcial")

        def trabajo():
            # todo se escribe primero como ".~nombre.parcial" (archivo o carpeta) y recién al
            # terminar bien se renombra al destino; si falla o se cancela, se borra
            terminado = False
            try:
                borrar(parcial)
                if h["salida"] == "carpeta":
                    os.makedirs(parcial)
                    ocultar(parcial)  # mientras se genera no se ve en el Explorador
                msg = ejecutar(h, archivos, parcial, opciones, cancelar=self._evento_cancelar)
                if self._cancelar:
                    raise core.Cancelado("Operación cancelada.")
                os.replace(parcial, destino)
                if h["salida"] == "carpeta":
                    ocultar(destino, False)
                terminado = True
                resultado.put(("ok", msg, destino))
            except core.Cancelado:
                resultado.put(("info", "Operación cancelada.", None))
            except core.SinCambios as e:
                resultado.put(("info", str(e), None))
            except Exception as e:
                resultado.put(("error", traducir_error(e), None))
            finally:
                if not terminado:
                    borrar(parcial)

        # el hilo de trabajo solo deja el resultado en una cola; la ventana la consulta
        resultado = queue.Queue()

        def esperar():
            try:
                ok, msg, dest = resultado.get_nowait()
            except queue.Empty:
                self.after(80, esperar)
                return
            gc.enable()
            gc.collect()  # la limpieza de memoria se hace acá, en el hilo de la ventana
            self._en_curso = False
            if self._cancelar:  # se pidió cerrar: el parcial ya se borró, se cierra la app
                self._cerrar_camara()
                self._borrar_fotos()
                self.destroy()
                return
            if panel == self._panel_id:  # el resultado se muestra solo en el panel que lo lanzó
                self._fin(ok, msg, dest)

        # Mientras trabaja el hilo de fondo se pausa la limpieza automática de memoria:
        # si ocurriera en ese hilo podría liberar imágenes de la ventana fuera del hilo
        # principal, cosa que Tkinter no admite (puede trabar la aplicación).
        gc.collect()
        gc.disable()
        threading.Thread(target=trabajo, daemon=True).start()
        self.after(80, esperar)

    def _info(self, ruta):
        """Páginas y cifrado de un PDF, guardado en memoria por (ruta, fecha, tamaño):
        así ordenar la lista no vuelve a abrir todos los PDF."""
        try:
            st = os.stat(ruta)
        except OSError:
            return None
        clave = (os.path.normcase(os.path.abspath(ruta)), st.st_mtime_ns, st.st_size)
        if clave not in self._info_cache:
            try:
                self._info_cache[clave] = core.info(ruta)
            except Exception:
                self._info_cache[clave] = None
        return self._info_cache[clave]

    @staticmethod
    def _revisar_seguridad(hid, ruta, inf):
        """PDF con contraseña de apertura: ninguna herramienta lo procesa (primero "Quitar
        contraseña"). PDF con restricciones: solo las herramientas que leen, y si el PDF
        permite esa lectura. Cifrado sin restricciones: se procesa como uno normal."""
        nombre = os.path.basename(ruta)
        if inf["seguridad"] == "clave":
            raise ValueError(f"\u201c{nombre}\u201d tiene contraseña para abrirse.\n\n"
                             "Quitala primero con \u201cQuitar contraseña\u201d.")
        if inf["seguridad"] == "restringido":
            permiso = SOLO_LECTURA.get(hid)
            if permiso and inf["permisos"] & permiso:
                return
            que = {core.pymupdf.PDF_PERM_COPY: "copiar el texto",
                   core.pymupdf.PDF_PERM_PRINT: "imprimir"}.get(permiso, "modificarlo")
            raise ValueError(f"\u201c{nombre}\u201d tiene restricciones de seguridad que no permiten {que}.\n\n"
                             "Para quitarlas hace falta la contraseña de propietario "
                             "(herramienta \u201cQuitar contraseña\u201d).")

    def _validar(self, h, archivos, op):
        """Revisa todo antes de empezar. Lanza ValueError con un mensaje claro o devuelve
        un texto a confirmar (o None)."""
        hid = h["id"]
        pdfs = [a for a in archivos if a.lower().endswith(".pdf")]
        infos = {}
        for a in pdfs:
            inf = self._info(a)
            if inf is None:
                raise ValueError(f"No se pudo abrir \u201c{os.path.basename(a)}\u201d. "
                                 "Verificá que sea un PDF válido y que no esté abierto en otro programa.")
            infos[a] = inf
            if hid != "desproteger":
                self._revisar_seguridad(hid, a, inf)
        if hid == "desproteger" and pdfs and not infos[pdfs[0]]["cifrado"]:
            raise ValueError("Este PDF no tiene contraseña.")
        total = infos[pdfs[0]]["paginas"] if pdfs else 0
        confirmaciones = []
        firmados = [os.path.basename(a) for a, inf in infos.items() if inf.get("firma") == "valida"]
        alterados = [os.path.basename(a) for a, inf in infos.items() if inf.get("firma") == "alterada"]
        if alterados and not firmados and hid not in SOLO_LECTURA:
            cual = (f"\u201c{alterados[0]}\u201d tiene" if len(alterados) == 1
                    else f"{len(alterados)} de los PDF tienen")
            confirmaciones.append(
                f"{cual} una firma digital que YA NO ES VÁLIDA: el archivo fue modificado después "
                "de firmarse (por ejemplo, es una copia unida o comprimida). Aunque se vea el sello "
                "de la firma, no sirve como documento firmado; tampoco la copia que se genere ahora.")
        if firmados and hid not in SOLO_LECTURA:
            cual = (f"\u201c{firmados[0]}\u201d tiene" if len(firmados) == 1
                    else f"{len(firmados)} de los PDF tienen")
            confirmaciones.append(
                f"{cual} FIRMA DIGITAL.\n\nEl archivo que se genere NO va a tener una firma válida: "
                "cualquier cambio la invalida (en Acrobat aparece como alterada) y al unir o extraer "
                "páginas se pierde.\n\nEl original no se modifica y sigue firmado: para trámites o "
                "para enviar como documento firmado, usá siempre el original.")
        adjuntos = sum(inf.get("adjuntos", 0) for inf in infos.values())
        if adjuntos and hid != "desproteger":
            confirmaciones.append(
                f"El PDF tiene {adjuntos} archivo{'s' if adjuntos != 1 else ''} adjunto{'s' if adjuntos != 1 else ''}. "
                "Ozone PDF genera las copias sin adjuntos y sin el nombre del autor de las notas, para no "
                "arrastrar datos personales.")
        respuestas = sum(inf.get("respuestas", 0) for inf in infos.values())
        if respuestas and hid in ("unir", "dividir"):
            confirmaciones.append(
                f"El PDF tiene {respuestas} respuesta{'s' if respuestas != 1 else ''} a comentarios. "
                f"{'Unir' if hid == 'unir' else 'Dividir'} arma un PDF nuevo y las respuestas no se copian "
                "(los comentarios originales sí). El original no se modifica.")
        if hid == "proteger":
            if not op["password"]:
                raise ValueError("Escribí una contraseña.")
            if op["password"] != op["password2"]:
                raise ValueError("Las contraseñas no coinciden.")
            if len(op["password"]) < 6:
                confirmaciones.append("La contraseña tiene menos de 6 caracteres y es fácil de adivinar.")
        if hid == "dividir":
            if op["modo"].startswith("Por tamaño"):
                try:
                    mb = float(op["valor"].strip().replace(",", "."))
                except ValueError:
                    mb = 0
                if mb <= 0:
                    raise ValueError("Indicá el tamaño máximo de cada parte en MB, por ejemplo 25 (o 9,5).")
            elif op["modo"].startswith("Cada"):
                try:
                    n = int(op["valor"].strip())
                except ValueError:
                    n = 0
                if n < 1:
                    raise ValueError("Indicá cada cuántas páginas dividir con un número entero, por ejemplo 2.")
            else:
                if not op["valor"].strip():
                    raise ValueError("Indicá los rangos, por ejemplo: 1-3,4-8,9-")
                for r in op["valor"].split(","):
                    if r.strip():
                        core.parse_rango(r, total)
        elif hid in ("extraer", "eliminar", "rotar") and op.get("rango", "").strip():
            core.parse_rango(op["rango"], total)
        elif hid == "eliminar" and not op.get("rango", "").strip():
            raise ValueError("Indicá qué páginas eliminar, por ejemplo: 2,4-6")
        if hid == "eliminar" and op.get("rango", "").strip() and total:
            if len(set(core.parse_rango(op["rango"], total))) >= total:
                raise ValueError("No se pueden eliminar todas las páginas: el PDF quedaría vacío.")
        elif hid == "reordenar":
            if not op["orden"].strip():
                raise ValueError("Indicá el nuevo orden de páginas, por ejemplo: 3,1,2,4-")
            paginas = core.parse_rango(op["orden"], total)
            faltan = total - len(set(paginas))
            if faltan > 0:
                confirmaciones.append(f"El nuevo orden no incluye {faltan} página{'s' if faltan != 1 else ''} "
                                      "del documento: se van a descartar del archivo final.")
        elif hid == "numerar":
            try:
                inicio = int(op["inicio"].strip())
            except ValueError:
                inicio = 0
            if inicio < 1:
                raise ValueError("\u201cEmpezar en\u201d tiene que ser un número entero de 1 en adelante, "
                                 "por ejemplo 1 o 21.")
            core.validar_formato_numeracion(op["formato"])
        elif hid == "marca" and not op["texto"].strip():
            raise ValueError("Escribí el texto de la marca de agua.")
        if confirmaciones:
            return "\n\n".join(confirmaciones) + "\n\n¿Querés continuar?"
        return None

    def _al_cerrar(self):
        if not self._en_curso:
            self._cerrar_camara()
            self._borrar_fotos()
            self.destroy()
            return
        if self._cancelar:  # ya se pidió: se está terminando el paso actual
            return
        if messagebox.askyesno(APP_NOMBRE, "Hay una operación en curso.\n\n¿Querés cancelarla y salir? "
                                           "Se detiene en la página que está procesando y el archivo "
                                           "a medio generar se descarta."):
            # se espera a que el hilo de trabajo termine su paso actual; al terminar ve el
            # pedido de cancelación, borra el parcial y la ventana se cierra sola
            self._cancelar = True
            self._evento_cancelar.set()  # el motor se detiene en la próxima página
            # la ventana queda visible hasta que el proceso realmente termine: algunos pasos
            # (recomprimir imágenes, guardar) los hace MuPDF de una vez y no se pueden cortar
            self.estado.configure(text="Cancelando… se termina el paso actual y la ventana se cierra sola.",
                                  fg=TEXTO_SUAVE)

    def _ocupado(self, si):
        self.btn_ejecutar.habilitar(not si)
        self.btn_abrir.pack_forget()
        if si:
            self.estado.configure(text="Procesando…", fg=TEXTO_SUAVE)
            self.progreso.pack(side="right", padx=px(14), before=self.estado)
            self.progreso.start(12)
        else:
            self.progreso.stop()
            self.progreso.pack_forget()

    def _fin(self, estado, msg, destino):
        self._ocupado(False)
        for clave in ("password", "password2"):
            if clave in self.vars:
                self.vars[clave].set("")
        if estado == "info":
            self.estado.configure(text=f"\u2139  {msg}", fg=TEXTO_SUAVE)
            self._aviso("Sin cambios", msg, ok=False)
            return
        ok = estado == "ok"
        if ok:
            self.ultimo_destino = destino
            self.estado.configure(text=f"✔  {msg}", fg=OK)
            self.btn_abrir.pack(side="right", padx=(0, px(10)), before=self.estado)
            extra = []
            if self.pref_limpiar and self.archivos:
                self.archivos = []
                self._refrescar_lista()
                extra.append("Se limpió la lista de archivos.")
                if self.herr_actual.get("camara"):
                    self._borrar_fotos()  # las fotos ya están en el PDF
            if self.pref_abrir:
                self.abrir_resultado(destino)
                extra.append("Se abrió el resultado.")
            self._aviso("¡Listo!", msg + ("\n\n" + " ".join(extra) if extra else ""), ok=True)
        else:
            self.estado.configure(text="", fg=TEXTO_SUAVE)
            messagebox.showerror(APP_NOMBRE, f"No se pudo completar la operación:\n\n{msg}")

    def _cambiar_pref(self, cual, valor):
        if cual == "abrir":
            self.pref_abrir = valor
            guardar_preferencia("AbrirAlTerminar", "1" if valor else "0")
        else:
            self.pref_limpiar = valor
            guardar_preferencia("LimpiarAlTerminar", "1" if valor else "0")

    def abrir_resultado(self, destino):
        """Abre lo que se generó: el archivo con su programa (PDF, imagen, texto) o la
        carpeta, si la herramienta genera varios archivos."""
        if destino and os.path.exists(destino):
            abrir_archivo(destino)

    def _aviso(self, titulo, msg, ok=True):
        """Aviso grande en el centro de la ventana al terminar una operación. Tiene fondo
        de color y un borde grueso para que se distinga del panel blanco que queda atrás.
        Se cierra con clic, Enter o Escape, o solo a los 6 segundos."""
        self._cerrar_aviso()
        color = OK if ok else TEXTO_SUAVE
        fondo = AVISO_OK if ok else AVISO_INFO
        marco = Tarjeta(self.main, relleno=color, borde=color, radio=px(20), bg_padre=TARJETA)
        self._aviso_w = marco
        caja = Tarjeta(marco, relleno=fondo, borde=fondo, radio=px(17), bg_padre=color)
        caja.pack(padx=px(3), pady=px(3))
        cuerpo = tk.Frame(caja, bg=fondo)
        cuerpo.pack(padx=px(36), pady=px(26))
        d = px(58)
        icono = tk.Canvas(cuerpo, width=d, height=d, bg=fondo, highlightthickness=0, bd=0)
        icono.pack()
        icono.create_oval(1, 1, d - 1, d - 1, fill=color, outline="")
        if ok:
            icono.create_line(d * 0.27, d * 0.52, d * 0.44, d * 0.68, d * 0.74, d * 0.34, fill=BLANCO,
                              width=max(3, px(5)), capstyle="round", joinstyle="round")
        else:
            icono.create_text(d / 2, d / 2, text="i", fill=BLANCO, font=fuente(20, True))
        tk.Label(cuerpo, text=titulo, bg=fondo, fg=color if ok else TEXTO,
                 font=fuente(18, True)).pack(pady=(px(10), px(4)))
        tk.Label(cuerpo, text=msg, bg=fondo, fg=TEXTO, font=fuente(10), justify="center",
                 wraplength=px(420)).pack()
        botones = tk.Frame(cuerpo, bg=fondo)
        botones.pack(pady=(px(18), 0))
        aceptar = Boton(botones, "Aceptar", self._cerrar_aviso, bg_padre=fondo)
        aceptar.pack(side="right")
        if ok and self.ultimo_destino:
            Boton(botones, "Abrir carpeta", lambda: (self._cerrar_aviso(), self.abrir_destino()),
                  tipo="secundario", bg_padre=fondo).pack(side="right", padx=(0, px(10)))
        marco.place(relx=0.5, rely=0.45, anchor="center")
        marco.lift()
        for w in [marco, caja, cuerpo, icono] + list(cuerpo.winfo_children()):
            if w not in (botones,):
                w.bind("<Button-1>", lambda e: self._cerrar_aviso(), add="+")
        aceptar.focus_set()
        aceptar.bind("<Escape>", lambda e: self._cerrar_aviso())
        self._aviso_tiempo = self.after(6000, self._cerrar_aviso)

    def _cerrar_aviso(self):
        if getattr(self, "_aviso_tiempo", None):
            try:
                self.after_cancel(self._aviso_tiempo)
            except Exception:
                pass
            self._aviso_tiempo = None
        if self._aviso_w is not None:
            try:
                self._aviso_w.destroy()
            except tk.TclError:
                pass
            self._aviso_w = None

    def abrir_destino(self):
        d = self.ultimo_destino
        if not d:
            return
        carpeta = d if os.path.isdir(d) else os.path.dirname(d)
        try:
            if sys.platform == "win32":
                if os.path.isfile(d):
                    explorer = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "explorer.exe")
                    subprocess.Popen([explorer, "/select,", os.path.normpath(d)])
                else:
                    os.startfile(carpeta)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", carpeta])
            else:
                subprocess.Popen(["xdg-open", carpeta])
        except Exception:
            pass


def _nitidez_windows():
    """Evita que Windows muestre la ventana borrosa en pantallas con escalado (125%, 150%)."""
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass


def autoprueba():
    """Prueba que usa CREAR_INSTALADOR.bat sobre el .exe recién armado (Ozone PDF.exe --autotest).

    Ejecuta las 15 operaciones sobre PDFs de prueba en una carpeta temporal, abre la ventana
    y verifica arrastrar y soltar. Sale con código 0 si todo anduvo y 1 si algo falló
    (el detalle queda en %TEMP%\\ozonepdf_autotest.txt)."""
    import tempfile
    import traceback
    import pymupdf
    carpeta = tempfile.mkdtemp(prefix="ozonepdf_prueba_")
    informe = os.path.join(tempfile.gettempdir(), "ozonepdf_autotest.txt")
    try:
        os.remove(informe)  # que nunca se lea un informe viejo
    except OSError:
        pass
    pasos = []

    def vencida():
        # si algo se colgara, la autoprueba termina sola y la compilación no queda esperando
        try:
            with open(informe, "w", encoding="utf-8") as fh:
                fh.write(f"{APP_NOMBRE} {APP_VERSION} - autoprueba\n" + "\n".join(pasos)
                         + "\nFALLA: la autoprueba superó los 10 minutos\n")
        finally:
            os._exit(3)
    reloj = threading.Timer(600, vencida)
    reloj.daemon = True
    reloj.start()
    try:
        def ruta(n):
            return os.path.join(carpeta, n)
        # PDF de prueba con texto e imagen
        img = Image.new("RGB", (800, 600), (40, 90, 160))
        buf = __import__("io").BytesIO()
        img.save(buf, format="PNG")
        for nombre in ("a.pdf", "b.pdf"):
            d = pymupdf.open()
            for i in range(4):
                p = d.new_page()
                p.insert_text((72, 72), f"{nombre} pagina {i + 1}")
                p.insert_image(pymupdf.Rect(72, 100, 520, 440), stream=buf.getvalue())
            d.save(ruta(nombre))
        img.save(ruta("foto.webp"))
        a, b = ruta("a.pdf"), ruta("b.pdf")
        pruebas = [
            ("unir", lambda: core.unir([a, b], ruta("u.pdf"))),
            ("dividir", lambda: core.dividir(a, ruta("div"), "cada", "2")),
            ("comprimir", lambda: core.comprimir(a, ruta("c.pdf"), "media")),
            ("extraer", lambda: core.extraer_paginas(a, ruta("e.pdf"), "1,3")),
            ("eliminar", lambda: core.eliminar_paginas(a, ruta("el.pdf"), "2")),
            ("ordenar", lambda: core.reordenar(a, ruta("o.pdf"), "4,1-3")),
            ("rotar", lambda: core.rotar(a, ruta("r.pdf"), 90, "")),
            ("numerar", lambda: core.numerar(a, ruta("n.pdf"))),
            ("marca", lambda: core.marca_agua(ruta("r.pdf"), ruta("m.pdf"), "COPIA \u201cprueba\u201d \u20ac")),
            ("pdf a imagen", lambda: core.pdf_a_imagenes(a, ruta("img"), 72, "jpg")),
            ("imagen a pdf", lambda: core.imagenes_a_pdf([ruta("foto.webp")], ruta("i.pdf"))),
            ("fotos a pdf", lambda: ejecutar(next(x for x in HERRAMIENTAS if x["id"] == "camara"),
                                             [ruta("foto.webp")] * 2, ruta("cam.pdf"),
                                             {"tamano": "A4", "color": "Documento (blanco y negro)"})),
            ("proteger", lambda: core.proteger(a, ruta("p.pdf"), "prueba123")),
            ("quitar contraseña", lambda: core.desproteger(ruta("p.pdf"), ruta("q.pdf"), "prueba123")),
            ("pdf a texto", lambda: core.pdf_a_texto(a, ruta("t.txt"))),
        ]
        for nombre, f in pruebas:
            try:
                f()
            except core.SinCambios:
                pass
            pasos.append(f"OK  {nombre}")

        # además de que nada falle, se revisan los resultados
        def comprobar(condicion, texto):
            if not condicion:
                raise RuntimeError("resultado incorrecto: " + texto)
        with pymupdf.open(ruta("u.pdf")) as d:
            comprobar(d.page_count == 8, "Unir debía dar 8 páginas")
        with pymupdf.open(ruta("p.pdf")) as d:
            comprobar(d.needs_pass, "el PDF protegido debía pedir contraseña")
            comprobar(d.authenticate("prueba123") > 0, "la contraseña del PDF protegido no funciona")
        with pymupdf.open(ruta("q.pdf")) as d:
            comprobar(not d.needs_pass, "Quitar contraseña debía dejar el PDF sin clave de apertura")
        with pymupdf.open(ruta("o.pdf")) as d:
            comprobar("pagina 4" in d[0].get_text(), "Ordenar debía poner la página 4 primero")
        with pymupdf.open(ruta("r.pdf")) as d:
            comprobar(d[0].rotation == 90, "Rotar debía girar 90 grados")
        with open(ruta("t.txt"), encoding="utf-8") as fh:
            comprobar("a.pdf pagina 1" in fh.read(), "PDF a texto debía extraer el texto")
        comprobar(len(os.listdir(ruta("div"))) == 2, "Dividir cada 2 páginas debía dar 2 archivos")
        with pymupdf.open(ruta("cam.pdf")) as d:
            comprobar(d.page_count == 2, "Fotos a PDF debía dar 2 páginas")
        # componente de cámara: se carga y no trae la biblioteca FFmpeg (se borra al compilar)
        import cv2
        comprobar(hasattr(cv2, "VideoCapture"), "OpenCV no tiene VideoCapture")
        # modo escanear: una hoja clara inclinada sobre fondo oscuro se detecta y se endereza
        prueba = Image.new("RGB", (1200, 900), (70, 60, 50))
        ImageDraw.Draw(prueba).polygon([(300, 120), (880, 160), (850, 820), (260, 780)], fill=(240, 238, 230))
        esquinas = detectar_hoja(prueba)
        comprobar(esquinas is not None, "el modo escanear no detectó la hoja de prueba")
        hoja = enderezar_hoja(prueba, esquinas)
        comprobar(540 <= hoja.size[0] <= 640 and 600 <= hoja.size[1] <= 700,
                  f"la hoja enderezada tiene un tamaño inesperado: {hoja.size}")
        if getattr(sys, "frozen", False):
            import glob
            comprobar(not glob.glob(os.path.join(os.path.dirname(cv2.__file__), "opencv_videoio_ffmpeg*")),
                      "el ejecutable no debía incluir la biblioteca FFmpeg de OpenCV")
        pasos.append("OK  componente de cámara (OpenCV) disponible")
        # dividir por tamaño: cada parte entra en el límite (salvo una página sola más pesada)
        d = pymupdf.open()
        for i in range(4):  # 4 páginas con fotos distintas, de peso parecido
            ruido = Image.effect_noise((500, 350), 40 + i * 5).convert("RGB")
            b = __import__("io").BytesIO()
            ruido.save(b, format="JPEG", quality=85)
            d.new_page().insert_image(pymupdf.Rect(40, 40, 540, 390), stream=b.getvalue())
        d.save(ruta("tam.pdf"))
        d.close()
        limite_mb = len(core._parte_bytes(pymupdf.open(ruta("tam.pdf")), 0, 3)) * 0.6 / core.MB
        partes, _ = core.dividir_por_tamano(ruta("tam.pdf"), ruta("div_tam"), f"{limite_mb:.4f}")
        paginas = 0
        for parte in partes:
            with pymupdf.open(parte) as d:
                paginas += d.page_count
                comprobar(os.path.getsize(parte) <= limite_mb * core.MB or d.page_count == 1,
                          "Dividir por tamaño generó una parte más grande que el límite")
        comprobar(len(partes) >= 2 and paginas == 4, "Dividir por tamaño debía repartir las 4 páginas en 2 o más partes")
        # PDF cifrado que abre sin clave y sin restricciones: se procesa como uno normal
        with pymupdf.open(a) as d:
            d.save(ruta("cl.pdf"), encryption=pymupdf.PDF_ENCRYPT_AES_256, owner_pw="dueño", user_pw="",
                   permissions=-1)
        core.extraer_paginas(ruta("cl.pdf"), ruta("cl_e.pdf"), "1")
        with pymupdf.open(ruta("cl_e.pdf")) as d:
            comprobar(d.page_count == 1, "un PDF cifrado sin restricciones debía poder procesarse")
        pasos.append("OK  resultados verificados (páginas, contraseña, orden, rotación, texto, cifrado sin clave)")
        if modo_compilacion() == "estricta":
            import importlib.util
            for m in ("socket", "_socket", "asyncio", "multiprocessing", "ssl", "_ssl", "http"):
                if m in sys.builtin_module_names:
                    # compilado dentro del propio intérprete (pasa con _socket en algunos Linux):
                    # no se puede excluir; sin el módulo "socket" de Python igual no se usa
                    pasos.append(f"--  {m}: incorporado al intérprete, no se puede excluir")
                    continue
                if importlib.util.find_spec(m) is not None:
                    raise RuntimeError(f"el ejecutable debía armarse sin el módulo '{m}' y lo incluye")
            pasos.append("OK  exclusión de red estricta verificada (sin socket, asyncio ni multiprocessing)")
        app = App()
        app.update()
        # el cambio de tema reconstruye la ventana (sin guardar la preferencia)
        oscuro_antes = TEMA_OSCURO
        for _ in range(2):
            aplicar_tema(not TEMA_OSCURO)
            app._reconstruir()
            app.update()
        comprobar(TEMA_OSCURO == oscuro_antes, "el cambio de tema no volvió al tema inicial")
        dnd = app.dnd
        app.destroy()
        if TkinterDnD is not None and not dnd:
            raise RuntimeError("no se pudo activar arrastrar y soltar")
        pasos.append("OK  la ventana abre, cambia de tema y se activa arrastrar y soltar")
        resultado = 0
    except Exception:
        pasos.append("FALLA\n" + traceback.format_exc())
        resultado = 1
    finally:
        reloj.cancel()
        shutil.rmtree(carpeta, ignore_errors=True)
    try:
        with open(informe, "w", encoding="utf-8") as fh:
            fh.write(f"Ozone PDF {APP_VERSION} - autoprueba\n" + "\n".join(pasos) + "\n")
    except OSError:
        pass
    return resultado


if __name__ == "__main__":
    if "--autotest" in sys.argv:
        sys.exit(autoprueba())
    _nitidez_windows()
    App(presentacion=True).mainloop()
