"""Motor de operaciones PDF. Todo se procesa localmente, nada sale de la máquina.

Reglas comunes a todas las funciones:
- Los PDF de entrada se abren con _abrir() (segunda barrera, además de la revisión de
  la interfaz): los que piden contraseña para abrirse se rechazan siempre; los que
  tienen restricciones se rechazan salvo que la herramienta solo lea y el PDF permita
  esa lectura (copiar texto para "PDF a texto", imprimir para "PDF a imagen"). Los PDF
  cifrados que abren sin clave y no restringen nada se tratan como normales. Solo
  "desproteger" acepta todos.
- Los resultados se guardan con _guardar(), que aplica la misma limpieza en TODAS las
  herramientas: borra metadatos (autor, título, XMP), archivos adjuntos (incrustados y
  anotaciones de archivo), JavaScript, miniaturas y el autor y las fechas de cada
  anotación (el texto de las notas y sus respuestas se conserva; excepción: Unir y
  Dividir arman un PDF nuevo con insert_pdf, que no copia las respuestas, y la
  interfaz avisa antes). No toca el contenido
  visible, la capa de texto oculta de los escaneos con OCR, las capas ocultas ni los
  valores de los campos de formulario (son contenido del documento).
- Un PDF con firma digital pierde la validez de la firma en cualquier copia modificada:
  info() lo informa ("firmado") para que la interfaz avise antes.
- Las operaciones largas reciben un threading.Event "cancelar" y lo revisan en cada
  página o archivo: si se activa, se detienen con Cancelado. Los pasos que MuPDF hace
  de una sola vez (recomprimir imágenes, guardar) terminan antes de detenerse.
"""
import io
import math
import os
import re
import secrets
import string
import time

import pymupdf
from PIL import Image, ImageOps, ImageSequence


class SinCambios(Exception):
    """La operación terminó bien pero no tiene sentido generar un archivo (ej.: no se pudo comprimir más)."""


class Cancelado(Exception):
    """El usuario pidió cancelar (por ejemplo, cerró la ventana)."""


# Todos los permisos que puede restringir un PDF
PERMISOS_TODOS = (pymupdf.PDF_PERM_PRINT | pymupdf.PDF_PERM_MODIFY | pymupdf.PDF_PERM_COPY
                  | pymupdf.PDF_PERM_ANNOTATE | pymupdf.PDF_PERM_FORM | pymupdf.PDF_PERM_ACCESSIBILITY
                  | pymupdf.PDF_PERM_ASSEMBLE | pymupdf.PDF_PERM_PRINT_HQ)

# Tope de píxeles por página al exportar imágenes (~40 megapíxeles, unos 120 MB en memoria)
MAX_PIXELES = 40_000_000


def _seguir(cancelar):
    """Se llama entre página y página: corta si se pidió cancelar y le cede un instante
    a la ventana (PyMuPDF no la deja actualizarse mientras dibuja una página)."""
    if cancelar is not None:
        if cancelar.is_set():
            raise Cancelado("Operación cancelada.")
        time.sleep(0.002)


def _fuente_ttf():
    """Fuente TrueType con acentos y símbolos (€, comillas tipográficas, rayas).
    En Windows usa Arial; si no está, Helvetica interna (solo Latin-1)."""
    windir = os.environ.get("WINDIR", r"C:\Windows")
    for ruta in (os.path.join(windir, "Fonts", "arial.ttf"),
                 "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if os.path.exists(ruta):
            return ruta
    return None


def _fuente():
    ttf = _fuente_ttf()
    if ttf:
        try:
            return pymupdf.Font(fontfile=ttf), ttf
        except Exception:
            pass
    return pymupdf.Font("helv"), None


def esta_cifrado(doc):
    """True si el PDF tiene cualquier cifrado: contraseña de apertura o solo de propietario.

    Ojo: en un PDF que solo tiene contraseña de propietario (restricciones de imprimir,
    copiar, etc.) PyMuPDF informa is_encrypted=False y needs_pass=0; el cifrado se ve
    en los metadatos."""
    if doc.needs_pass:
        return True
    return bool((doc.metadata or {}).get("encryption"))


def seguridad(doc):
    """'clave': pide contraseña para abrirse.
    'restringido': abre sin clave pero limita algo (imprimir, copiar, modificar...).
    'libre': sin cifrado, o cifrado sin clave y sin ninguna restricción (muy común en PDF
    de bancos, escáneres y sistemas: para el usuario es un PDF normal)."""
    if doc.needs_pass:
        return "clave"
    if not esta_cifrado(doc):
        return "libre"
    if (doc.permissions & PERMISOS_TODOS) == PERMISOS_TODOS:
        return "libre"
    return "restringido"


def _campos_formulario(doc):
    """xrefs de los campos de primer nivel del formulario (AcroForm/Fields). El array
    puede estar escrito directamente o guardado como objeto aparte (/Fields 12 0 R)."""
    try:
        cat = doc.pdf_catalog()
        tipo, valor = doc.xref_get_key(cat, "AcroForm/Fields")
        if tipo == "xref":
            valor = doc.xref_object(int(valor.split()[0]), compressed=True)
        elif tipo != "array":
            return set()
        nums = valor.strip().strip("[]").split()
        return {int(nums[k]) for k in range(0, len(nums) - 2) if nums[k + 2] == "R"
                and nums[k].isdigit() and nums[k + 1].isdigit()}
    except Exception:
        return set()


def _firmas(doc):
    """Objetos de firma aplicados (los que tienen /V) de los campos de firma que forman
    parte del formulario. No cuentan un campo de firma vacío (para firmar después) ni los
    restos de un campo que quedaron en una copia extraída fuera del formulario."""
    campos = _campos_formulario(doc)
    try:
        sigflags = doc.get_sigflags()
    except Exception:
        sigflags = -1
    encontradas = []

    def valor_y_raiz(xref):
        valor, saltos = None, 0
        while saltos < 20:
            if valor is None and doc.xref_get_key(xref, "V")[0] != "null":
                valor = xref
            padre = doc.xref_get_key(xref, "Parent")
            if padre[0] != "xref":
                return valor, xref
            xref = int(padre[1].split()[0])
            saltos += 1
        return valor, xref
    for p in doc:
        for w in p.widgets(types=[pymupdf.PDF_WIDGET_TYPE_SIGNATURE]) or []:
            con_valor, raiz = valor_y_raiz(w.xref)
            # red de seguridad: si no se pudo leer la lista de campos pero el documento
            # declara que tiene firmas (SigFlags), alcanza con un campo de firma con valor
            if con_valor and (raiz in campos or (not campos and sigflags > 0 and sigflags & 1)):
                if con_valor not in encontradas:
                    encontradas.append(con_valor)
    return encontradas


def _firma_cubre_archivo(doc, xref_campo, ruta):
    """True si la firma cubre el archivo completo tal como está en disco. Una firma
    abarca con /ByteRange [0 a b c] todo el archivo menos su propio contenido; si
    después de firmar el archivo se reescribió (unir, comprimir, rotar...), los rangos
    ya no coinciden con el archivo y la firma no es válida. No reemplaza la verificación
    criptográfica de Acrobat, pero detecta cualquier copia modificada."""
    try:
        tipo, valor = doc.xref_get_key(xref_campo, "V/ByteRange")
        if tipo != "array":
            return False
        a, b, c, d = (int(float(v)) for v in valor.strip("[]").split()[:4])
        tamano = os.path.getsize(ruta)
        if a != 0 or b <= 0 or c <= b or c + d != tamano:
            return False
        with open(ruta, "rb") as fh:
            fh.seek(b)
            inicio = fh.read(1)
            fh.seek(c - 1)
            fin = fh.read(1)
        return inicio == b"<" and fin == b">"
    except Exception:
        return False


def estado_firma(doc, ruta=None):
    """None: sin firma digital. "valida": tiene firma y al menos una cubre el archivo
    completo (el documento no se modificó después de la última firma). "alterada": tiene
    datos de firma pero el archivo se modificó después de firmarlo (por ejemplo, una copia
    unida o comprimida): para Acrobat la firma no es válida."""
    try:
        firmas = _firmas(doc)
    except Exception:
        try:
            return "valida" if doc.get_sigflags() > 0 else None
        except Exception:
            return None
    if not firmas:
        return None
    if ruta is None:
        return "valida"
    return "valida" if any(_firma_cubre_archivo(doc, x, ruta) for x in firmas) else "alterada"


def esta_firmado(doc):
    """True si el PDF tiene datos de firma digital (válida o no)."""
    return estado_firma(doc) is not None


QUE_PERMITE = {pymupdf.PDF_PERM_COPY: "copiar el texto", pymupdf.PDF_PERM_PRINT: "imprimir"}


def _abrir(ruta, permiso=None):
    """Abre un PDF de entrada (segunda barrera).

    permiso: para herramientas que solo leen, el permiso que necesitan
    (PDF_PERM_COPY para texto, PDF_PERM_PRINT para imágenes). Sin permiso, la
    herramienta modifica el documento y no acepta PDF con restricciones."""
    d = pymupdf.open(ruta)
    nombre = os.path.basename(ruta)
    s = seguridad(d)
    if s == "clave":
        d.close()
        raise ValueError(f"\u201c{nombre}\u201d tiene contraseña para abrirse. "
                         "Quitala primero con \u201cQuitar contraseña\u201d.")
    if s == "restringido" and not (permiso and d.permissions & permiso):
        d.close()
        if permiso:
            raise ValueError(f"\u201c{nombre}\u201d tiene restricciones de seguridad que no permiten "
                             f"{QUE_PERMITE.get(permiso, 'esta operación')}. Para quitarlas hace falta la "
                             "contraseña de propietario (\u201cQuitar contraseña\u201d).")
        raise ValueError(f"\u201c{nombre}\u201d tiene restricciones de seguridad que no permiten "
                         "modificarlo. Para quitarlas hace falta la contraseña de propietario "
                         "(\u201cQuitar contraseña\u201d).")
    return d


def _es_js(d, xref, clave):
    """True si la acción guardada en xref/clave es JavaScript (directa o por referencia)."""
    try:
        return d.xref_get_key(xref, clave + "/S")[1] == "/JavaScript"
    except Exception:
        return False


def _quitar_javascript(d):
    """scrub(javascript=True) solo vacía las acciones JavaScript que son objetos propios.
    Acá se recorren TODOS los objetos del PDF y se quita cualquier JavaScript:
    - en el catálogo: lo que se ejecuta al abrir (OpenAction), los scripts del documento
      (Names/JavaScript) y las acciones automáticas (AA);
    - en cualquier objeto (páginas, campos, anotaciones, enlaces, marcadores): las
      acciones automáticas (AA), y las acciones A u OpenAction que sean JavaScript;
    - las acciones encadenadas (Next) de las acciones que se conservan, porque pueden
      continuar con JavaScript (por ejemplo, un "ir a página" seguido de un script);
    - una acción JavaScript guardada como objeto propio queda vacía."""
    cat = d.pdf_catalog()
    for clave in ("AA", "Names/JavaScript"):
        if d.xref_get_key(cat, clave)[0] != "null":
            d.xref_set_key(cat, clave, "null")
    for x in range(1, d.xref_length()):
        try:
            for clave in ("A", "OpenAction"):
                if d.xref_get_key(x, clave)[0] == "null":
                    continue
                if _es_js(d, x, clave):
                    d.xref_set_key(x, clave, "null")
                elif d.xref_get_key(x, clave + "/Next")[0] != "null":
                    d.xref_set_key(x, clave + "/Next", "null")
            if d.xref_get_key(x, "AA")[0] != "null":
                d.xref_set_key(x, "AA", "null")
            # diccionario de nombres guardado aparte (Names 12 0 R): sus scripts
            if d.xref_get_key(x, "JavaScript")[0] != "null":
                d.xref_set_key(x, "JavaScript", "null")
                if not d.xref_is_stream(x):  # se quita también la clave (queda "null")
                    d.update_object(x, re.sub(r"/JavaScript\s+null", "", d.xref_object(x)))
            # el objeto es en sí una acción (tiene /S): se le quita el código o la cadena
            # (ojo: los marcadores también tienen /Next, pero ahí es el marcador siguiente)
            if d.xref_get_key(x, "S")[0] == "name":
                if d.xref_get_key(x, "S")[1] == "/JavaScript":
                    d.update_object(x, "<<>>")  # queda un objeto vacío, sin acción
                    continue
                if d.xref_get_key(x, "Next")[0] != "null" and d.xref_get_key(x, "Title")[0] == "null":
                    d.xref_set_key(x, "Next", "null")
        except Exception:
            pass


def _limpiar(d, quitar_adjuntos=True):
    """Quita datos ocultos que podrían arrastrar información personal a las copias."""
    try:
        d.scrub(attached_files=quitar_adjuntos, embedded_files=quitar_adjuntos, javascript=True, metadata=True,
                xml_metadata=True, reset_responses=False, thumbnails=True,
                # lo que alteraría el contenido queda desactivado:
                hidden_text=False, clean_pages=False, redactions=False, remove_links=False,
                reset_fields=False)
    except Exception:
        try:
            d.set_metadata({})
            d.del_xml_metadata()
        except Exception:
            pass
    try:
        _quitar_javascript(d)
    except Exception:
        pass
    try:
        # datos privados de programas de edición (Illustrator, etc.) e /Info del trailer
        d.xref_set_key(-1, "Info", "null")
        cat = d.pdf_catalog()
        if d.xref_get_key(cat, "PieceInfo")[0] != "null":
            d.xref_set_key(cat, "PieceInfo", "null")
        for p in d:
            if d.xref_get_key(p.xref, "PieceInfo")[0] != "null":
                d.xref_set_key(p.xref, "PieceInfo", "null")
    except Exception:
        pass
    for p in d:
        for an in list(p.annots() or []):
            try:
                if quitar_adjuntos and an.type[0] == pymupdf.PDF_ANNOT_FILE_ATTACHMENT:
                    p.delete_annot(an)
                    continue
                # autor, fechas e identificador (también en las respuestas, que son notas)
                for clave in ("T", "CreationDate", "M", "NM"):
                    d.xref_set_key(an.xref, clave, "null")
            except Exception:
                pass


def _guardar(d, salida, quitar_adjuntos=True, **opciones):
    """Guarda aplicando la limpieza de datos ocultos (ver _limpiar)."""
    _limpiar(d, quitar_adjuntos)
    opciones.setdefault("garbage", 3)
    opciones.setdefault("deflate", True)
    d.save(salida, **opciones)


def parse_rango(texto, total):
    """Convierte '1-3,5,8-' en lista de índices 0-based. Vacío = todas."""
    texto = (texto or "").replace(" ", "")
    if not texto:
        return list(range(total))
    paginas = []
    for parte in texto.split(","):
        if not parte:
            continue
        try:
            if "-" in parte:
                a, b = parte.split("-", 1)
                a = int(a) if a else 1
                b = int(b) if b else total
            else:
                a = b = int(parte)
        except ValueError:
            raise ValueError(f"No se entiende \u201c{parte}\u201d. Usá números, comas y guiones, "
                             "por ejemplo: 1-3,5,8-")
        if a < 1 or b > total or a > b:
            raise ValueError(f"El rango \u201c{parte}\u201d no es válido: el documento tiene {total} "
                             f"página{'s' if total != 1 else ''}.")
        paginas.extend(range(a - 1, b))
    return paginas


def validar_formato_numeracion(formato):
    """Solo admite {n} y {total}, sin opciones de formato (evita textos gigantes como {n:>200000000})."""
    if len(formato) > 100:
        raise ValueError("El formato de numeración es demasiado largo (máximo 100 caracteres).")
    try:
        partes = list(string.Formatter().parse(formato))
    except ValueError:
        raise ValueError("El formato tiene una llave { o } sin cerrar.\n\n"
                         "Usá {n} para el número y {total} para el total. "
                         "Para escribir una llave, poné {{ o }}.")
    for _, campo, opciones, conversion in partes:
        if campo is None:
            continue
        if campo not in ("n", "total"):
            raise ValueError(f"El formato solo admite {{n}} y {{total}}; no se reconoce \u201c{{{campo}}}\u201d.")
        if opciones or conversion:
            raise ValueError("El formato no admite opciones dentro de las llaves (por ejemplo {n:5}). "
                             "Usá solo {n} y {total}.")


def unir(archivos, salida, cancelar=None):
    """Une los PDF en orden y conserva sus marcadores (índice), corridos a su nueva página."""
    out = pymupdf.open()
    try:
        indice, desplazamiento = [], 0
        for f in archivos:
            _seguir(cancelar)
            with _abrir(f) as d:
                try:
                    toc = d.get_toc(simple=True)
                except Exception:
                    toc = []
                out.insert_pdf(d)
                # un marcador que apunta a una página inexistente se descarta junto con sus
                # hijos (si no, quedarían colgados del marcador anterior); los niveles se
                # corrigen para que no salten (1 → 3)
                saltar, previo = None, 0
                for nivel, titulo, pagina in toc:
                    if saltar is not None and nivel > saltar:
                        continue
                    saltar = None
                    if not 1 <= pagina <= d.page_count:
                        saltar = nivel
                        continue
                    nivel = max(1, min(nivel, previo + 1))
                    indice.append([nivel, titulo, pagina + desplazamiento])
                    previo = nivel
                desplazamiento += d.page_count
        if indice:
            try:
                out.set_toc(indice)
            except Exception:
                pass  # un índice mal formado en algún original no impide unir
        _seguir(cancelar)
        _guardar(out, salida)
    finally:
        out.close()
    return salida


def dividir(archivo, carpeta, modo="cada", valor="1", cancelar=None):
    """modo 'cada': cada N páginas. modo 'rangos': '1-3,4-6' -> un archivo por rango."""
    os.makedirs(carpeta, exist_ok=True)
    base = os.path.splitext(os.path.basename(archivo))[0]
    generados = []
    with _abrir(archivo) as d:
        n = d.page_count
        if modo == "cada":
            try:
                paso = int(str(valor).strip())
            except ValueError:
                paso = 0
            if paso < 1:
                raise ValueError("Indicá cada cuántas páginas dividir con un número entero, por ejemplo 2.")
            grupos = [list(range(i, min(i + paso, n))) for i in range(0, n, paso)]
        else:
            grupos = [parse_rango(r, n) for r in str(valor).split(",") if r.strip()]
            if not grupos:
                raise ValueError("Indicá los rangos, por ejemplo: 1-3,4-8,9-")
        for i, grupo in enumerate(grupos, 1):
            out = pymupdf.open()
            try:
                for p in grupo:
                    _seguir(cancelar)
                    out.insert_pdf(d, from_page=p, to_page=p)
                ruta = os.path.join(carpeta, f"{base}_parte{i:02d}.pdf")
                _guardar(out, ruta)
            finally:
                out.close()
            generados.append(ruta)
    return generados


MB = 1024 * 1024  # como lo muestra el Explorador de Windows


def _parte_bytes(d, desde, hasta):
    """Arma en memoria el PDF con las páginas desde..hasta (0-based, inclusive), con la
    misma limpieza y opciones de guardado que _guardar, y devuelve sus bytes. Lo que se
    mide es exactamente lo que después se escribe en disco."""
    out = pymupdf.open()
    try:
        out.insert_pdf(d, from_page=desde, to_page=hasta)
        _limpiar(out)
        return out.tobytes(garbage=3, deflate=True)
    finally:
        out.close()


def dividir_por_tamano(archivo, carpeta, mb, cancelar=None):
    """Divide en partes de como máximo `mb` megabytes, con páginas consecutivas y la mayor
    cantidad de páginas que entran en cada parte. El tamaño de cada parte se mide armándola
    de verdad (los recursos compartidos, como las fuentes, se repiten en cada parte), con
    una estimación inicial proporcional y después búsqueda binaria.

    Una página que sola ya supera el límite va en una parte propia (no se puede partir una
    página). Devuelve (lista de archivos, cantidad de partes que superan el límite)."""
    try:
        limite = float(str(mb).strip().replace(",", ".")) * MB
    except ValueError:
        limite = 0
    if limite <= 0:
        raise ValueError("Indicá el tamaño máximo de cada parte en MB, por ejemplo 25.")
    os.makedirs(carpeta, exist_ok=True)
    base = os.path.splitext(os.path.basename(archivo))[0]
    generados, grandes = [], 0
    with _abrir(archivo) as d:
        n = d.page_count
        promedio = max(1.0, os.path.getsize(archivo) / max(1, n))  # bytes por página, estimado
        i = 0
        while i < n:
            quedan = n - i

            def medir(k):
                _seguir(cancelar)
                return _parte_bytes(d, i, i + k - 1)
            ok_k, ok_datos, tope = 0, None, None
            k = max(1, min(quedan, int(limite * 0.9 / promedio)))
            datos = medir(k)
            if len(datos) <= limite:
                ok_k, ok_datos = k, datos
                # crecer en proporción a lo que sobra, hasta pasarse o llegar al final
                while ok_k < quedan:
                    prueba = min(quedan, max(ok_k + 1, int(ok_k * limite / max(1, len(ok_datos)) * 0.97)))
                    datos = medir(prueba)
                    if len(datos) <= limite:
                        ok_k, ok_datos = prueba, datos
                    else:
                        tope = prueba
                        break
            else:
                tope = k
            # búsqueda binaria entre lo que entra (ok_k) y lo que no (tope)
            while tope is not None and tope - ok_k > 1:
                medio = (ok_k + tope) // 2
                datos = medir(medio)
                if len(datos) <= limite:
                    ok_k, ok_datos = medio, datos
                else:
                    tope = medio
            if ok_k == 0:  # una sola página ya supera el límite: va sola
                ok_k, ok_datos = 1, (datos if tope == 1 else medir(1))
                grandes += 1
            ruta = os.path.join(carpeta, f"{base}_parte{len(generados) + 1:02d}.pdf")
            with open(ruta, "wb") as fh:
                fh.write(ok_datos)
            generados.append(ruta)
            promedio = max(1.0, len(ok_datos) / ok_k)
            i += ok_k
    return generados, grandes


NIVELES = {  # dpi destino, calidad jpg, ¿reducir escaneos en blanco y negro?
    # Los escaneos en blanco y negro (expedientes) ya pesan poco y al bajarles la
    # resolución se pierde legibilidad: solo el nivel "alta" los toca.
    "baja": (150, 85, False),
    "media": (110, 70, False),
    "alta": (72, 50, True),
}


def comprimir(archivo, salida, nivel="media", cancelar=None):
    dpi, calidad, bitonal = NIVELES[nivel]
    with _abrir(archivo) as d:
        _seguir(cancelar)
        # MuPDF recomprime todas las imágenes de una vez: la cancelación se ve al terminar este paso
        d.rewrite_images(dpi_threshold=dpi + 10, dpi_target=dpi, quality=calidad,
                         lossy=True, lossless=True, bitonal=bitonal, color=True, gray=True)
        _seguir(cancelar)
        d.subset_fonts()
        _guardar(d, salida, garbage=4, deflate=True, deflate_images=True,
                 deflate_fonts=True, clean=True, use_objstms=1)
    antes, despues = os.path.getsize(archivo), os.path.getsize(salida)
    if despues >= antes:
        # no se guarda un archivo igual o más grande que el original
        try:
            os.remove(salida)
        except OSError:
            pass
        raise SinCambios("Este PDF ya está optimizado: comprimirlo no lo achica, así que no se "
                         "generó ningún archivo nuevo.")
    return antes, despues


def extraer_paginas(archivo, salida, rango, cancelar=None):
    with _abrir(archivo) as d:
        d.select(parse_rango(rango, d.page_count))
        _seguir(cancelar)
        _guardar(d, salida)
    return salida


def eliminar_paginas(archivo, salida, rango, cancelar=None):
    with _abrir(archivo) as d:
        quitar = set(parse_rango(rango, d.page_count))
        quedan = [i for i in range(d.page_count) if i not in quitar]
        if not quedan:
            raise ValueError("No se pueden eliminar todas las páginas.")
        d.select(quedan)
        _seguir(cancelar)
        _guardar(d, salida)
    return salida


def rotar(archivo, salida, grados=90, rango="", cancelar=None):
    with _abrir(archivo) as d:
        for i in sorted(set(parse_rango(rango, d.page_count))):  # "1-3,2" no gira dos veces la 2
            _seguir(cancelar)
            p = d[i]
            p.set_rotation((p.rotation + grados) % 360)
        _guardar(d, salida)
    return salida


def reordenar(archivo, salida, orden, cancelar=None):
    """orden: '3,1,2,4-6' -> nuevo orden de páginas."""
    with _abrir(archivo) as d:
        d.select(parse_rango(orden, d.page_count))
        _seguir(cancelar)
        _guardar(d, salida)
    return salida


def pdf_a_imagenes(archivo, carpeta, dpi=150, formato="png", cancelar=None):
    """Devuelve (lista de imágenes, cantidad de páginas que se bajaron de resolución).
    Una página enorme (por ejemplo un plano A0 a 300 dpi) se limita a MAX_PIXELES."""
    os.makedirs(carpeta, exist_ok=True)
    base = os.path.splitext(os.path.basename(archivo))[0]
    generados, reducidas = [], 0
    with _abrir(archivo, permiso=pymupdf.PDF_PERM_PRINT) as d:
        for i, p in enumerate(d, 1):
            _seguir(cancelar)
            r = p.rect
            zoom = dpi / 72
            pixeles = (r.width * zoom) * (r.height * zoom)
            if pixeles > MAX_PIXELES:  # se baja la escala lo justo para no pasar el tope
                zoom *= math.sqrt(MAX_PIXELES / pixeles) * 0.999
                reducidas += 1
            pix = p.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom))
            ruta = os.path.join(carpeta, f"{base}_pag{i:03d}.{formato}")
            if formato == "jpg":
                pix.save(ruta, jpg_quality=90)
            else:
                pix.save(ruta)
            pix = None
            generados.append(ruta)
    return generados, reducidas


TAMANOS = {"A4": pymupdf.paper_rect("a4"), "Carta": pymupdf.paper_rect("letter"), "Original": None}


def _a_8_bits(f):
    """Pasa imágenes de 16 o 32 bits a 8 bits escalando (no recortando) los valores."""
    if f.mode.startswith("I;16"):
        return f.convert("I").point(lambda i: i * (1 / 256)).convert("L")
    if f.mode in ("I", "F"):
        lo, hi = f.getextrema()
        escala = 255.0 / (hi - lo) if hi > lo else 1.0
        return f.point(lambda v: v * escala - lo * escala).convert("L")
    return f


# Bloques de un JPG que se conservan al insertarlo sin recomprimir: APP0 (JFIF), APP2 solo
# si es el perfil de color ICC, y APP14 (Adobe, indica el espacio de color). Los demás
# APPn (EXIF con GPS y modelo de celular, XMP, IPTC/Photoshop, FlashPix) y los comentarios
# se descartan. Todo lo que haya después del fin de la imagen (por ejemplo, el video de
# las "fotos con movimiento") también se descarta.
def _conservar_segmento(marca, segmento):
    if marca == 0xE2:
        return segmento[4:16] == b"ICC_PROFILE\x00"
    if marca in (0xE0, 0xEE):
        return True
    if 0xE0 <= marca <= 0xEF or marca == 0xFE:
        return False
    return True


def _jpeg_sin_metadatos(datos):
    """Devuelve el JPG sin metadatos (ver _conservar_segmento), sin recomprimir la imagen
    y cortado en el marcador de fin (FFD9). Recorre también los datos de imagen, para los
    JPG progresivos que tienen varios bloques de datos. Si la estructura no es la esperada,
    devuelve None (la imagen se recodifica con Pillow)."""
    if datos[:2] != b"\xff\xd8":
        return None
    salida = bytearray(b"\xff\xd8")
    i, n = 2, len(datos)
    while i + 1 < n:
        if datos[i] != 0xFF:
            return None
        marca = datos[i + 1]
        if marca == 0xFF:                       # relleno
            i += 1
            continue
        if marca == 0xD9:                       # fin de la imagen: se corta acá
            salida += b"\xff\xd9"
            return bytes(salida)
        if 0xD0 <= marca <= 0xD7 or marca == 0x01:
            salida += datos[i:i + 2]
            i += 2
            continue
        if i + 4 > n:
            return None
        largo = int.from_bytes(datos[i + 2:i + 4], "big")
        if largo < 2 or i + 2 + largo > n:
            return None
        segmento = datos[i:i + 2 + largo]
        if _conservar_segmento(marca, segmento):
            salida += segmento
        i += 2 + largo
        if marca == 0xDA:                       # datos de imagen hasta el próximo marcador
            j = i
            while j + 1 < n:
                if datos[j] == 0xFF and datos[j + 1] != 0x00 and not (0xD0 <= datos[j + 1] <= 0xD7):
                    break
                j += 1
            else:
                j = n
            salida += datos[i:j]
            i = j
    # sin marcador de fin (archivo truncado): se cierra la imagen igual
    salida += b"\xff\xd9"
    return bytes(salida)


def _webp_con_perdida(ruta):
    """True si el WEBP es de los comprimidos con pérdida (bloque VP8), como las fotos."""
    try:
        with open(ruta, "rb") as fh:
            cabecera = fh.read(1 << 16)
        return b"VP8 " in cabecera and b"VP8L" not in cabecera
    except OSError:
        return False


def _resolucion(res):
    """dpi de la imagen; si falta o es irreal (menos de 50 dpi) se usa 72."""
    try:
        dx, dy = (float(res[0]), float(res[1])) if res else (72.0, 72.0)
    except (TypeError, ValueError, IndexError):
        dx = dy = 72.0
    return (dx if dx >= 50 else 72.0), (dy if dy >= 50 else 72.0)


def _cuadros_imagen(ruta):
    """Abre la imagen con Pillow y devuelve (bytes, ancho_pt, alto_pt) por cada página.

    - Un TIFF de varias páginas da una página por cada una. En GIF, WEBP o PNG
      animados se usa solo el primer cuadro (una imagen = una página).
    - Las fotos "Ultra HDR" (MPO) guardan un segundo cuadro oculto: se usa el primero.
    - Respeta la orientación EXIF de las fotos de celular.
    - Un JPG que no hay que girar se inserta sin recomprimir pero SIN sus metadatos
      (EXIF con ubicación GPS, modelo de celular, autor, XMP, comentarios).
    - Las imágenes sin pérdida (PNG, BMP, TIFF, GIF) se insertan como PNG (sin pérdida);
      las fotos JPG que hay que girar, como JPEG de alta calidad. Pillow no copia los
      metadatos al recodificar.
    - Los escaneos en grises de 16 bits se escalan a 8 bits (no se recortan)."""
    cuadros = []
    with Image.open(ruta) as im:
        formato = im.format
        dpi = im.info.get("dpi")
        orientacion = im.getexif().get(0x0112, 1) if hasattr(im, "getexif") else 1
        if (formato == "JPEG" and getattr(im, "n_frames", 1) == 1 and orientacion in (0, 1)
                and im.mode in ("RGB", "L")):
            with open(ruta, "rb") as fh:
                limpio = _jpeg_sin_metadatos(fh.read())
            if limpio is not None:
                dx, dy = _resolucion(dpi)
                return [(limpio, im.width * 72.0 / dx, im.height * 72.0 / dy)]
        con_perdida = formato in ("JPEG", "MPO") or (formato == "WEBP" and _webp_con_perdida(ruta))
        fuente = ImageSequence.Iterator(im) if formato == "TIFF" else [im]
        for frame in fuente:
            f = ImageOps.exif_transpose(frame.copy())
            dx, dy = _resolucion(dpi or f.info.get("dpi"))
            buf = io.BytesIO()
            if f.mode.startswith("I") or f.mode == "F":
                f = _a_8_bits(f)
            if con_perdida and f.mode in ("RGB", "L", "CMYK", "YCbCr"):
                if f.mode not in ("RGB", "L"):
                    f = f.convert("RGB")
                f.save(buf, format="JPEG", quality=92, optimize=True)
            else:
                if f.mode == "PA":
                    f = f.convert("RGBA")
                elif f.mode not in ("1", "L", "LA", "P", "RGB", "RGBA"):
                    f = f.convert("RGB")
                f.save(buf, format="PNG", optimize=True)
            cuadros.append((buf.getvalue(), f.width * 72.0 / dx, f.height * 72.0 / dy))
    if not cuadros:
        raise ValueError(f"No se pudo leer la imagen: {os.path.basename(ruta)}")
    return cuadros


# Tamaño máximo de página que admiten los lectores de PDF (Acrobat: 200 pulgadas)
MAX_LADO_PT = 14400


def ajustar_fotos(fotos, carpeta, modo, cancelar=None):
    """Prepara fotos de la cámara para el PDF según el modo de color: "gris" (escala de
    grises con contraste automático) o "documento" (fondo de papel bien blanco y texto
    oscuro, como un escaneo). Guarda copias JPEG en "carpeta" y devuelve sus rutas."""
    salidas = []
    for i, ruta in enumerate(fotos, 1):
        _seguir(cancelar)
        with Image.open(ruta) as im:
            g = ImageOps.exif_transpose(im).convert("L")
        if modo == "documento":
            # el papel (lo más claro) pasa a blanco y la tinta se oscurece
            g = ImageOps.autocontrast(g, cutoff=(2, 12))
            g = g.point(lambda v: 255 if v > 215 else int(v * 0.92))
        else:
            g = ImageOps.autocontrast(g, cutoff=1)
        destino = os.path.join(carpeta, f"foto_{i:03d}.jpg")
        g.save(destino, format="JPEG", quality=88)
        salidas.append(destino)
    return salidas


def imagenes_a_pdf(imagenes, salida, tamano="A4", cancelar=None):
    out = pymupdf.open()
    rect_pag = TAMANOS.get(tamano)
    try:
        for img in imagenes:
            _seguir(cancelar)
            try:
                cuadros = _cuadros_imagen(img)
            except ValueError:
                raise
            except Exception:
                raise ValueError(f"No se pudo leer la imagen \u201c{os.path.basename(img)}\u201d. "
                                 "Verificá que sea JPG, PNG, BMP, TIFF o WEBP y que no esté dañada.")
            for datos, w, h in cuadros:
                if rect_pag is None:
                    if max(w, h) > MAX_LADO_PT:  # que el lector pueda abrir la página
                        escala = MAX_LADO_PT / max(w, h)
                        w, h = w * escala, h * escala
                    page = out.new_page(width=w, height=h)
                    page.insert_image(page.rect, stream=datos)
                else:
                    pr = rect_pag
                    if w > h:  # apaisada
                        pr = pymupdf.Rect(0, 0, pr.height, pr.width)
                    page = out.new_page(width=pr.width, height=pr.height)
                    margen = 20
                    page.insert_image(pr + (margen, margen, -margen, -margen), stream=datos, keep_proportion=True)
        _guardar(out, salida)
    finally:
        out.close()
    return salida


def marca_agua(archivo, salida, texto, opacidad=0.25, tamano=60, cancelar=None):
    fuente, ttf = _fuente()
    nombre = "MarcaPDF" if ttf else "helv"
    with _abrir(archivo) as d:
        for p in d:
            _seguir(cancelar)
            vis = p.rect  # la hoja tal como se ve (ya rotada)
            # centro visible pasado a coordenadas sin rotar, que es donde se escribe el texto
            centro = pymupdf.Point(vis.width / 2, vis.height / 2) * p.derotation_matrix
            t = tamano
            ancho = fuente.text_length(texto, fontsize=t)
            diagonal = (vis.width ** 2 + vis.height ** 2) ** 0.5 * 0.75
            if ancho > diagonal:  # que no se salga de la hoja
                t = t * diagonal / ancho
                ancho = diagonal
            pos = pymupdf.Point(centro.x - ancho / 2, centro.y + t / 3)
            # diagonal de abajo-izquierda a arriba-derecha tal como se ve, compensando la rotación
            m = pymupdf.Matrix(45 + p.rotation)
            p.insert_text(pos, texto, fontsize=t, fontname=nombre, fontfile=ttf,
                          color=(0.6, 0.6, 0.6), fill_opacity=opacidad, stroke_opacity=opacidad,
                          morph=(centro, m), overlay=True)
        if ttf:
            d.subset_fonts()
        _guardar(d, salida)
    return salida


def numerar(archivo, salida, posicion="abajo-centro", formato="{n} / {total}", inicio=1, tamano=10,
            cancelar=None):
    validar_formato_numeracion(formato)
    if inicio < 1:
        raise ValueError("\u201cEmpezar en\u201d tiene que ser 1 o más.")
    fuente, ttf = _fuente()
    nombre = "NumPDF" if ttf else "helv"
    with _abrir(archivo) as d:
        total = d.page_count
        for i, p in enumerate(d):
            _seguir(cancelar)
            txt = formato.format(n=i + inicio, total=total + inicio - 1)
            r = p.rect
            ancho = fuente.text_length(txt, fontsize=tamano)
            vert, hor = posicion.split("-")
            y = r.height - 20 if vert == "abajo" else 20 + tamano
            x = {"izq": 30, "centro": (r.width - ancho) / 2, "der": r.width - 30 - ancho}[hor]
            # compensar rotación de la página
            punto = pymupdf.Point(x, y) * p.derotation_matrix
            p.insert_text(punto, txt, fontsize=tamano, fontname=nombre, fontfile=ttf,
                          color=(0.2, 0.2, 0.2), rotate=p.rotation)
        if ttf:
            d.subset_fonts()
        _guardar(d, salida)
    return salida


def proteger(archivo, salida, password, cancelar=None):
    """Cifra con AES-256 con una contraseña de apertura. La misma contraseña es la de
    propietario: quien la conoce abre el PDF con todos los permisos (imprimir, copiar,
    editar) y puede quitarle la protección con "Quitar contraseña". No se marcan
    restricciones: con la clave de propietario no tendrían efecto."""
    with _abrir(archivo) as d:
        _seguir(cancelar)
        _guardar(d, salida, encryption=pymupdf.PDF_ENCRYPT_AES_256,
                 owner_pw=password, user_pw=password, permissions=PERMISOS_TODOS)
    return salida


def desproteger(archivo, salida, password, cancelar=None):
    """Quita la contraseña exigiendo siempre la clave correcta.

    - Con la clave de propietario: el resultado queda sin contraseña ni restricciones.
    - Con la clave de apertura (no la de propietario): se quita la contraseña de apertura,
      pero si el PDF tenía restricciones se mantienen (no se generan copias sin
      restricciones sin conocer la clave de propietario).
    - PDF que abre sin clave pero tiene restricciones: exige la de propietario.

    Devuelve {"restricciones_mantenidas": bool}."""
    with pymupdf.open(archivo) as d:
        if not esta_cifrado(d):
            raise ValueError("Este PDF no tiene contraseña.")
        if seguridad(d) == "libre":
            # cifrado sin clave y sin restricciones: no hay nada que proteger, se guarda sin cifrar
            _seguir(cancelar)
            _guardar(d, salida, quitar_adjuntos=False, encryption=pymupdf.PDF_ENCRYPT_NONE)
            return {"restricciones_mantenidas": False}
        pide_apertura = bool(d.needs_pass)
        rc = d.authenticate(password or "")
        # rc: 0 = incorrecta, 2 = clave de usuario (apertura), 4 = clave de propietario
        es_propietario = bool(rc & 4)
        valida = rc > 0 if pide_apertura else es_propietario
        if not valida:
            raise ValueError("Contraseña incorrecta.")
        _seguir(cancelar)
        restringido = (d.permissions & PERMISOS_TODOS) != PERMISOS_TODOS
        if not es_propietario and restringido:
            _guardar(d, salida, quitar_adjuntos=False, encryption=pymupdf.PDF_ENCRYPT_AES_256, user_pw="",
                     owner_pw=secrets.token_urlsafe(24), permissions=d.permissions)
            return {"restricciones_mantenidas": True}
        # Quitar contraseña devuelve el mismo documento: conserva los adjuntos (son parte
        # del expediente); el resto de la limpieza se aplica igual.
        _guardar(d, salida, quitar_adjuntos=False, encryption=pymupdf.PDF_ENCRYPT_NONE)
    return {"restricciones_mantenidas": False}


def pdf_a_texto(archivo, salida, cancelar=None):
    with _abrir(archivo, permiso=pymupdf.PDF_PERM_COPY) as d, open(salida, "w", encoding="utf-8") as f:
        for i, p in enumerate(d, 1):
            _seguir(cancelar)
            f.write(f"===== Página {i} =====\n")
            f.write(p.get_text())
            f.write("\n")
    return salida


def contar_adjuntos(d):
    """Archivos adjuntos: incrustados en el documento y anotaciones de archivo en las páginas."""
    n = 0
    try:
        n += d.embfile_count()
        for p in d:
            for an in p.annots(types=[pymupdf.PDF_ANNOT_FILE_ATTACHMENT]) or []:
                n += 1
    except Exception:
        pass
    return n


def contar_respuestas(d):
    """Respuestas a notas (anotaciones con /IRT). Unir y Dividir arman un PDF nuevo con
    insert_pdf de PyMuPDF, que no copia las respuestas: la interfaz avisa antes."""
    n = 0
    try:
        for p in d:
            for xref in p.annot_xrefs() or []:
                if d.xref_get_key(xref[0], "IRT")[0] != "null":
                    n += 1
    except Exception:
        pass
    return n


def info(archivo):
    """seguridad: 'libre', 'restringido' o 'clave' (ver seguridad()).
    cifrado: tiene cualquier cifrado (lo usa "Quitar contraseña").
    permisos: los permisos del PDF (para las herramientas que solo leen)."""
    with pymupdf.open(archivo) as d:
        abre = not d.needs_pass
        return {"paginas": d.page_count,
                "seguridad": seguridad(d), "cifrado": esta_cifrado(d), "pide_clave": not abre,
                "permisos": d.permissions if abre else 0,
                "firma": estado_firma(d, archivo) if abre else None,
                "firmado": (estado_firma(d, archivo) is not None) if abre else False,
                "adjuntos": contar_adjuntos(d) if abre else 0,
                "respuestas": contar_respuestas(d) if abre else 0,
                "tamano": os.path.getsize(archivo)}
