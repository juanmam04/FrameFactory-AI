"""Generación y verificación de descripciones visuales por escena para coherencia de imágenes."""
import json
import os
import re

from .config_loader import get_instrucciones_descripcion_escenas
from .scene_splitter import Escena

# Reintentos de corrección tras verificación fallida (por ronda de corrección)
MAX_CORRECCIONES = 2


def generar_descripciones_visuales_escenas(
    escenas: list[Escena],
    tema: str | None = None,
    verificar_y_corregir: bool = False,
) -> list[str]:
    """
    Genera una descripción visual (para prompt de imagen) por cada escena usando OpenAI.
    La verificación posterior está desactivada por defecto (verificar_y_corregir=False).
    """
    if not escenas:
        return []

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return _fallback_descripciones(escenas)

    descripciones = _generar_descripciones_una_vez(escenas, tema)
    if not descripciones or len(descripciones) != len(escenas):
        return _fallback_descripciones(escenas)

    if verificar_y_corregir:
        descripciones = _verificar_y_corregir_loop(escenas, descripciones, tema)
    return descripciones


def _generar_descripciones_una_vez(escenas: list[Escena], tema: str | None) -> list[str]:
    """Una sola pasada de generación de descripciones."""
    instrucciones = get_instrucciones_descripcion_escenas()
    system_prompt = instrucciones.get(
        "system_prompt",
        "Generás una descripción visual corta por cada escena para usarla como prompt de imagen. "
        "Devolvé JSON: {\"descripciones\": [\"...\", \"...\", ...]} en el mismo orden que las escenas.",
    )
    user_template = instrucciones.get(
        "user_prompt_template",
        "Tema: {tema}\n\nEscenas:\n{escenas_texto}\n\nDevolvé solo JSON con clave \"descripciones\" (array de strings).",
    )
    bloques = [f"ESCENA {i}:\n{e.texto.strip()}" for i, e in enumerate(escenas, start=1)]
    escenas_texto = "\n\n".join(bloques)
    user_prompt = user_template.format(tema=tema or "Video narrativo", escenas_texto=escenas_texto)

    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        response = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.4,
        )
        content = (response.choices[0].message.content or "").strip()
        return _parsear_descripciones_json(content, len(escenas))
    except Exception as e:
        print(f"⚠️ Error generando descripciones por escena: {e}.")
    return []


def verificar_descripciones_escenas(
    escenas: list[Escena],
    descripciones: list[str],
) -> list[dict]:
    """
    Verifica que cada descripción visual concuerde con su tramo del guion.
    Retorna lista de dicts con keys: ok (bool), problema (str|None), sugerencia (str|None).
    """
    if not escenas or not descripciones or len(escenas) != len(descripciones):
        return []

    instrucciones = get_instrucciones_descripcion_escenas()
    system = instrucciones.get("verification_system_prompt", "").strip()
    user_tpl = instrucciones.get("verification_user_prompt_template", "").strip()
    if not system or not user_tpl:
        return [{"ok": True, "problema": None, "sugerencia": None} for _ in escenas]

    pares = []
    for i, (e, d) in enumerate(zip(escenas, descripciones), start=1):
        pares.append(f"--- ESCENA {i} ---\nGUION:\n{e.texto.strip()}\n\nDESCRIPCIÓN VISUAL:\n{d.strip()}")
    pares_escena_descripcion = "\n\n".join(pares)
    user_prompt = user_tpl.format(pares_escena_descripcion=pares_escena_descripcion)

    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        response = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
        )
        content = (response.choices[0].message.content or "").strip()
        return _parsear_resultados_verificacion(content, len(escenas))
    except Exception as e:
        print(f"⚠️ Error en verificación de descripciones: {e}, se aceptan todas.")
    return [{"ok": True, "problema": None, "sugerencia": None} for _ in escenas]


def _parsear_resultados_verificacion(content: str, esperados: int) -> list[dict]:
    """Extrae resultados de verificación del JSON del modelo."""
    match = re.search(r"\{[\s\S]*\}", content)
    if match:
        content = match.group(0)
    try:
        data = json.loads(content)
        resultados = data.get("resultados") or data.get("results") or []
        if not isinstance(resultados, list):
            return [{"ok": True, "problema": None, "sugerencia": None} for _ in range(esperados)]
        out = []
        for i in range(esperados):
            if i < len(resultados):
                r = resultados[i]
                if isinstance(r, dict):
                    out.append({
                        "ok": bool(r.get("ok", True)),
                        "problema": r.get("problema") or r.get("problem"),
                        "sugerencia": r.get("sugerencia") or r.get("suggestion"),
                    })
                else:
                    out.append({"ok": True, "problema": None, "sugerencia": None})
            else:
                out.append({"ok": True, "problema": None, "sugerencia": None})
        return out
    except json.JSONDecodeError:
        pass
    return [{"ok": True, "problema": None, "sugerencia": None} for _ in range(esperados)]


def _regenerar_descripciones_fallidas(
    escenas: list[Escena],
    descripciones_actuales: list[str],
    indices_fallidos: list[int],
    resultados_verificacion: list[dict],
    tema: str | None,
) -> list[str]:
    """Re-genera solo las descripciones de las escenas que fallaron, usando problema/sugerencia."""
    if not indices_fallidos:
        return list(descripciones_actuales)

    instrucciones = get_instrucciones_descripcion_escenas()
    system = instrucciones.get("correction_system_prompt", "").strip()
    user_tpl = instrucciones.get("correction_user_prompt_template", "").strip()
    if not system or not user_tpl:
        return list(descripciones_actuales)

    bloques = []
    for idx in indices_fallidos:
        e = escenas[idx]
        r = resultados_verificacion[idx]
        problema = r.get("problema") or "no especificado"
        sugerencia = r.get("sugerencia") or "ajustar la descripción al guion"
        bloques.append(
            f"ESCENA (índice {idx + 1}):\n{e.texto.strip()}\n\n"
            f"Problema detectado: {problema}\nSugerencia: {sugerencia}"
        )
    bloques_fallidos = "\n\n".join(bloques)
    user_prompt = user_tpl.format(tema=tema or "Video narrativo", bloques_fallidos=bloques_fallidos)

    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        response = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
        )
        content = (response.choices[0].message.content or "").strip()
        nuevas = _parsear_descripciones_json(content, len(indices_fallidos))
        if len(nuevas) != len(indices_fallidos):
            return list(descripciones_actuales)
        result = list(descripciones_actuales)
        for k, idx in enumerate(indices_fallidos):
            result[idx] = nuevas[k]
        return result
    except Exception as e:
        print(f"⚠️ Error corrigiendo descripciones fallidas: {e}.")
    return list(descripciones_actuales)


def _verificar_y_corregir_loop(
    escenas: list[Escena],
    descripciones: list[str],
    tema: str | None,
) -> list[str]:
    """Verifica cada descripción; si alguna no concuerda con el guion, la re-genera y repite hasta MAX_CORRECCIONES."""
    for ronda in range(MAX_CORRECCIONES):
        resultados = verificar_descripciones_escenas(escenas, descripciones)
        indices_fallidos = [i for i, r in enumerate(resultados) if not r.get("ok")]
        if not indices_fallidos:
            if ronda > 0:
                print(f"   Todas las descripciones pasaron la verificación (ronda {ronda + 1}).")
            return descripciones
        print(f"   Verificación: {len(indices_fallidos)} escena(s) no concuerdan con el guion; corrigiendo...")
        for i in indices_fallidos:
            r = resultados[i]
            print(f"      Escena {i + 1}: {r.get('problema') or 'sin detalle'}")
        descripciones = _regenerar_descripciones_fallidas(
            escenas, descripciones, indices_fallidos, resultados, tema
        )
    # Última verificación: si aún hay fallos, los dejamos pero se informó
    resultados_final = verificar_descripciones_escenas(escenas, descripciones)
    fallos = [i + 1 for i, r in enumerate(resultados_final) if not r.get("ok")]
    if fallos:
        print(f"   Aviso: tras {MAX_CORRECCIONES} correcciones, escenas {fallos} siguen con posibles incoherencias.")
    return descripciones


def _parsear_descripciones_json(content: str, esperadas: int) -> list[str]:
    """Extrae el array de descripciones del JSON devuelto por el modelo."""
    # Intentar sacar solo el JSON si el modelo añadió texto
    content = content.strip()
    match = re.search(r"\{[\s\S]*\}", content)
    if match:
        content = match.group(0)
    try:
        data = json.loads(content)
        desc = data.get("descripciones") or data.get("descriptions") or []
        if isinstance(desc, list) and len(desc) >= esperadas:
            return [str(d).strip() for d in desc[:esperadas]]
        if isinstance(desc, list):
            # Rellenar si faltan
            while len(desc) < esperadas:
                desc.append("")
            return [str(d).strip() for d in desc[:esperadas]]
    except json.JSONDecodeError:
        pass
    return []


def _fallback_descripciones(escenas: list[Escena]) -> list[str]:
    """Fallback sin API: usar el texto de la escena truncado como descripción visual."""
    return [e.texto[:300].replace("\n", " ").strip() for e in escenas]
