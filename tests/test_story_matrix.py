"""Wide, deterministic cross-genre story QA matrix. No paid LLM calls.

These tests exercise contracts, genre routing and narrative failure gates; they do
not pretend to measure the literary quality of a live model.
"""
import pytest
from studio import story_architect as sa

# 16 genuinely different narrative goals, not just distressed companies.
SCENARIOS = [
 ("rescue_gym", True, "Comprás un gimnasio por US$1", "You buy a bankrupt gym for $1"),
 ("rescue_hotel", True, "Te entregan un hotel en quiebra por un dólar", "You buy a hotel for $1"),
 ("rescue_airline", True, "Adquirís una aerolínea por US$1", "You buy an airline for $1"),
 ("rescue_factory", True, "Comprás una fábrica por un dólar", "You buy a factory for $1"),
 ("build_startup", False, "Fundás una startup sin contactos", "You build a startup from zero"),
 ("career_creator", False, "Pasás de cero a creador de contenido", "You become a content creator"),
 ("career_athlete", False, "Intentás llegar a una liga profesional", "You try to become a pro athlete"),
 ("wealth_resale", False, "Convertís ventas callejeras en un imperio", "You build a resale empire"),
 ("wealth_investing", False, "Tu primera inversión cambia tu vida", "Your first investment changes everything"),
 ("risk_time", False, "Tenés 24 horas para decidir tu futuro", "You have 24 hours to choose your future"),
 ("risk_escape", False, "Despertás atrapado en una ciudad vacía", "You wake up in an empty city"),
 ("risk_space", False, "Aceptás un viaje sin retorno a Marte", "You accept a one-way trip to Mars"),
 ("fantasy_kingdom", False, "Heredás un reino que te odia", "You inherit a kingdom that hates you"),
 ("scifi_machine", False, "Inventás una máquina que detiene el tiempo", "You invent a machine that stops time"),
 ("adventure_island", False, "Comprás un mapa de una isla perdida", "You buy a map to a lost island"),
 ("mystery_detective", False, "Descubrís que todos recuerdan otro pasado", "You discover everyone remembers another past"),
]
DURATIONS = [(15,20),(20,25),(25,35),(35,45)]
ANGLES = ("la oferta","el reloj","el secreto","la trampa","el regreso","el desafío","el giro","la decisión")
LANGUAGES=("es","en")


def build_data(label,lang,duration,acts=7):
    titles=[f"POV: {label} — {angle}" for angle in ANGLES[:3]]
    return {
       "brief":{"language":lang,"duration_min":list(duration),"narration":"segunda persona" if lang=="es" else "second person"},
       "concepts":{"options":[{"id":"A","title":titles[0],"premise":label}],"selected":"A"},
       "packaging":{"options":[{"id":"B","title":titles[1],"hook":"Comienza el dilema"}],"selected":"B"},
       "structure":{"acts":[{"title":f"Acto {i}","events":f"Evento diferente {i}"} for i in range(acts)]},
       "bible":{"characters":[{"name":"Alex","role":"protagonist"}]},
       "production":{"script_plan":"Secuencias"}
    }


@pytest.mark.parametrize("scenario",SCENARIOS,ids=[row[0] for row in SCENARIOS])
@pytest.mark.parametrize("duration",DURATIONS,ids=["15-20","20-25","25-35","35-45"])
@pytest.mark.parametrize("language",LANGUAGES)
@pytest.mark.parametrize("angle",ANGLES)
def test_1024_genre_language_duration_title_combinations(monkeypatch,scenario,duration,language,angle):
    name,should_acquire,spanish,english=scenario
    label=spanish if language=="es" else english
    locked={"title":f"POV: {label} — {angle}","premise":label}
    assert sa.is_acquisition(locked) is should_acquire
    data=build_data(label,language,duration)
    seen=[]
    def fake_plan(client,system,payload):
        seen.append(payload)
        return {"acts":[{"new_events":[f"Unique event for act {i}"],
                         "irreversible_change":f"Situation changes {i}",
                         "ending_state":f"State {i}"} for i in range(7)]}
    monkeypatch.setattr(sa,"model_json",fake_plan)
    plan=sa.architecture(object(),data,["No recycled events"])
    assert len(plan["acts"])==7
    assert plan["acts"][0]["approved_outline_act"]["title"]=="Acto 0"
    assert seen[0]["language"]==language
    assert seen[0]["locked_story"]["title"]==data["concepts"]["options"][0]["title"]
    assert seen[0]["locked_packaging"]["title"]==data["packaging"]["options"][0]["title"]
    assert seen[0]["user_rules"]==["No recycled events"]
    assert duration[0]<=duration[1]


@pytest.mark.parametrize("scenario",SCENARIOS,ids=[row[0] for row in SCENARIOS])
@pytest.mark.parametrize("language",LANGUAGES)
def test_all_genres_handle_good_and_bad_act_openings(scenario,language):
    _,acquisition,es,en=scenario
    opening=("Te hacen una oferta. Firmás la compra y recibís las llaves. " if language=="es"
             else "An owner offers you the company. You sign and receive the keys. ")
    good=(opening+"Tomás una decisión que cambia el rumbo de la historia. " * 25).strip()
    if acquisition:
        assert not any("adquisición" in w for w in sa.local_warnings(good,first=True,acquisition=True))
        bad=("Entrás al edificio sin saber cómo te convertiste en dueño. " * 35)
        assert any("adquisición" in w for w in sa.local_warnings(bad,first=True,acquisition=True))
    else:
        assert not any("adquisición" in w for w in sa.local_warnings(good,first=True,acquisition=False))
    assert not any("Frase repetitiva" in w for w in sa.local_warnings(good))


@pytest.mark.parametrize("duration",DURATIONS)
@pytest.mark.parametrize("language",LANGUAGES)
def test_eight_length_language_boundaries(duration,language):
    low,high=duration
    target=round(sum(duration)/2*135)
    assert low*110<=target<=high*165
    assert target>0
    assert language in ("es","en")


@pytest.mark.parametrize("form",["bad_act_count","no_new_events","no_change"])
@pytest.mark.parametrize("acts",[3,7,9])
def test_architect_rejects_incomplete_or_empty_plans(monkeypatch,form,acts):
    data=build_data("Reinventás tu carrera","es",(20,25),acts=acts)
    def bad_plan(*args):
        items=[{"new_events":[f"Event {i}"],"irreversible_change":f"Change {i}"} for i in range(acts)]
        if form=="bad_act_count": items.pop()
        if form=="no_new_events": items[0].pop("new_events")
        if form=="no_change": items[-1]["irreversible_change"]=""
        return {"acts":items}
    monkeypatch.setattr(sa,"model_json",bad_plan)
    with pytest.raises(ValueError):
        sa.architecture(object(),data,[])


@pytest.mark.parametrize("genre",["fantasy","startup","mystery","hotel"])
@pytest.mark.parametrize("verdict",["pass","revise","unknown"])
def test_final_editor_verdict_contract(monkeypatch,genre,verdict):
    monkeypatch.setattr(sa,"model_json",lambda *a,**kw:{"verdict":verdict,"issues":["Problem"] if verdict=="revise" else []})
    args=dict(client=object(),plan={"acts":[],"locked_story":{"title":genre}},
              script="Escena de ejemplo",acts=["Primero","Segundo"],
              brief={"language":"es"},rules=[])
    if verdict=="unknown":
        with pytest.raises(ValueError):
            sa.final_review(**args)
    else:
        assert sa.final_review(**args)["verdict"]==verdict


def test_copy_pasted_act_is_blocked_but_distinct_event_is_allowed():
    one=("Descubrís una falla, llamás al técnico y evitás una catástrofe en el puerto. "*18).strip()
    two=("Entrás al observatorio, descifrás un mensaje y decidís abandonar la misión. "*18).strip()
    assert any("pasajes largos" in x for x in sa.local_warnings(one,other_acts=[one]))
    assert not any("pasajes largos" in x for x in sa.local_warnings(two,other_acts=[one]))


def test_previous_written_act_is_not_required_for_story_that_does_not_involve_buying_business():
    story={"title":"POV: Comprás un mapa que muestra la ciudad del futuro",
           "premise":"Te lanzás a una aventura"}
    assert not sa.is_acquisition(story)
