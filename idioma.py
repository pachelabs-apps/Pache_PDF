# -*- coding: utf-8 -*-
"""Idiomas de Ozone PDF.

El programa está escrito en español: cada texto que ve el usuario pasa por T("texto en
español"), que devuelve la traducción del idioma elegido (está en traducciones.py).
Si un texto no tiene traducción, se muestra en español, así nunca queda un hueco.

Idiomas: español, inglés, alemán, chino simplificado, japonés y ruso.
"""
import sys

IDIOMAS = [  # (código, nombre en su propio idioma)
    ("es", "Español"),
    ("en", "English"),
    ("de", "Deutsch"),
    ("zh", "中文（简体）"),
    ("ja", "日本語"),
    ("ru", "Русский"),
]
CODIGOS = [c for c, _ in IDIOMAS]

IDIOMA = "es"
_EMITIDOS = set()   # mensajes ya traducidos que generó el programa (ver es_propio)

try:
    from traducciones import TEXTOS
except Exception:  # pragma: no cover - sin traducciones, todo queda en español
    TEXTOS = {}


def idioma_de_windows():
    """Código del idioma de Windows del usuario si es uno de los disponibles; si no, inglés
    (y español si no se puede saber)."""
    codigo = ""
    try:
        if sys.platform == "win32":
            import ctypes
            import locale
            lcid = ctypes.windll.kernel32.GetUserDefaultUILanguage()
            codigo = (locale.windows_locale.get(lcid) or "")[:2].lower()
        else:
            import locale
            codigo = (locale.getlocale()[0] or "")[:2].lower()
    except Exception:
        codigo = ""
    if not codigo:
        return "es"
    return codigo if codigo in CODIGOS else "en"


def configurar(codigo):
    global IDIOMA
    IDIOMA = codigo if codigo in CODIGOS else "es"


def nombre(codigo=None):
    return dict(IDIOMAS).get(codigo or IDIOMA, "Español")


def T(texto, **datos):
    """Traduce un texto en español al idioma elegido. Con datos, completa los {campos}."""
    if IDIOMA != "es":
        texto = TEXTOS.get(texto, {}).get(IDIOMA, texto)
    if datos:
        try:
            texto = texto.format(**datos)
        except (KeyError, IndexError, ValueError):
            pass
    _EMITIDOS.add(texto)
    return texto


def N(n, singular, plural, **datos):
    """Como T, pero elige singular o plural según n. Los textos usan {n}."""
    return T(singular if n == 1 else plural, n=n, **datos)


def es_propio(texto):
    """True si el texto es un mensaje que armó el propio programa (no un error técnico)."""
    return texto in _EMITIDOS


def fuente_para_idioma(base):
    """Fuente de Windows que tiene los caracteres del idioma (Segoe UI no trae chino ni japonés)."""
    if sys.platform != "win32":
        return base
    return {"zh": "Microsoft YaHei UI", "ja": "Yu Gothic UI"}.get(IDIOMA, base)
