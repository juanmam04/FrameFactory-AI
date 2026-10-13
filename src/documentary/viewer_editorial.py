"""Editorial checks with evidence, not a prediction of views or a quality score."""
from __future__ import annotations
import re
from collections import Counter
from typing import Any

VIEWER_BRIEF = """
FINAL EDITORIAL PRIORITY — judge this as a viewer choosing whether to keep watching:
The first 60–75 words must reveal this episode's specific promise, surprising problem or costly decision. Age, job and biography are optional context, not the hook. Do not force 'Hay una razón' or the same purchase formula into every premise.
Every scene changes at least one thing: what the protagonist knows, wants, can lose, chooses, or must do next. A quiet scene can earn its place by making that change visible; stillness alone is not development.
Show an attempt, resistance, decision and consequence. Progress is not 'with time the community grows'. Show what someone tried and why the result creates the next problem.
Entertaining need not mean jokes: use irony, awkward human reactions, a surprising consequence or a recurring detail with a payoff when this story supports it. Do not add random comedy or humiliation.
Make the premise's best moment happen on screen early enough to reward the click. Later turns change the situation rather than repeating bigger versions of the same success.
Use money only when it changes a choice or a risk. One meaningful figure beats six percentages. Do not invent exact dates/numbers to sound specific. Preserve all locked facts; uncertain documentary facts stay uncertain.
Earn the ending: resolve the opening promise through a concrete outcome or changed choice. One final image; no repeated endings, motivational sermon, or generic unknown caller.
Duration follows story substance. If short, expand unused causal events in the supplied story, not glasses of water, windows, silent waiting, repeated morals or invented new facts. A tighter shorter story is preferable to empty minutes.
Output natural spoken narration only, no titles, headings or production instructions.
""".strip()

_FILLER = (
    'el futuro está lleno de posibilidades', 'la aventura apenas comienza',
    'cada desafío es una oportunidad', 'arquitecto de tu destino',
    'cada pequeño paso cuenta', 'has creado algo más que un negocio',
    'con una visión clara', 'sientes que has tomado una decisión audaz',
    'el minuto se estira hasta volverse parte de la escena',
    'esta vida pide ese sorbo', 'la escena no se corta porque tú no la cortas',
    'meteoric rise', 'cautionary tale', 'broader implications',
    'the importance of', 'only time will tell',
)
_PASSIVE = ('miras por la ventana', 'tomas un sorbo', 'te secas despacio',
            'cuentas las respiraciones', 'te sientas otra vez', 'enciendes una lámpara')


def review_script(script: str) -> dict[str, Any]:
    text = (script or '').strip()
    low = text.casefold()
    findings: list[dict[str, Any]] = []
    def add(code: str, severity: str, message: str, evidence: list[str]):
        findings.append(dict(code=code, severity=severity, message=message, evidence=evidence[:5]))
    filler = [phrase for phrase in _FILLER if phrase in low]
    if filler:
        add('generic_filler', 'rewrite' if len(filler) >= 3 else 'review',
            'Reemplazá frases genéricas por acciones y consecuencias propias de esta historia.', filler)
    counts = Counter(s.strip().casefold() for s in re.split(r'(?<=[.!?])\s+', text)
                     if len(s.split()) >= 7)
    repeated = [s for s, n in counts.items() if n >= 3]
    if repeated:
        add('repetition', 'rewrite', 'Hay oraciones repetidas tres veces o más; no son nuevos beats.', repeated)
    passive = [phrase for phrase in _PASSIVE if low.count(phrase) >= 2]
    if len(passive) >= 2:
        add('synthetic_padding', 'rewrite', 'Pausas y gestos intercambiables alargan el guion sin desarrollar la historia.', passive)
    tail = ' '.join(low.split()[-250:])
    endings = [p for p in ('apenas comienza', 'lejos de haber terminado', 'lleno de posibilidades',
                          'cada paso', 'camino correcto', 'es solo el principio') if p in tail]
    if len(endings) >= 2:
        add('unearned_ending', 'rewrite', 'El cierre repite promesas de futuro en lugar de pagar la historia.', endings)
    opener = ' '.join(text.split()[:75])
    if re.search(r'(?i)hoy (vamos|te voy)|en este video|bienvenid', opener):
        add('intro_before_story', 'review', 'Entrá directamente en la situación que motivó el clic.', [opener])
    return {'method': 'editorial_heuristics', 'findings': findings,
            'needs_rewrite': any(f['severity'] == 'rewrite' for f in findings),
            'opening': opener, 'word_count': len(text.split()),
            'requires_human_review': True}


def revision_prompt(script: str, facts: dict[str, Any], review: dict[str, Any], target: int) -> str:
    import json
    return (VIEWER_BRIEF + '\n\nRewrite the complete narration, preserving the supplied facts. '
            f'Aim for {target} words only if meaningful material supports them. '
            'Do not preserve padding just to retain length. Add only causal scenes grounded in the supplied beats.\n'
            + json.dumps({'facts': facts, 'editorial_findings': review['findings'], 'draft': script}, ensure_ascii=False))
