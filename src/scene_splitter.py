"""FASE 4: División automática del guion en escenas con duración estimada."""
import re
from dataclasses import dataclass

from .config_loader import get_duracion_por_imagen


@dataclass
class Escena:
    numero: int
    texto: str
    duracion_segundos: float


def _split_oraciones(texto: str) -> list[str]:
    """Divide un texto en oraciones (evitando cortar en abreviaturas como Sr., etc.)."""
    if not texto or not texto.strip():
        return []
    # Cortar por . seguido de espacio y mayúscula, o por . al final
    partes = re.split(r'(?<=[.!?])\s+(?=[A-ZÁÉÍÓÚÜ])', texto.strip())
    return [p.strip() for p in partes if p.strip()]


def _expandir_parrafo_en_escenas(parrafo: str, seg: float, palabras_por_escena: int = 18) -> list[str]:
    """
    Si un párrafo es largo, lo divide en varias escenas por oraciones,
    agrupando ~palabras_por_escena palabras por escena (~5 s de narración).
    """
    parrafo = (parrafo or "").strip()
    if not parrafo:
        return []
    oraciones = _split_oraciones(parrafo)
    if not oraciones:
        return [parrafo]
    # Si hay pocas oraciones o el párrafo es corto, una sola escena
    total_palabras = len(parrafo.split())
    if len(oraciones) <= 1 or total_palabras <= palabras_por_escena:
        return [parrafo]
    # Agrupar oraciones hasta ~palabras_por_escena por escena
    bloques = []
    actual = []
    palabras_actual = 0
    for oracion in oraciones:
        n = len(oracion.split())
        if palabras_actual + n > palabras_por_escena and actual:
            bloques.append(" ".join(actual))
            actual = [oracion]
            palabras_actual = n
        else:
            actual.append(oracion)
            palabras_actual += n
    if actual:
        bloques.append(" ".join(actual))
    return bloques


def dividir_en_escenas(guion: str, segundos_por_imagen: float | None = None) -> list[Escena]:
    """
    Divide el guion en escenas: primero por párrafos; si un párrafo es largo,
    lo subdivide por oraciones para que cada escena sea ~5 s (una imagen por beat narrativo).
    """
    seg = segundos_por_imagen or get_duracion_por_imagen()
    # ~18 palabras ≈ 5 s de narración en español
    palabras_por_escena = max(12, int(seg * 3.5))

    # Párrafos (doble salto)
    parrafos = [p.strip() for p in guion.strip().split("\n\n") if p.strip()]
    if len(parrafos) <= 1:
        parrafos = [p.strip() for p in guion.strip().split("\n") if p.strip()]
    if not parrafos:
        parrafos = [guion.strip() or "Escena"]

    bloques = []
    for parrafo in parrafos:
        sub = _expandir_parrafo_en_escenas(parrafo, seg, palabras_por_escena)
        bloques.extend(sub)

    # Log para debugging
    print(f"📝 Guion dividido en {len(bloques)} escenas")
    print(f"   Longitud total del guion: {len(guion)} caracteres")
    print(f"   Total de palabras estimadas: {len(guion.split())}")

    escenas = [
        Escena(numero=i + 1, texto=t, duracion_segundos=seg)
        for i, t in enumerate(bloques)
    ]

    escenas_vacias = [e for e in escenas if not e.texto.strip()]
    if escenas_vacias:
        print(f"⚠️ ADVERTENCIA: {len(escenas_vacias)} escenas vacías detectadas")

    return escenas


def escenas_a_texto_continuo(escenas: list[Escena]) -> str:
    """
    Texto completo del guion (para TTS), uniendo todas las escenas.
    Asegura que el texto esté completo y bien formateado.
    """
    if not escenas:
        print("⚠️ ADVERTENCIA: No hay escenas para convertir a texto continuo")
        return ""
    
    # Filtrar escenas vacías
    escenas_validas = [e for e in escenas if e.texto.strip()]
    
    if not escenas_validas:
        print(f"⚠️ ADVERTENCIA: Todas las {len(escenas)} escenas están vacías")
        return ""
    
    # Unir todas las escenas con espacios, preservando la estructura
    texto_completo = " ".join(e.texto.strip() for e in escenas_validas)
    
    # Verificar que no esté vacío
    if not texto_completo.strip():
        print(f"⚠️ ADVERTENCIA: Texto de narración vacío después de unir {len(escenas_validas)} escenas")
        # Intentar obtener texto de otra forma
        texto_completo = "\n\n".join(e.texto for e in escenas_validas)
    
    # Log para debugging
    palabras_total = len(texto_completo.split())
    caracteres_total = len(texto_completo)
    print(f"🔊 Texto de narración generado:")
    print(f"   Escenas procesadas: {len(escenas_validas)} de {len(escenas)}")
    print(f"   Palabras totales: {palabras_total}")
    print(f"   Caracteres totales: {caracteres_total}")
    print(f"   Primeros 100 caracteres: {texto_completo[:100]}...")
    print(f"   Últimos 100 caracteres: ...{texto_completo[-100:]}")
    
    return texto_completo
