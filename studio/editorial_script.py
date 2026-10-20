"""Generate a continuous script from the approved editorial decisions."""
import json
import os
from openai import OpenAI
from src.documentary.openai_key import require_openai_api_key
from src.documentary.project import save_project


def selected(data):
    return next((o for o in data.get("options", []) if str(o.get("id")) == str(data.get("selected"))), {})


def generate(project):
    from studio.editorial import current, STAGE_IDS
    from src.documentary.script_service import save_edited_script
    ed = current(project)
    if not all(ed["stages"][k]["approved"] for k in STAGE_IDS):
        raise ValueError("Editorial approvals missing")
    data = {k: ed["stages"][k]["data"] for k in STAGE_IDS}
    acts = data["structure"]["acts"]
    duration = data["brief"]["duration_min"]
    target = round(sum(duration) / 2 * 135)
    words_per_act = round(target / len(acts))
    client = OpenAI(api_key=require_openai_api_key("Editorial script"))
    output = []
    for i, act in enumerate(acts):
        context = {
            "act": act, "index": i + 1, "total": len(acts),
            "brief": data["brief"], "locked_story": selected(data["concepts"]),
            "selected_packaging": selected(data["packaging"]),
            "complete_structure": data["structure"], "narrative_bible": data["bible"],
            "production_plan": data["production"],
            "preceding_script": "\n\n".join(output),
            "target_words_this_act": words_per_act,
            "final_act": i == len(acts) - 1,
        }
        response = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"), temperature=0.65,
            messages=[{"role": "system", "content":
                "Write one act of an original fictional story in natural spoken "
                + ("Spanish" if data["brief"]["language"] == "es" else "English")
                + f". Target {words_per_act} words for this act. Respect the locked story, chosen "
                "hook, full chronology, financial constraints, character identities and approved POV. "
                "Continue the preceding script without recap or repetition. No filler or headings. "
                "For every consequential business turnaround decision, dramatize the full causal chain: "
                "(1) a specific diagnosed business problem using concrete numbers or evidence, "
                "(2) at least two plausible alternatives and their tradeoffs, "
                "(3) the protagonist's strategic choice and why it is preferable under constraints, "
                "(4) practical execution: negotiations, operational actions, people, contracts and timeline, "
                "(5) measurable financial/operational result AND unintended consequences. "
                "Show smart decisions through scenes and causal actions, NEVER empty claims like "
                "'improved management', 'worked hard', 'secured funding', 'restructured debt' or "
                "'saved the company' without showing exactly HOW. Some choices should fail and "
                "force a revised strategy. Do not invent convenient last-minute investors. "
                "A thirty-day deadline may yield a credible standstill, NOT miraculous complete "
                "repayment of impossible debts; long-term recovery requires time. "
                "Make the protagonist's decision logic legible without lecturing or dumping accounting. "
                "Only the final act resolves the approved ending. Do not present fiction as fact."},
                {"role": "user", "content": json.dumps(context, ensure_ascii=False)}])
        segment = (response.choices[0].message.content or "").strip()
        if not segment:
            raise ValueError("Empty act; the previous script remains saved")
        output.append(segment)
    script = "\n\n".join(output)
    words = len(script.split())
    if words < duration[0] * 110 or words > duration[1] * 165:
        raise ValueError(f"El guion tiene {words} palabras y no alcanza la duración elegida. Reintentá; conservamos el anterior.")
    project["target_words"] = target
    project = save_edited_script(project, script)
    project["editorial_audit"] = {}
    project["editorial_script_quality"] = {"word_count": words, "requires_human_review": True}
    save_project(project)
    return project
