"""Narrative story architect and continuity gates. Fiction should entertain, not repeat itself."""
import json
import os
import re

BAD_PHRASES=("no podemos rendirnos","la presión aumenta","la energía regresa","esto apenas comienza")
def selected(options):
    return next((x for x in options.get("options",[]) if str(x.get("id"))==str(options.get("selected"))),{})

def model_json(client,system,payload):
    result=client.chat.completions.create(model=os.getenv("FRAMEFACTORY_WRITER_MODEL",os.getenv("OPENAI_MODEL","gpt-4o-mini")),
        temperature=0.45,response_format={"type":"json_object"},
        messages=[{"role":"system","content":system},{"role":"user","content":json.dumps(payload,ensure_ascii=False)}])
    return json.loads(result.choices[0].message.content or "{}")

def architecture(client,data,rules):
    acts=data["structure"]["acts"]
    story=selected(data["concepts"])
    packaging=selected(data["packaging"])
    spec={
      "locked_story":story,"locked_packaging":packaging,"outline":acts,
      "bible":data["bible"],"user_rules":rules,
      "language":data["brief"].get("language","es"),
      "pov":data["brief"].get("narration","segunda persona")}
    system=("You are an elite fictional POV story architect. Entertainment first. "
      "Build exactly one continuous story BEFORE prose. Return JSON with acts array having exactly "
      "the same count/order as the approved outline. Every act: goal, new_events array, "
      "central_decision, irreversible_change, character_state_changes, ending_state, "
      "handoff_to_next. Never repeat an event, conflict or solution across acts. "
      "For business-acquisition stories, act 1 MUST show discovering the deal, WHY it costs US$1 "
      "or its approved symbolic amount, negotiation, actual acquisition and receiving keys BEFORE "
      "entering the business. Escalate setbacks, ingenious plans and consequences; no motivational filler. "
      "Resolve initial stakes in final act. Preserve approved story, title, numbers and user rules.")
    plan=model_json(client,system,spec)
    planned=plan.get("acts")
    if not isinstance(planned,list) or len(planned)!=len(acts):
        raise ValueError("El arquitecto narrativo no produjo un plan completo de actos.")
    for i,act in enumerate(planned):
        if not isinstance(act,dict) or not isinstance(act.get("new_events"),list) or not act.get("irreversible_change"):
            raise ValueError("El plan narrativo contiene actos sin acontecimientos nuevos.")
        act["approved_outline_act"]=acts[i]
    return plan

def local_warnings(script,*,first=False,acquisition=False,other_acts=()):
    warnings=[]
    lower=script.casefold()
    if first and acquisition:
        beginning=lower[:1800]
        transfer=("compr" ,"adquir","ofrec","entreg","llav","firm","propiet","purchase","bought","handed","keys")
        if sum(any(stem in beginning for stem in stems) for stems in (transfer[:4],transfer[4:]))<2:
            warnings.append("El comienzo no desarrolla la adquisición ni la entrega.")
    for phrase in BAD_PHRASES:
        if lower.count(phrase)>=3: warnings.append("Frase repetitiva: "+phrase)
    # Detect long copied passages between acts, not just exact single phrases.
    words=re.findall(r"\\w+",lower)
    if other_acts and len(words)>110:
        sequences={" ".join(words[i:i+18]) for i in range(0,len(words)-17,5)}
        for previous in other_acts[-3:]:
            prior=re.findall(r"\\w+",previous.casefold())
            older={" ".join(prior[i:i+18]) for i in range(0,len(prior)-17,5)}
            if len(sequences.intersection(older))>=3:
                warnings.append("Reutiliza pasajes largos de un acto anterior")
                break
    if len(script.split())<150: warnings.append("Acto demasiado corto")
    return warnings

def evaluate(client,*,plan,act_number,candidate,previous,brief,rules):
    payload={"act":plan["acts"][act_number],"previous_acts":previous[-3:],
             "candidate":candidate,"locked_story":plan.get("locked_story"),
             "brief":brief,"rules":rules}
    return model_json(client,
      "You are an independent ruthless fiction script editor. Return JSON with verdict 'pass' or "
      "'revise', issues array of actionable explanations, and revision_instructions string. "
      "Reject repeated plots and dialogue, skipping the purchase/key transfer in a business takeover "
      "first act, contradictory characters, scenes without meaningful events or consequences, "
      "unearned miracles, failure to meet the chosen POV/title, boring motivational speeches, "
      "and an act that does not actually accomplish its assigned irreversible story change. "
      "Fiction may be exaggerated; assess entertainment and internal story continuity, not realism. "
      "Only pass when the act works on its own and advances the larger plot.",
      payload)
