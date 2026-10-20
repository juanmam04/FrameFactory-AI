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
    from studio.story_architect import architecture, evaluate, local_warnings
    plan = architecture(client, data, project.get("creative_rules") or [])
    output = []
    reviews = []
    for i, act in enumerate(acts):
        context = {
            "act": act, "architecture_act": plan["acts"][i],
            "previous_story_states": [x.get("ending_state") for x in plan["acts"][:i]], "index": i + 1, "total": len(acts),
            "brief": data["brief"], "locked_story": selected(data["concepts"]),
            "selected_packaging": selected(data["packaging"]),
            "complete_structure": data["structure"], "narrative_bible": data["bible"],
            "production_plan": data["production"],
            "preceding_script": "\n\n".join(output),
            "target_words_this_act": words_per_act,
            "permanent_creative_rules": project.get("creative_rules") or [],
            "final_act": i == len(acts) - 1,
        }
        for attempt in range(3):
            context["revision_feedback"] = reviews[-1].get("issues", []) if attempt and reviews else []
            response = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"), temperature=0.65,
            messages=[{"role": "system", "content":
                "Write one act of an original fictional story in natural spoken "
                + ("Spanish" if data["brief"]["language"] == "es" else "English")
                + f". Target {words_per_act} words for this act. Respect the locked story, chosen "
                "hook, full chronology, financial constraints, character identities and approved POV. "
                "Continue the preceding script without recap or repetition. No filler or headings. "
                "ENTERTAINMENT FIRST. This is a heightened fictional adventure told as POV, not an "
                "MBA lecture or a realistic case study. Open major scenes with dramatic events, "
                "unexpected setbacks and a difficult choice. Show HOW the protagonist actually "
                "responds through clever concrete actions and plans, conflicting choices, "
                "bold negotiations, clever gambles, imperfect execution and spectacular consequences. "
                "Make the decisions entertaining to WATCH, not just to explain: stakes must escalate "
                "and plans can backfire. Numbers may be exaggerated for dramatic effect. Do not "
                "overexplain accountancy, insist on mundane financing rules or diminish extraordinary "
                "events to satisfy real-world plausibility. Keep character goals, prior events and "
                "established story facts consistent. Avoid empty montage summaries of 'worked hard'. "
                "In act ONE of an acquisition story, show how the protagonist hears about the deal, "
                "why the previous owner hands over the business for one dollar, the offer, "
                "acceptance, key handover, hidden problems and deadline BEFORE the first arrival. "
                "Never start inside a business as owner without showing the actual acquisition. "
                "Do not replay the same event or have characters forget their earlier development. "
                "Obey every user-approved permanent creative rule in the project. "
                "Only the final act resolves the approved ending. Do not present fiction as fact."},
                {"role": "user", "content": json.dumps(context, ensure_ascii=False)}])
            segment = (response.choices[0].message.content or "").strip()
            if not segment:
                raise ValueError("Acto vacío. Se conserva el guion anterior.")
            decision = evaluate(client,plan=plan,act_number=i,candidate=segment,previous=output,brief=data["brief"],rules=project.get("creative_rules") or [])
            local = local_warnings(segment,first=i==0,acquisition=any(w in str(selected(data["concepts"])).lower() for w in ("compr","adquir","buy","purchase","us$1")))
            if local: decision["issues"] = list(decision.get("issues") or []) + local
            reviews.append({"act":i+1,"attempt":attempt+1,**decision})
            if decision.get("verdict")=="pass" and not local: break
            if attempt==2:
                raise ValueError("El acto "+str(i+1)+" no superó la revisión narrativa: "+str(decision.get("issues") or [])[:260]+". Se conservó el guion anterior.")
        output.append(segment)
    script = "\n\n".join(output)
    words = len(script.split())
    if words < duration[0] * 110 or words > duration[1] * 165:
        raise ValueError(f"El guion tiene {words} palabras y no alcanza la duración elegida. Reintentá; conservamos el anterior.")
    project["target_words"] = target
    project["narrative_architecture"] = plan
    project = save_edited_script(project, script)
    project["editorial_audit"] = {}
    project["editorial_script_quality"] = {"word_count": words, "requires_human_review": True, "act_reviews": reviews, "architecture_complete": True}
    save_project(project)
    return project
