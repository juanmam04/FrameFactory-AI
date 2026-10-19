"""Approved editorial workflow script adapter."""
import json
import os
from openai import OpenAI
from src.documentary.openai_key import require_openai_api_key
from src.documentary.project import save_project

def generate(project):
    from studio.editorial import current, STAGE_IDS
    ed=current(project)
    if not all(ed["stages"][k]["approved"] for k in STAGE_IDS):
        raise ValueError("Editorial approvals missing")
    data={k:ed["stages"][k]["data"] for k in STAGE_IDS}
    lang=data["brief"]["language"]
    acts=data["structure"]["acts"]
    model=os.getenv("OPENAI_MODEL","gpt-4o-mini")
    client=OpenAI(api_key=require_openai_api_key("Editorial script"))
    output=[]
    for i, act in enumerate(acts):
        context={"act":act,"index":i+1,"total":len(acts),"brief":data["brief"],
                 "narrative_bible":data["bible"],"selected_packaging":data["packaging"],
                 "preceding_excerpt":output[-1][-1800:] if output else ""}
        response=client.chat.completions.create(model=model,temperature=0.65,messages=[
          {"role":"system","content":"Write one substantial act of an original fictional story in natural spoken "+("Spanish" if lang=="es" else "English")+". Respect chronology, numerical constraints, character identities, approved narrative perspective and the chosen hook. No filler or headings. Write approximately 350-500 words per act. Do not present fiction as historical fact."},
          {"role":"user","content":json.dumps(context,ensure_ascii=False)}])
        segment=(response.choices[0].message.content or "").strip()
        if not segment: raise ValueError("Empty act")
        output.append(segment)
    script="\n\n".join(output)
    project["script"]=script
    project["script_approved"]=False
    project["fact_check_status"]="pending"
    project["editorial_script_quality"]={"word_count":len(script.split()),"requires_human_review":True}
    save_project(project)
    return project
