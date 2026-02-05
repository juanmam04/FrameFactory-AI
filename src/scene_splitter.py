"""FASE 4: División automática del guion en escenas con duración estimada."""
from dataclasses import dataclass

from .config_loader import get_duracion_por_imagen


@dataclass
class Escena:
    numero: int
    texto: str
    duracion_segundos: float


def dividir_en_escenas(guion: str, segundos_por_imagen: float | None = None) -> list[Escena]:
    """
    Divide el guion en escenas por párrafos.
    Cada escena tiene duración estimada (por defecto 5 segundos).
    """
    seg = segundos_por_imagen or get_duracion_por_imagen()
    
    # Intentar dividir por párrafos dobles primero
    bloques = [p.strip() for p in guion.strip().split("\n\n") if p.strip()]
    
    # Si no hay párrafos dobles, intentar por párrafos simples
    if len(bloques) <= 1:
        bloques = [p.strip() for p in guion.strip().split("\n") if p.strip()]
    
    # Si aún no hay bloques, usar el texto completo
    if not bloques:
        bloques = [guion.strip() or "Escena"]
    
    # Log para debugging
    print(f"📝 Guion dividido en {len(bloques)} escenas")
    print(f"   Longitud total del guion: {len(guion)} caracteres")
    print(f"   Total de palabras estimadas: {len(guion.split())}")
    
    escenas = [
        Escena(numero=i + 1, texto=t, duracion_segundos=seg)
        for i, t in enumerate(bloques)
    ]
    
    # Verificar que todas las escenas tengan texto
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
