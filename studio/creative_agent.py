"""Conversational editor for a FrameFactory project. No autonomous or unapproved writes."""
import json
import os
from datetime import datetime, timezone
from typing import Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from studio.editorial import _load, current
from src.documentary.project import save_project

router=APIRouter(prefix="/api/projects",tags=["creative-agent"])

class AgentMessage(BaseModel):
    message:str=Field(min_length=3,max_length=4000)
    project_snapshot:dict[str,Any]|None=None
    creative_rules:list[str]=Field(default_factory=list)

class AgentRevision(BaseModel):
    instruction:str=Field(min_length=4,max_length=3000)
    scope:str="opening"
    project_snapshot:dict[str,Any]|None=None
    creative_rules:list[str]=Field(default_factory=list)

class RuleApproval(BaseModel):
    rule:str=Field(min_length=8,max_length=700)
    project_snapshot:dict[str,Any]|None=None

def _client():
    from openai import OpenAI
    from src.documentary.openai_key import require_openai_api_key
    return OpenAI(api_key=require_openai_api_key("FrameFactory Agente Editorial"))

def _llm(messages,*,json_mode=False,temperature=0.45):
    kwargs={"model":os.getenv("OPENAI_MODEL","gpt-4o-mini"),"temperature":temperature,"messages":messages}
    if json_mode: kwargs["response_format"]={"type":"json_object"}
    return (_client().chat.completions.create(**kwargs).choices[0].message.content or "").strip()

def _context(p):
    ed=current(p) if p.get("editorial") else {}
    stages=ed.get("stages",{})
    chosen={}
    for key in ("concepts","packaging"):
        data=stages.get(key,{}).get("data",{})
        chosen[key]=next((x for x in data.get("options",[]) if str(x.get("id"))==str(data.get("selected"))),{})
    return {"title":p.get("title"),"topic":p.get("topic"),"brief":stages.get("brief",{}).get("data",{}),
            "approved_story":chosen.get("concepts"),"approved_packaging":chosen.get("packaging"),
            "structure":stages.get("structure",{}).get("data",{}),"bible":stages.get("bible",{}).get("data",{}),
            "script":str(p.get("script") or "")[:28000],
            "existing_rules":p.get("creative_rules") or [],
            "previous_feedback":(p.get("creative_agent_history") or [])[-5:]}

@router.post("/{project_id}/agent/chat")
def agent_chat(project_id:str,body:AgentMessage):
    p=_load(project_id,body.project_snapshot)
    rules=list(dict.fromkeys([*p.get("creative_rules",[]),*body.creative_rules]))[:35]
    context=_context(p);context["existing_rules"]=rules
    try:
        result=json.loads(_llm([
            {"role":"system","content":(
                "You are the built-in FrameFactory creative director. Respond in the user's language. "
                "Treat the entire video as FICTION DESIGNED FOR ENTERTAINMENT. "
                "Diagnose narrative problems precisely and offer concrete, actionable fixes. "
                "An acquisition story must show the handover/bargain and deadline early, not begin "
                "with the protagonist already owning the property. Check for duplicate event loops, "
                "contradictory characters, weak stakes, coincidental rescues, unexplained recovery, "
                "and POV/language inconsistency. Respect selected title, premise and established events. "
                "Propose a useful REUSABLE writing rule if feedback should apply to future videos, "
                "but DO NOT say that any fix or permanent rule was already applied. "
                "Always return a JSON object with reply (clear specific advice), proposed_rule "
                "(short reusable rule or empty string), suggested_edit (specific instruction for "
                "a script revision or empty string), suggested_scope ('opening' or 'full'). "
                "Never execute repository changes or claim you edited files.")},
            {"role":"user","content":json.dumps({"feedback":body.message,"project":context},ensure_ascii=False)}
        ],json_mode=True))
        answer={"reply":str(result.get("reply") or "Revisá los problemas señalados."),
                "proposed_rule":str(result.get("proposed_rule") or "")[:700],
                "suggested_edit":str(result.get("suggested_edit") or "")[:3000],
                "suggested_scope":result.get("suggested_scope") if result.get("suggested_scope") in ("opening","full") else "opening"}
        p.setdefault("creative_agent_history",[]).append({"at":datetime.now(timezone.utc).isoformat(),
             "feedback":body.message,"reply":answer["reply"]})
        p["creative_agent_history"]=p["creative_agent_history"][-30:]
        save_project(p)
        return answer
    except Exception as e:
        raise HTTPException(502,"No se pudo consultar el agente: "+str(e)[:200]) from e

@router.post("/{project_id}/agent/revise")
def revise_with_agent(project_id:str,body:AgentRevision):
    p=_load(project_id,body.project_snapshot)
    script=str(p.get("script") or "").strip()
    if not script: raise HTTPException(409,"Este proyecto todavía no tiene un guion.")
    if p.get("script_approved"): raise HTTPException(409,"El guion está aprobado. Reabrilo antes de modificarlo.")
    scope=body.scope if body.scope in ("opening","full") else "opening"
    # Large full rewrites must be planned separately, not silently truncate a script.
    if scope=="full" and len(script)>13500:
        raise HTTPException(422,"El guion es demasiado largo para una reescritura completa segura. Elegí corregir el inicio.")
    cut=min(len(script),6500)
    if scope=="opening":
        boundary=script.rfind("\n\n",0,cut)
        if boundary>1200:cut=boundary
    original=script if scope=="full" else script[:cut]
    rest="" if scope=="full" else script[cut:]
    context=_context(p);context.pop("script",None)
    rules=list(dict.fromkeys([*p.get("creative_rules",[]),*body.creative_rules]))[:35]
    try:
        edited=_llm([
          {"role":"system","content":(
            "Rewrite the given fictional POV narrative according to the user's requested edit. "
            "Return ONLY revised narration, not commentary, headings, markdown or a summary. "
            "Keep the same selected story, perspective and characters. Focus on entertaining scenes "
            "with actual events, actions, decisions and consequences. Do not repeat scenes. "
            "For acquisitions show HOW and WHY the protagonist receives the keys, the symbolic "
            "transaction, the catch, the countdown, THEN the first entrance. Keep comparable "
            "length to the original, and ensure a smooth transition into any untouched remainder. "
            "Use the requested language and the permanent editorial rules.")},
          {"role":"user","content":json.dumps({"user_instruction":body.instruction,
             "permanent_rules":rules,"project":context,"text_to_rewrite":original,
             "next_untouched_text":rest[:700]},ensure_ascii=False)}
        ],temperature=0.6)
        if len(edited.split())<max(60,int(len(original.split())*0.45)):
            raise ValueError("La corrección quedó demasiado corta. Se conservó el guion.")
        previous=script
        from src.documentary.script_service import save_edited_script
        p=save_edited_script(p,edited+rest)
        p.setdefault("creative_agent_revisions",[]).append({
          "at":datetime.now(timezone.utc).isoformat(),"instruction":body.instruction,
          "scope":scope,"previous_script":previous})
        p["creative_agent_revisions"]=p["creative_agent_revisions"][-4:]
        p["creative_rules"]=rules
        save_project(p)
        return {"applied":True,"scope":scope,"script":p["script"],
                "note":"Guion actualizado. La aprobación y auditoría se reiniciaron para revisarlo."}
    except HTTPException: raise
    except Exception as e:raise HTTPException(502,"No se pudo aplicar la corrección: "+str(e)[:200]) from e

@router.post("/{project_id}/agent/rule")
def approve_creative_rule(project_id:str,body:RuleApproval):
    p=_load(project_id,body.project_snapshot)
    rules=p.setdefault("creative_rules",[])
    rule=body.rule.strip()
    if rule.casefold() not in [x.casefold() for x in rules]:
        rules.append(rule)
    p["creative_rules"]=rules[-35:]
    save_project(p)
    return {"approved":True,"creative_rules":p["creative_rules"]}
