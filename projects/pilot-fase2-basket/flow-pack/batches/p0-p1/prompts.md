# Check production — P0 P1

**24 prompts** · Each visual slot targets its own still (NNN.png). P0–P3 = generation order only, not permission to skip slots. Smart reuse activates only when the exact asset is missing.

Import each still as `NNN.png` matching `shot_id`.

## Index

- `007` · P0 · curiosity/opportunity · cubicle · era `ordinary_life` · fallback neighbours: —
- `009` · P1 · tension/progress · city · era `ordinary_life` · fallback neighbours: 025
- `010` · P0 · opportunity/commitment · city · era `pre_owner` · fallback neighbours: —
- `016` · P0 · opportunity/commitment · city · era `early_owner` · fallback neighbours: —
- `020` · P0 · hope/payoff · locker_room · era `early_owner` · fallback neighbours: —
- `021` · P0 · tension/progress · court · era `early_owner` · fallback neighbours: —
- `028` · P1 · pressure/crisis · city · era `ordinary_life` · fallback neighbours: 039
- `029` · P1 · progress/reward · city · era `ordinary_life` · fallback neighbours: 037
- `044` · P1 · failure/setback · city · era `struggling_owner` · fallback neighbours: 055
- `045` · P1 · tension/progress · city · era `struggling_owner` · fallback neighbours: 054
- `049` · P1 · tension/progress · city · era `struggling_owner` · fallback neighbours: 057
- `051` · P0 · glory/payoff · stands · era `struggling_owner` · fallback neighbours: —
- `053` · P0 · tension/progress · arena · era `struggling_owner` · fallback neighbours: —
- `059` · P1 · tension/progress · city · era `growing_owner` · fallback neighbours: 068, 077, 085
- `060` · P1 · tension/progress · city · era `growing_owner` · fallback neighbours: 069, 078
- `061` · P0 · tension/progress · new_apartment · era `growing_owner` · fallback neighbours: —
- `062` · P1 · tension/progress · city · era `growing_owner` · fallback neighbours: 070, 080
- `063` · P1 · progress/proof · city · era `growing_owner` · fallback neighbours: 084
- `064` · P1 · tension/progress · locker_room · era `growing_owner` · fallback neighbours: 073, 082
- `066` · P1 · tension/progress · city · era `growing_owner` · fallback neighbours: 074, 083
- `067` · P0 · happiness/reward · locker_room · era `growing_owner` · fallback neighbours: —
- `071` · P1 · tension/progress · city · era `growing_owner` · fallback neighbours: 081
- `075` · P1 · tension/progress · city · era `established_owner` · fallback neighbours: 089, 098
- `095` · P0 · reflection/ending · city · era `late_story` · fallback neighbours: —

## 007 — P0

- shot_id: `007`
- priority: `P0` (generation order)
- requires_own_still: `true`
- protagonist_era: `ordinary_life`
- location: `cubicle`
- mood: `curiosity`
- story_function: `opportunity`
- visual_bible_refs: protagonist_visual_bible, office_visual_bible
- reuse_slots (fallback only): —

```
2D cinematic illustrated storytelling, simple expressive protagonist, detailed environments, clean linework, cinematic lighting, strong depth, consistent proportions, mature not childish. Not anime, not clipart, not stock-photo look, not hyperrealistic random humans.
STYLE LOCK (Check): 2D cinematic illustrated storytelling: clean linework, expressive simple characters, detailed environments, strong lighting, readable silhouettes, consistent proportions. Not childish, not clipart, not stock, not anime, not inconsistent hyperrealism.
EXACT CHARACTER: Same Latino man throughout, ages 22 to 27: short dark brown hair, lean build, simple expressive face, readable eyes, clean linework, not a model, not a cartoon mascot. Age 22: cheap office collared shirt, dark trousers, worn backpack. After ownership: same face, slightly sharper haircut, dark green-and-gold team jacket over a casual shirt. Age 27: same person five years older, faint stubble, more tired eyes, same hairline and jaw. Never swap ethnicity, never redesign the face. Age now: 22. State: office employee, shared apartment, not yet owner. AGE 22 wardrobe only: cheap office collared shirt, dark trousers, worn backpack. No team jacket.
EXACT ACTION: holding a printed sale notice with a one-dollar figure, unreadably small type
EXACT ENVIRONMENT: Dull corporate cubicle farm: gray partitions, fluorescent lights, cheap LCD, a sad plant, plastic badge. Not WeWork, not glass startup HQ.
STORY TIME: AGE 22
CAMERA: insert of paper and hands, cubicle behind
COMPOSITION: 16:9 widescreen, strong foreground/midground/background, one clear subject Foreground: printed aviso. Background: gray cubicle.
LIGHTING: fluorescent + paper white
IMPORTANT OBJECTS: cheap printed sale notice / one-dollar figure on paper
CONTINUITY: Same protagonist face and hair. Same Halcones arena architecture when in stadium. AGE 22 wardrobe only: cheap office collared shirt, dark trousers, worn backpack. No team jacket. Do not invent a new man or a new building.
AVOID: anime, stock photo, photoreal random faces, clipart, collage, readable UI text, watermarks.
```

## 009 — P1

- shot_id: `009`
- priority: `P1` (generation order)
- requires_own_still: `true`
- protagonist_era: `ordinary_life`
- location: `city`
- mood: `tension`
- story_function: `progress`
- visual_bible_refs: protagonist_visual_bible
- reuse_slots (fallback only): 025

```
2D cinematic illustrated storytelling, simple expressive protagonist, detailed environments, clean linework, cinematic lighting, strong depth, consistent proportions, mature not childish. Not anime, not clipart, not stock-photo look, not hyperrealistic random humans.
STYLE LOCK (Check): 2D cinematic illustrated storytelling: clean linework, expressive simple characters, detailed environments, strong lighting, readable silhouettes, consistent proportions. Not childish, not clipart, not stock, not anime, not inconsistent hyperrealism.
EXACT CHARACTER: Same Latino man throughout, ages 22 to 27: short dark brown hair, lean build, simple expressive face, readable eyes, clean linework, not a model, not a cartoon mascot. Age 22: cheap office collared shirt, dark trousers, worn backpack. After ownership: same face, slightly sharper haircut, dark green-and-gold team jacket over a casual shirt. Age 27: same person five years older, faint stubble, more tired eyes, same hairline and jaw. Never swap ethnicity, never redesign the face. Age now: 22. State: office, shared apartment, not yet owner. AGE 22 wardrobe only: cheap office collared shirt, dark trousers, worn backpack. No team jacket.
EXACT ACTION: En la carpeta: proveedores impagos, un crédito viejo, un techo que gotea sobre la tribuna este
EXACT ENVIRONMENT: Night streets of a mid-size fictional city near the municipal arena.
STORY TIME: AGE 22
CAMERA: close-up
COMPOSITION: 16:9 widescreen, strong foreground/midground/background, one clear subject
LIGHTING: cinematic motivated light, strong depth
IMPORTANT OBJECTS: story-specific props only
CONTINUITY: Same protagonist face and hair. Same Halcones arena architecture when in stadium. AGE 22 wardrobe only: cheap office collared shirt, dark trousers, worn backpack. No team jacket. Do not invent a new man or a new building.
AVOID: anime, stock photo, photoreal random faces, clipart, collage, readable UI text, watermarks.
```

## 010 — P0

- shot_id: `010`
- priority: `P0` (generation order)
- requires_own_still: `true`
- protagonist_era: `pre_owner`
- location: `city`
- mood: `opportunity`
- story_function: `commitment`
- visual_bible_refs: protagonist_visual_bible
- reuse_slots (fallback only): —

```
2D cinematic illustrated storytelling, simple expressive protagonist, detailed environments, clean linework, cinematic lighting, strong depth, consistent proportions, mature not childish. Not anime, not clipart, not stock-photo look, not hyperrealistic random humans.
STYLE LOCK (Check): 2D cinematic illustrated storytelling: clean linework, expressive simple characters, detailed environments, strong lighting, readable silhouettes, consistent proportions. Not childish, not clipart, not stock, not anime, not inconsistent hyperrealism.
EXACT CHARACTER: Same Latino man throughout, ages 22 to 27: short dark brown hair, lean build, simple expressive face, readable eyes, clean linework, not a model, not a cartoon mascot. Age 22: cheap office collared shirt, dark trousers, worn backpack. After ownership: same face, slightly sharper haircut, dark green-and-gold team jacket over a casual shirt. Age 27: same person five years older, faint stubble, more tired eyes, same hairline and jaw. Never swap ethnicity, never redesign the face. Age now: 22. State: office, shared apartment, not yet owner. AGE 22 wardrobe only: cheap office collared shirt, dark trousers, worn backpack. No team jacket.
EXACT ACTION: in this story world: El precio de compra es un dólar.
EXACT ENVIRONMENT: Night streets of a mid-size fictional city near the municipal arena.
STORY TIME: AGE 22
CAMERA: low angle close
COMPOSITION: 16:9 widescreen, strong foreground/midground/background, one clear subject Foreground: a distinct near-plane object for this beat. Background: deep environment, different depth than the previous still.
LIGHTING: cinematic motivated light, strong depth
IMPORTANT OBJECTS: cheap printed sale notice / one-dollar figure on paper
CONTINUITY: Same protagonist face and hair. Same Halcones arena architecture when in stadium. AGE 22 wardrobe only: cheap office collared shirt, dark trousers, worn backpack. No team jacket. Do not invent a new man or a new building.
AVOID: anime, stock photo, photoreal random faces, clipart, collage, readable UI text, watermarks.
```

## 016 — P0

- shot_id: `016`
- priority: `P0` (generation order)
- requires_own_still: `true`
- protagonist_era: `early_owner`
- location: `city`
- mood: `opportunity`
- story_function: `commitment`
- visual_bible_refs: protagonist_visual_bible
- reuse_slots (fallback only): —

```
2D cinematic illustrated storytelling, simple expressive protagonist, detailed environments, clean linework, cinematic lighting, strong depth, consistent proportions, mature not childish. Not anime, not clipart, not stock-photo look, not hyperrealistic random humans.
STYLE LOCK (Check): 2D cinematic illustrated storytelling: clean linework, expressive simple characters, detailed environments, strong lighting, readable silhouettes, consistent proportions. Not childish, not clipart, not stock, not anime, not inconsistent hyperrealism.
EXACT CHARACTER: Same Latino man throughout, ages 22 to 27: short dark brown hair, lean build, simple expressive face, readable eyes, clean linework, not a model, not a cartoon mascot. Age 22: cheap office collared shirt, dark trousers, worn backpack. After ownership: same face, slightly sharper haircut, dark green-and-gold team jacket over a casual shirt. Age 27: same person five years older, faint stubble, more tired eyes, same hairline and jaw. Never swap ethnicity, never redesign the face. Age now: 22. State: new 51% owner entering the arena. Wardrobe matches age/state from the protagonist bible.
EXACT ACTION: Preguntan si sabes de básquet
EXACT ENVIRONMENT: Night streets of a mid-size fictional city near the municipal arena.
STORY TIME: AGE 22 · season 1
CAMERA: POV first person
COMPOSITION: 16:9 widescreen, strong foreground/midground/background, one clear subject
LIGHTING: cinematic motivated light, strong depth
IMPORTANT OBJECTS: story-specific props only
CONTINUITY: Same protagonist face and hair. Same Halcones arena architecture when in stadium. Wardrobe matches age/state from the protagonist bible. Do not invent a new man or a new building.
AVOID: anime, stock photo, photoreal random faces, clipart, collage, readable UI text, watermarks.
```

## 020 — P0

- shot_id: `020`
- priority: `P0` (generation order)
- requires_own_still: `true`
- protagonist_era: `early_owner`
- location: `locker_room`
- mood: `hope`
- story_function: `payoff`
- visual_bible_refs: protagonist_visual_bible, arena_visual_bible, team_visual_bible, utilero_visual_bible
- reuse_slots (fallback only): —

```
2D cinematic illustrated storytelling, simple expressive protagonist, detailed environments, clean linework, cinematic lighting, strong depth, consistent proportions, mature not childish. Not anime, not clipart, not stock-photo look, not hyperrealistic random humans.
STYLE LOCK (Check): 2D cinematic illustrated storytelling: clean linework, expressive simple characters, detailed environments, strong lighting, readable silhouettes, consistent proportions. Not childish, not clipart, not stock, not anime, not inconsistent hyperrealism.
EXACT CHARACTER: Same Latino man throughout, ages 22 to 27: short dark brown hair, lean build, simple expressive face, readable eyes, clean linework, not a model, not a cartoon mascot. Age 22: cheap office collared shirt, dark trousers, worn backpack. After ownership: same face, slightly sharper haircut, dark green-and-gold team jacket over a casual shirt. Age 27: same person five years older, faint stubble, more tired eyes, same hairline and jaw. Never swap ethnicity, never redesign the face. Age now: 22. State: new 51% owner entering the arena. Wardrobe matches age/state from the protagonist bible.
EXACT ACTION: equipment manager in the doorway with keys; protagonist just inside. Beat: in the Halcones locker room / tunnel threshold: Te entrega un manojo de llaves. Hace una pausa. Las llaves pesan más que el contrato.
EXACT ENVIRONMENT: Halcones locker room. Los Halcones de la Ciudad: dark green and copper-gold, hawk mark on jerseys. Worn kits early, cleaner later. Same uniform identity across years.
STORY TIME: AGE 22 · season 1
CAMERA: from inside looking at the doorway
COMPOSITION: 16:9 widescreen, strong foreground/midground/background, one clear subject Foreground: green locker edge. Background: tunnel light.
LIGHTING: cinematic motivated light, strong depth
IMPORTANT OBJECTS: ring of old arena keys
CONTINUITY: Same protagonist face and hair. Same Halcones arena architecture when in stadium. Wardrobe matches age/state from the protagonist bible. Do not invent a new man or a new building.
AVOID: anime, stock photo, photoreal random faces, clipart, collage, readable UI text, watermarks.
```

## 021 — P0

- shot_id: `021`
- priority: `P0` (generation order)
- requires_own_still: `true`
- protagonist_era: `early_owner`
- location: `court`
- mood: `tension`
- story_function: `progress`
- visual_bible_refs: protagonist_visual_bible, arena_visual_bible, team_visual_bible
- reuse_slots (fallback only): —

```
2D cinematic illustrated storytelling, simple expressive protagonist, detailed environments, clean linework, cinematic lighting, strong depth, consistent proportions, mature not childish. Not anime, not clipart, not stock-photo look, not hyperrealistic random humans.
STYLE LOCK (Check): 2D cinematic illustrated storytelling: clean linework, expressive simple characters, detailed environments, strong lighting, readable silhouettes, consistent proportions. Not childish, not clipart, not stock, not anime, not inconsistent hyperrealism.
EXACT CHARACTER: Same Latino man throughout, ages 22 to 27: short dark brown hair, lean build, simple expressive face, readable eyes, clean linework, not a model, not a cartoon mascot. Age 22: cheap office collared shirt, dark trousers, worn backpack. After ownership: same face, slightly sharper haircut, dark green-and-gold team jacket over a casual shirt. Age 27: same person five years older, faint stubble, more tired eyes, same hairline and jaw. Never swap ethnicity, never redesign the face. Age now: 22. State: office employee, shared apartment. Wardrobe matches age/state from the protagonist bible.
EXACT ACTION: one hand on a cracked seat; hawk mark nearby. Beat: in the same municipal Halcones arena: No contestas enseguida. El túnel tiene una gotera. Al fondo, la cancha vacía.
EXACT ENVIRONMENT: Run-down municipal Halcones arena: empty or sparse stands (~620 early, later filling), yellowed lights, peeling paint. SAME building as later sold-out years. Same municipal basketball arena throughout: brick exterior, faded 'Halcones' sign, 4800-seat bowl, same roof shape, same tunnel to the court, same floor orientation. Early: peeling paint, empty stands, yellowed lights, water stains, old wood floor. Later: same architecture, better lighting, fresh paint, packed then sold-out stands. The building evolves; it does not become a different NBA arena. Seat-level detail.
STORY TIME: AGE 22 · season 1
CAMERA: close-up of a hand on a peeling seat
COMPOSITION: 16:9 widescreen, strong foreground/midground/background, one clear subject Foreground: cracked green seat. Background: soft stands.
LIGHTING: cinematic motivated light, strong depth
IMPORTANT OBJECTS: Halcones hawk mark
CONTINUITY: Same protagonist face and hair. Same Halcones arena architecture when in stadium. Wardrobe matches age/state from the protagonist bible. Do not invent a new man or a new building.
AVOID: anime, stock photo, photoreal random faces, clipart, collage, readable UI text, watermarks.
```

## 028 — P1

- shot_id: `028`
- priority: `P1` (generation order)
- requires_own_still: `true`
- protagonist_era: `ordinary_life`
- location: `city`
- mood: `pressure`
- story_function: `crisis`
- visual_bible_refs: protagonist_visual_bible
- reuse_slots (fallback only): 039

```
2D cinematic illustrated storytelling, simple expressive protagonist, detailed environments, clean linework, cinematic lighting, strong depth, consistent proportions, mature not childish. Not anime, not clipart, not stock-photo look, not hyperrealistic random humans.
STYLE LOCK (Check): 2D cinematic illustrated storytelling: clean linework, expressive simple characters, detailed environments, strong lighting, readable silhouettes, consistent proportions. Not childish, not clipart, not stock, not anime, not inconsistent hyperrealism.
EXACT CHARACTER: Same Latino man throughout, ages 22 to 27: short dark brown hair, lean build, simple expressive face, readable eyes, clean linework, not a model, not a cartoon mascot. Age 22: cheap office collared shirt, dark trousers, worn backpack. After ownership: same face, slightly sharper haircut, dark green-and-gold team jacket over a casual shirt. Age 27: same person five years older, faint stubble, more tired eyes, same hairline and jaw. Never swap ethnicity, never redesign the face. Age now: 22. State: office employee, shared apartment. Wardrobe matches age/state from the protagonist bible.
EXACT ACTION: in this story world: Un viernes, después de tres derrotas seguidas, miras la caja del equipo y la cuota de la deuda en la misma pantalla.
EXACT ENVIRONMENT: Night streets of a mid-size fictional city near the municipal arena.
STORY TIME: AGE 22 · season 1
CAMERA: side tracking
COMPOSITION: 16:9 widescreen, strong foreground/midground/background, one clear subject Foreground: a distinct near-plane object for this beat. Background: deep environment, different depth than the previous still.
LIGHTING: cinematic motivated light, strong depth
IMPORTANT OBJECTS: story-specific props only
CONTINUITY: Same protagonist face and hair. Same Halcones arena architecture when in stadium. Wardrobe matches age/state from the protagonist bible. Do not invent a new man or a new building.
AVOID: anime, stock photo, photoreal random faces, clipart, collage, readable UI text, watermarks.
```

## 029 — P1

- shot_id: `029`
- priority: `P1` (generation order)
- requires_own_still: `true`
- protagonist_era: `ordinary_life`
- location: `city`
- mood: `progress`
- story_function: `reward`
- visual_bible_refs: protagonist_visual_bible
- reuse_slots (fallback only): 037

```
2D cinematic illustrated storytelling, simple expressive protagonist, detailed environments, clean linework, cinematic lighting, strong depth, consistent proportions, mature not childish. Not anime, not clipart, not stock-photo look, not hyperrealistic random humans.
STYLE LOCK (Check): 2D cinematic illustrated storytelling: clean linework, expressive simple characters, detailed environments, strong lighting, readable silhouettes, consistent proportions. Not childish, not clipart, not stock, not anime, not inconsistent hyperrealism.
EXACT CHARACTER: Same Latino man throughout, ages 22 to 27: short dark brown hair, lean build, simple expressive face, readable eyes, clean linework, not a model, not a cartoon mascot. Age 22: cheap office collared shirt, dark trousers, worn backpack. After ownership: same face, slightly sharper haircut, dark green-and-gold team jacket over a casual shirt. Age 27: same person five years older, faint stubble, more tired eyes, same hairline and jaw. Never swap ethnicity, never redesign the face. Age now: 22. State: first-year owner in playoffs. Wardrobe matches age/state from the protagonist bible.
EXACT ACTION: in this story world: Inyectas cinco mil dólares tuyos. Los últimos cinco mil que te quedaban de la compra.
EXACT ENVIRONMENT: Night streets of a mid-size fictional city near the municipal arena.
STORY TIME: AGE 22 · season 1
CAMERA: high angle wide
COMPOSITION: 16:9 widescreen, strong foreground/midground/background, one clear subject Foreground: a distinct near-plane object for this beat. Background: deep environment, different depth than the previous still.
LIGHTING: cinematic motivated light, strong depth
IMPORTANT OBJECTS: story-specific props only
CONTINUITY: Same protagonist face and hair. Same Halcones arena architecture when in stadium. Wardrobe matches age/state from the protagonist bible. Do not invent a new man or a new building.
AVOID: anime, stock photo, photoreal random faces, clipart, collage, readable UI text, watermarks.
```

## 044 — P1

- shot_id: `044`
- priority: `P1` (generation order)
- requires_own_still: `true`
- protagonist_era: `struggling_owner`
- location: `city`
- mood: `failure`
- story_function: `setback`
- visual_bible_refs: protagonist_visual_bible
- reuse_slots (fallback only): 055

```
2D cinematic illustrated storytelling, simple expressive protagonist, detailed environments, clean linework, cinematic lighting, strong depth, consistent proportions, mature not childish. Not anime, not clipart, not stock-photo look, not hyperrealistic random humans.
STYLE LOCK (Check): 2D cinematic illustrated storytelling: clean linework, expressive simple characters, detailed environments, strong lighting, readable silhouettes, consistent proportions. Not childish, not clipart, not stock, not anime, not inconsistent hyperrealism.
EXACT CHARACTER: Same Latino man throughout, ages 22 to 27: short dark brown hair, lean build, simple expressive face, readable eyes, clean linework, not a model, not a cartoon mascot. Age 22: cheap office collared shirt, dark trousers, worn backpack. After ownership: same face, slightly sharper haircut, dark green-and-gold team jacket over a casual shirt. Age 27: same person five years older, faint stubble, more tired eyes, same hairline and jaw. Never swap ethnicity, never redesign the face. Age now: 23. State: quitting the office job. Wardrobe matches age/state from the protagonist bible.
EXACT ACTION: Temporada 2: otro 14-18
EXACT ENVIRONMENT: Night streets of a mid-size fictional city near the municipal arena.
STORY TIME: AGE 23 · season 3
CAMERA: close-up
COMPOSITION: 16:9 widescreen, strong foreground/midground/background, one clear subject
LIGHTING: cinematic motivated light, strong depth
IMPORTANT OBJECTS: story-specific props only
CONTINUITY: Same protagonist face and hair. Same Halcones arena architecture when in stadium. Wardrobe matches age/state from the protagonist bible. Do not invent a new man or a new building.
AVOID: anime, stock photo, photoreal random faces, clipart, collage, readable UI text, watermarks.
```

## 045 — P1

- shot_id: `045`
- priority: `P1` (generation order)
- requires_own_still: `true`
- protagonist_era: `struggling_owner`
- location: `city`
- mood: `tension`
- story_function: `progress`
- visual_bible_refs: protagonist_visual_bible
- reuse_slots (fallback only): 054

```
2D cinematic illustrated storytelling, simple expressive protagonist, detailed environments, clean linework, cinematic lighting, strong depth, consistent proportions, mature not childish. Not anime, not clipart, not stock-photo look, not hyperrealistic random humans.
STYLE LOCK (Check): 2D cinematic illustrated storytelling: clean linework, expressive simple characters, detailed environments, strong lighting, readable silhouettes, consistent proportions. Not childish, not clipart, not stock, not anime, not inconsistent hyperrealism.
EXACT CHARACTER: Same Latino man throughout, ages 22 to 27: short dark brown hair, lean build, simple expressive face, readable eyes, clean linework, not a model, not a cartoon mascot. Age 22: cheap office collared shirt, dark trousers, worn backpack. After ownership: same face, slightly sharper haircut, dark green-and-gold team jacket over a casual shirt. Age 27: same person five years older, faint stubble, more tired eyes, same hairline and jaw. Never swap ethnicity, never redesign the face. Age now: 23. State: quitting the office job. Wardrobe matches age/state from the protagonist bible.
EXACT ACTION: in this story world: El público, en cambio, no se va. Cuatro mil doscientas sesenta y seis de promedio. El club vale más de veinte millones s
EXACT ENVIRONMENT: Night streets of a mid-size fictional city near the municipal arena.
STORY TIME: AGE 23 · season 3
CAMERA: doorway frame
COMPOSITION: 16:9 widescreen, strong foreground/midground/background, one clear subject Foreground: a distinct near-plane object for this beat. Background: deep environment, different depth than the previous still.
LIGHTING: cinematic motivated light, strong depth
IMPORTANT OBJECTS: story-specific props only
CONTINUITY: Same protagonist face and hair. Same Halcones arena architecture when in stadium. Wardrobe matches age/state from the protagonist bible. Do not invent a new man or a new building.
AVOID: anime, stock photo, photoreal random faces, clipart, collage, readable UI text, watermarks.
```

## 049 — P1

- shot_id: `049`
- priority: `P1` (generation order)
- requires_own_still: `true`
- protagonist_era: `struggling_owner`
- location: `city`
- mood: `tension`
- story_function: `progress`
- visual_bible_refs: protagonist_visual_bible
- reuse_slots (fallback only): 057

```
2D cinematic illustrated storytelling, simple expressive protagonist, detailed environments, clean linework, cinematic lighting, strong depth, consistent proportions, mature not childish. Not anime, not clipart, not stock-photo look, not hyperrealistic random humans.
STYLE LOCK (Check): 2D cinematic illustrated storytelling: clean linework, expressive simple characters, detailed environments, strong lighting, readable silhouettes, consistent proportions. Not childish, not clipart, not stock, not anime, not inconsistent hyperrealism.
EXACT CHARACTER: Same Latino man throughout, ages 22 to 27: short dark brown hair, lean build, simple expressive face, readable eyes, clean linework, not a model, not a cartoon mascot. Age 22: cheap office collared shirt, dark trousers, worn backpack. After ownership: same face, slightly sharper haircut, dark green-and-gold team jacket over a casual shirt. Age 27: same person five years older, faint stubble, more tired eyes, same hairline and jaw. Never swap ethnicity, never redesign the face. Age now: 23. State: quitting the office job. Wardrobe matches age/state from the protagonist bible.
EXACT ACTION: in this story world: Temporada 3.
EXACT ENVIRONMENT: Night streets of a mid-size fictional city near the municipal arena.
STORY TIME: AGE 23 · season 3
CAMERA: side tracking
COMPOSITION: 16:9 widescreen, strong foreground/midground/background, one clear subject Foreground: a distinct near-plane object for this beat. Background: deep environment, different depth than the previous still.
LIGHTING: cinematic motivated light, strong depth
IMPORTANT OBJECTS: story-specific props only
CONTINUITY: Same protagonist face and hair. Same Halcones arena architecture when in stadium. Wardrobe matches age/state from the protagonist bible. Do not invent a new man or a new building.
AVOID: anime, stock photo, photoreal random faces, clipart, collage, readable UI text, watermarks.
```

## 051 — P0

- shot_id: `051`
- priority: `P0` (generation order)
- requires_own_still: `true`
- protagonist_era: `struggling_owner`
- location: `stands`
- mood: `glory`
- story_function: `payoff`
- visual_bible_refs: protagonist_visual_bible, arena_visual_bible, team_visual_bible
- reuse_slots (fallback only): —

```
2D cinematic illustrated storytelling, simple expressive protagonist, detailed environments, clean linework, cinematic lighting, strong depth, consistent proportions, mature not childish. Not anime, not clipart, not stock-photo look, not hyperrealistic random humans.
STYLE LOCK (Check): 2D cinematic illustrated storytelling: clean linework, expressive simple characters, detailed environments, strong lighting, readable silhouettes, consistent proportions. Not childish, not clipart, not stock, not anime, not inconsistent hyperrealism.
EXACT CHARACTER: Same Latino man throughout, ages 22 to 27: short dark brown hair, lean build, simple expressive face, readable eyes, clean linework, not a model, not a cartoon mascot. Age 22: cheap office collared shirt, dark trousers, worn backpack. After ownership: same face, slightly sharper haircut, dark green-and-gold team jacket over a casual shirt. Age 27: same person five years older, faint stubble, more tired eyes, same hairline and jaw. Never swap ethnicity, never redesign the face. Age now: 23. State: quitting the office job. Wardrobe matches age/state from the protagonist bible.
EXACT ACTION: hands on the dark tunnel rail, looking toward the court, body off-center. Beat: in the same municipal Halcones arena: Sold out.
EXACT ENVIRONMENT: Same Halcones municipal arena now packed toward 4800 capacity, stronger lights, same architecture. Same municipal basketball arena throughout: brick exterior, faded 'Halcones' sign, 4800-seat bowl, same roof shape, same tunnel to the court, same floor orientation. Early: peeling paint, empty stands, yellowed lights, water stains, old wood floor. Later: same architecture, better lighting, fresh paint, packed then sold-out stands. The building evolves; it does not become a different NBA arena. Tunnel locked; court in depth.
STORY TIME: AGE 23 · season 3
CAMERA: behind him in the tunnel mouth looking out
COMPOSITION: 16:9 widescreen, strong foreground/midground/background, one clear subject Foreground: tunnel concrete and a drip stain. Background: court lights, same floor orientation.
LIGHTING: harder game lights, crowd glow
IMPORTANT OBJECTS: Halcones hawk mark
CONTINUITY: Same protagonist face and hair. Same Halcones arena architecture when in stadium. Wardrobe matches age/state from the protagonist bible. Do not invent a new man or a new building.
AVOID: anime, stock photo, photoreal random faces, clipart, collage, readable UI text, watermarks.
```

## 053 — P0

- shot_id: `053`
- priority: `P0` (generation order)
- requires_own_still: `true`
- protagonist_era: `struggling_owner`
- location: `arena`
- mood: `tension`
- story_function: `progress`
- visual_bible_refs: protagonist_visual_bible, arena_visual_bible, team_visual_bible
- reuse_slots (fallback only): —

```
2D cinematic illustrated storytelling, simple expressive protagonist, detailed environments, clean linework, cinematic lighting, strong depth, consistent proportions, mature not childish. Not anime, not clipart, not stock-photo look, not hyperrealistic random humans.
STYLE LOCK (Check): 2D cinematic illustrated storytelling: clean linework, expressive simple characters, detailed environments, strong lighting, readable silhouettes, consistent proportions. Not childish, not clipart, not stock, not anime, not inconsistent hyperrealism.
EXACT CHARACTER: Same Latino man throughout, ages 22 to 27: short dark brown hair, lean build, simple expressive face, readable eyes, clean linework, not a model, not a cartoon mascot. Age 22: cheap office collared shirt, dark trousers, worn backpack. After ownership: same face, slightly sharper haircut, dark green-and-gold team jacket over a casual shirt. Age 27: same person five years older, faint stubble, more tired eyes, same hairline and jaw. Never swap ethnicity, never redesign the face. Age now: 23. State: quitting the office job. Wardrobe matches age/state from the protagonist bible.
EXACT ACTION: one hand on a cracked seat; hawk mark nearby. Beat: in the same municipal Halcones arena: En la mochila, de vuelta, no llevas notebook de la empresa. Llevas un llavero del estadio.
EXACT ENVIRONMENT: Same Halcones municipal arena now packed toward 4800 capacity, stronger lights, same architecture. Same municipal basketball arena throughout: brick exterior, faded 'Halcones' sign, 4800-seat bowl, same roof shape, same tunnel to the court, same floor orientation. Early: peeling paint, empty stands, yellowed lights, water stains, old wood floor. Later: same architecture, better lighting, fresh paint, packed then sold-out stands. The building evolves; it does not become a different NBA arena. Seat-level detail.
STORY TIME: AGE 23 · season 3
CAMERA: close-up of a hand on a peeling seat
COMPOSITION: 16:9 widescreen, strong foreground/midground/background, one clear subject Foreground: cracked green seat. Background: soft stands.
LIGHTING: cinematic motivated light, strong depth
IMPORTANT OBJECTS: Halcones hawk mark
CONTINUITY: Same protagonist face and hair. Same Halcones arena architecture when in stadium. Wardrobe matches age/state from the protagonist bible. Do not invent a new man or a new building.
AVOID: anime, stock photo, photoreal random faces, clipart, collage, readable UI text, watermarks.
```

## 059 — P1

- shot_id: `059`
- priority: `P1` (generation order)
- requires_own_still: `true`
- protagonist_era: `growing_owner`
- location: `city`
- mood: `tension`
- story_function: `progress`
- visual_bible_refs: protagonist_visual_bible
- reuse_slots (fallback only): 068, 077, 085

```
2D cinematic illustrated storytelling, simple expressive protagonist, detailed environments, clean linework, cinematic lighting, strong depth, consistent proportions, mature not childish. Not anime, not clipart, not stock-photo look, not hyperrealistic random humans.
STYLE LOCK (Check): 2D cinematic illustrated storytelling: clean linework, expressive simple characters, detailed environments, strong lighting, readable silhouettes, consistent proportions. Not childish, not clipart, not stock, not anime, not inconsistent hyperrealism.
EXACT CHARACTER: Same Latino man throughout, ages 22 to 27: short dark brown hair, lean build, simple expressive face, readable eyes, clean linework, not a model, not a cartoon mascot. Age 22: cheap office collared shirt, dark trousers, worn backpack. After ownership: same face, slightly sharper haircut, dark green-and-gold team jacket over a casual shirt. Age 27: same person five years older, faint stubble, more tired eyes, same hairline and jaw. Never swap ethnicity, never redesign the face. Age now: 25. State: owner moving into own apartment. Wardrobe matches age/state from the protagonist bible.
EXACT ACTION: a specific insert matching this story beat, protagonist recognizable if present
EXACT ENVIRONMENT: Night streets of a mid-size fictional city near the municipal arena.
STORY TIME: AGE 25 · season 4
CAMERA: insert detail
COMPOSITION: 16:9 widescreen, strong foreground/midground/background, one clear subject Foreground: a distinct near-plane object for this beat. Background: deep environment, different depth than the previous still.
LIGHTING: cinematic motivated light, strong depth
IMPORTANT OBJECTS: story-specific props only
CONTINUITY: Same protagonist face and hair. Same Halcones arena architecture when in stadium. Wardrobe matches age/state from the protagonist bible. Do not invent a new man or a new building.
AVOID: anime, stock photo, photoreal random faces, clipart, collage, readable UI text, watermarks.
```

## 060 — P1

- shot_id: `060`
- priority: `P1` (generation order)
- requires_own_still: `true`
- protagonist_era: `growing_owner`
- location: `city`
- mood: `tension`
- story_function: `progress`
- visual_bible_refs: protagonist_visual_bible
- reuse_slots (fallback only): 069, 078

```
2D cinematic illustrated storytelling, simple expressive protagonist, detailed environments, clean linework, cinematic lighting, strong depth, consistent proportions, mature not childish. Not anime, not clipart, not stock-photo look, not hyperrealistic random humans.
STYLE LOCK (Check): 2D cinematic illustrated storytelling: clean linework, expressive simple characters, detailed environments, strong lighting, readable silhouettes, consistent proportions. Not childish, not clipart, not stock, not anime, not inconsistent hyperrealism.
EXACT CHARACTER: Same Latino man throughout, ages 22 to 27: short dark brown hair, lean build, simple expressive face, readable eyes, clean linework, not a model, not a cartoon mascot. Age 22: cheap office collared shirt, dark trousers, worn backpack. After ownership: same face, slightly sharper haircut, dark green-and-gold team jacket over a casual shirt. Age 27: same person five years older, faint stubble, more tired eyes, same hairline and jaw. Never swap ethnicity, never redesign the face. Age now: 25. State: owner moving into own apartment. Wardrobe matches age/state from the protagonist bible.
EXACT ACTION: in this story world: Tienes veinticinco.
EXACT ENVIRONMENT: Night streets of a mid-size fictional city near the municipal arena.
STORY TIME: AGE 25 · season 4
CAMERA: doorway frame
COMPOSITION: 16:9 widescreen, strong foreground/midground/background, one clear subject Foreground: a distinct near-plane object for this beat. Background: deep environment, different depth than the previous still.
LIGHTING: cinematic motivated light, strong depth
IMPORTANT OBJECTS: story-specific props only
CONTINUITY: Same protagonist face and hair. Same Halcones arena architecture when in stadium. Wardrobe matches age/state from the protagonist bible. Do not invent a new man or a new building.
AVOID: anime, stock photo, photoreal random faces, clipart, collage, readable UI text, watermarks.
```

## 061 — P0

- shot_id: `061`
- priority: `P0` (generation order)
- requires_own_still: `true`
- protagonist_era: `growing_owner`
- location: `new_apartment`
- mood: `tension`
- story_function: `progress`
- visual_bible_refs: protagonist_visual_bible, new_apartment_visual_bible
- reuse_slots (fallback only): —

```
2D cinematic illustrated storytelling, simple expressive protagonist, detailed environments, clean linework, cinematic lighting, strong depth, consistent proportions, mature not childish. Not anime, not clipart, not stock-photo look, not hyperrealistic random humans.
STYLE LOCK (Check): 2D cinematic illustrated storytelling: clean linework, expressive simple characters, detailed environments, strong lighting, readable silhouettes, consistent proportions. Not childish, not clipart, not stock, not anime, not inconsistent hyperrealism.
EXACT CHARACTER: Same Latino man throughout, ages 22 to 27: short dark brown hair, lean build, simple expressive face, readable eyes, clean linework, not a model, not a cartoon mascot. Age 22: cheap office collared shirt, dark trousers, worn backpack. After ownership: same face, slightly sharper haircut, dark green-and-gold team jacket over a casual shirt. Age 27: same person five years older, faint stubble, more tired eyes, same hairline and jaw. Never swap ethnicity, never redesign the face. Age now: 25. State: owner moving into own apartment. Wardrobe matches age/state from the protagonist bible.
EXACT ACTION: El nuevo queda a cuatro cuadras de la arena
EXACT ENVIRONMENT: Simple one-bedroom of his own, four blocks from the arena: moving boxes, a window that can see arena lights at night. Modest upgrade, not a penthouse.
STORY TIME: AGE 25 · season 4
CAMERA: POV first person
COMPOSITION: 16:9 widescreen, strong foreground/midground/background, one clear subject
LIGHTING: cinematic motivated light, strong depth
IMPORTANT OBJECTS: moving boxes
CONTINUITY: Same protagonist face and hair. Same Halcones arena architecture when in stadium. Wardrobe matches age/state from the protagonist bible. Do not invent a new man or a new building.
AVOID: anime, stock photo, photoreal random faces, clipart, collage, readable UI text, watermarks.
```

## 062 — P1

- shot_id: `062`
- priority: `P1` (generation order)
- requires_own_still: `true`
- protagonist_era: `growing_owner`
- location: `city`
- mood: `tension`
- story_function: `progress`
- visual_bible_refs: protagonist_visual_bible
- reuse_slots (fallback only): 070, 080

```
2D cinematic illustrated storytelling, simple expressive protagonist, detailed environments, clean linework, cinematic lighting, strong depth, consistent proportions, mature not childish. Not anime, not clipart, not stock-photo look, not hyperrealistic random humans.
STYLE LOCK (Check): 2D cinematic illustrated storytelling: clean linework, expressive simple characters, detailed environments, strong lighting, readable silhouettes, consistent proportions. Not childish, not clipart, not stock, not anime, not inconsistent hyperrealism.
EXACT CHARACTER: Same Latino man throughout, ages 22 to 27: short dark brown hair, lean build, simple expressive face, readable eyes, clean linework, not a model, not a cartoon mascot. Age 22: cheap office collared shirt, dark trousers, worn backpack. After ownership: same face, slightly sharper haircut, dark green-and-gold team jacket over a casual shirt. Age 27: same person five years older, faint stubble, more tired eyes, same hairline and jaw. Never swap ethnicity, never redesign the face. Age now: 25. State: owner moving into own apartment. Wardrobe matches age/state from the protagonist bible.
EXACT ACTION: No es un penthouse
EXACT ENVIRONMENT: Night streets of a mid-size fictional city near the municipal arena.
STORY TIME: AGE 25 · season 4
CAMERA: over the shoulder
COMPOSITION: 16:9 widescreen, strong foreground/midground/background, one clear subject
LIGHTING: cinematic motivated light, strong depth
IMPORTANT OBJECTS: story-specific props only
CONTINUITY: Same protagonist face and hair. Same Halcones arena architecture when in stadium. Wardrobe matches age/state from the protagonist bible. Do not invent a new man or a new building.
AVOID: anime, stock photo, photoreal random faces, clipart, collage, readable UI text, watermarks.
```

## 063 — P1

- shot_id: `063`
- priority: `P1` (generation order)
- requires_own_still: `true`
- protagonist_era: `growing_owner`
- location: `city`
- mood: `progress`
- story_function: `proof`
- visual_bible_refs: protagonist_visual_bible
- reuse_slots (fallback only): 084

```
2D cinematic illustrated storytelling, simple expressive protagonist, detailed environments, clean linework, cinematic lighting, strong depth, consistent proportions, mature not childish. Not anime, not clipart, not stock-photo look, not hyperrealistic random humans.
STYLE LOCK (Check): 2D cinematic illustrated storytelling: clean linework, expressive simple characters, detailed environments, strong lighting, readable silhouettes, consistent proportions. Not childish, not clipart, not stock, not anime, not inconsistent hyperrealism.
EXACT CHARACTER: Same Latino man throughout, ages 22 to 27: short dark brown hair, lean build, simple expressive face, readable eyes, clean linework, not a model, not a cartoon mascot. Age 22: cheap office collared shirt, dark trousers, worn backpack. After ownership: same face, slightly sharper haircut, dark green-and-gold team jacket over a casual shirt. Age 27: same person five years older, faint stubble, more tired eyes, same hairline and jaw. Never swap ethnicity, never redesign the face. Age now: 25. State: owner moving into own apartment. Wardrobe matches age/state from the protagonist bible.
EXACT ACTION: in this story world: Temporada 4: 19-13.
EXACT ENVIRONMENT: Night streets of a mid-size fictional city near the municipal arena.
STORY TIME: AGE 25 · season 4
CAMERA: top-down
COMPOSITION: 16:9 widescreen, strong foreground/midground/background, one clear subject Foreground: a distinct near-plane object for this beat. Background: deep environment, different depth than the previous still.
LIGHTING: cinematic motivated light, strong depth
IMPORTANT OBJECTS: story-specific props only
CONTINUITY: Same protagonist face and hair. Same Halcones arena architecture when in stadium. Wardrobe matches age/state from the protagonist bible. Do not invent a new man or a new building.
AVOID: anime, stock photo, photoreal random faces, clipart, collage, readable UI text, watermarks.
```

## 064 — P1

- shot_id: `064`
- priority: `P1` (generation order)
- requires_own_still: `true`
- protagonist_era: `growing_owner`
- location: `locker_room`
- mood: `tension`
- story_function: `progress`
- visual_bible_refs: protagonist_visual_bible, arena_visual_bible, team_visual_bible, coach_visual_bible
- reuse_slots (fallback only): 073, 082

```
2D cinematic illustrated storytelling, simple expressive protagonist, detailed environments, clean linework, cinematic lighting, strong depth, consistent proportions, mature not childish. Not anime, not clipart, not stock-photo look, not hyperrealistic random humans.
STYLE LOCK (Check): 2D cinematic illustrated storytelling: clean linework, expressive simple characters, detailed environments, strong lighting, readable silhouettes, consistent proportions. Not childish, not clipart, not stock, not anime, not inconsistent hyperrealism.
EXACT CHARACTER: Same Latino man throughout, ages 22 to 27: short dark brown hair, lean build, simple expressive face, readable eyes, clean linework, not a model, not a cartoon mascot. Age 22: cheap office collared shirt, dark trousers, worn backpack. After ownership: same face, slightly sharper haircut, dark green-and-gold team jacket over a casual shirt. Age 27: same person five years older, faint stubble, more tired eyes, same hairline and jaw. Never swap ethnicity, never redesign the face. Age now: 25. State: owner moving into own apartment. Wardrobe matches age/state from the protagonist bible.
EXACT ACTION: keys dropping into a younger palm; older staffer hand. Beat: in the Halcones locker room / tunnel threshold: El primer record ganador. El vestuario lo celebra como si fuera un título. No lo es. El coach nuevo —ya no el interino—
EXACT ENVIRONMENT: Halcones locker room. Los Halcones de la Ciudad: dark green and copper-gold, hawk mark on jerseys. Worn kits early, cleaner later. Same uniform identity across years.
STORY TIME: AGE 25 · season 4
CAMERA: close-up
COMPOSITION: 16:9 widescreen, strong foreground/midground/background, one clear subject Foreground: ring of old arena keys. Background: blurred lockers.
LIGHTING: cinematic motivated light, strong depth
IMPORTANT OBJECTS: story-specific props only
CONTINUITY: Same protagonist face and hair. Same Halcones arena architecture when in stadium. Wardrobe matches age/state from the protagonist bible. Do not invent a new man or a new building.
AVOID: anime, stock photo, photoreal random faces, clipart, collage, readable UI text, watermarks.
```

## 066 — P1

- shot_id: `066`
- priority: `P1` (generation order)
- requires_own_still: `true`
- protagonist_era: `growing_owner`
- location: `city`
- mood: `tension`
- story_function: `progress`
- visual_bible_refs: protagonist_visual_bible
- reuse_slots (fallback only): 074, 083

```
2D cinematic illustrated storytelling, simple expressive protagonist, detailed environments, clean linework, cinematic lighting, strong depth, consistent proportions, mature not childish. Not anime, not clipart, not stock-photo look, not hyperrealistic random humans.
STYLE LOCK (Check): 2D cinematic illustrated storytelling: clean linework, expressive simple characters, detailed environments, strong lighting, readable silhouettes, consistent proportions. Not childish, not clipart, not stock, not anime, not inconsistent hyperrealism.
EXACT CHARACTER: Same Latino man throughout, ages 22 to 27: short dark brown hair, lean build, simple expressive face, readable eyes, clean linework, not a model, not a cartoon mascot. Age 22: cheap office collared shirt, dark trousers, worn backpack. After ownership: same face, slightly sharper haircut, dark green-and-gold team jacket over a casual shirt. Age 27: same person five years older, faint stubble, more tired eyes, same hairline and jaw. Never swap ethnicity, never redesign the face. Age now: 25. State: owner moving into own apartment. Wardrobe matches age/state from the protagonist bible.
EXACT ACTION: in this story world: Cuatro mil ochocientos otra vez. El número del club en el papel cruza cincuenta y cuatro millones doscientos cincuenta y
EXACT ENVIRONMENT: Night streets of a mid-size fictional city near the municipal arena.
STORY TIME: AGE 25 · season 4
CAMERA: side tracking
COMPOSITION: 16:9 widescreen, strong foreground/midground/background, one clear subject Foreground: a distinct near-plane object for this beat. Background: deep environment, different depth than the previous still.
LIGHTING: cinematic motivated light, strong depth
IMPORTANT OBJECTS: story-specific props only
CONTINUITY: Same protagonist face and hair. Same Halcones arena architecture when in stadium. Wardrobe matches age/state from the protagonist bible. Do not invent a new man or a new building.
AVOID: anime, stock photo, photoreal random faces, clipart, collage, readable UI text, watermarks.
```

## 067 — P0

- shot_id: `067`
- priority: `P0` (generation order)
- requires_own_still: `true`
- protagonist_era: `growing_owner`
- location: `locker_room`
- mood: `happiness`
- story_function: `reward`
- visual_bible_refs: protagonist_visual_bible, arena_visual_bible, team_visual_bible, utilero_visual_bible
- reuse_slots (fallback only): —

```
2D cinematic illustrated storytelling, simple expressive protagonist, detailed environments, clean linework, cinematic lighting, strong depth, consistent proportions, mature not childish. Not anime, not clipart, not stock-photo look, not hyperrealistic random humans.
STYLE LOCK (Check): 2D cinematic illustrated storytelling: clean linework, expressive simple characters, detailed environments, strong lighting, readable silhouettes, consistent proportions. Not childish, not clipart, not stock, not anime, not inconsistent hyperrealism.
EXACT CHARACTER: Same Latino man throughout, ages 22 to 27: short dark brown hair, lean build, simple expressive face, readable eyes, clean linework, not a model, not a cartoon mascot. Age 22: cheap office collared shirt, dark trousers, worn backpack. After ownership: same face, slightly sharper haircut, dark green-and-gold team jacket over a casual shirt. Age 27: same person five years older, faint stubble, more tired eyes, same hairline and jaw. Never swap ethnicity, never redesign the face. Age now: 25. State: owner moving into own apartment. Wardrobe matches age/state from the protagonist bible.
EXACT ACTION: walking the locker aisle, not facing camera. Beat: in the Halcones locker room / tunnel threshold: En el tercero pide un agua y se ríe cuando el utilero le dice “familia del jefe”. Tu vieja guarda el ticket. No es un so
EXACT ENVIRONMENT: Halcones locker room. Los Halcones de la Ciudad: dark green and copper-gold, hawk mark on jerseys. Worn kits early, cleaner later. Same uniform identity across years.
STORY TIME: AGE 25 · season 4
CAMERA: side angle along locker row
COMPOSITION: 16:9 widescreen, strong foreground/midground/background, one clear subject Foreground: open locker door. Background: chalkboard 0-0.
LIGHTING: cinematic motivated light, strong depth
IMPORTANT OBJECTS: story-specific props only
CONTINUITY: Same protagonist face and hair. Same Halcones arena architecture when in stadium. Wardrobe matches age/state from the protagonist bible. Do not invent a new man or a new building.
AVOID: anime, stock photo, photoreal random faces, clipart, collage, readable UI text, watermarks.
```

## 071 — P1

- shot_id: `071`
- priority: `P1` (generation order)
- requires_own_still: `true`
- protagonist_era: `growing_owner`
- location: `city`
- mood: `tension`
- story_function: `progress`
- visual_bible_refs: protagonist_visual_bible
- reuse_slots (fallback only): 081

```
2D cinematic illustrated storytelling, simple expressive protagonist, detailed environments, clean linework, cinematic lighting, strong depth, consistent proportions, mature not childish. Not anime, not clipart, not stock-photo look, not hyperrealistic random humans.
STYLE LOCK (Check): 2D cinematic illustrated storytelling: clean linework, expressive simple characters, detailed environments, strong lighting, readable silhouettes, consistent proportions. Not childish, not clipart, not stock, not anime, not inconsistent hyperrealism.
EXACT CHARACTER: Same Latino man throughout, ages 22 to 27: short dark brown hair, lean build, simple expressive face, readable eyes, clean linework, not a model, not a cartoon mascot. Age 22: cheap office collared shirt, dark trousers, worn backpack. After ownership: same face, slightly sharper haircut, dark green-and-gold team jacket over a casual shirt. Age 27: same person five years older, faint stubble, more tired eyes, same hairline and jaw. Never swap ethnicity, never redesign the face. Age now: 25. State: owner moving into own apartment. Wardrobe matches age/state from the protagonist bible.
EXACT ACTION: in this story world: Un local pone su nombre en la camiseta. Hay plata que no salió de tu bolsillo.
EXACT ENVIRONMENT: Night streets of a mid-size fictional city near the municipal arena.
STORY TIME: AGE 25 · season 4
CAMERA: over the shoulder
COMPOSITION: 16:9 widescreen, strong foreground/midground/background, one clear subject Foreground: a distinct near-plane object for this beat. Background: deep environment, different depth than the previous still.
LIGHTING: cinematic motivated light, strong depth
IMPORTANT OBJECTS: story-specific props only
CONTINUITY: Same protagonist face and hair. Same Halcones arena architecture when in stadium. Wardrobe matches age/state from the protagonist bible. Do not invent a new man or a new building.
AVOID: anime, stock photo, photoreal random faces, clipart, collage, readable UI text, watermarks.
```

## 075 — P1

- shot_id: `075`
- priority: `P1` (generation order)
- requires_own_still: `true`
- protagonist_era: `established_owner`
- location: `city`
- mood: `tension`
- story_function: `progress`
- visual_bible_refs: protagonist_visual_bible
- reuse_slots (fallback only): 089, 098

```
2D cinematic illustrated storytelling, simple expressive protagonist, detailed environments, clean linework, cinematic lighting, strong depth, consistent proportions, mature not childish. Not anime, not clipart, not stock-photo look, not hyperrealistic random humans.
STYLE LOCK (Check): 2D cinematic illustrated storytelling: clean linework, expressive simple characters, detailed environments, strong lighting, readable silhouettes, consistent proportions. Not childish, not clipart, not stock, not anime, not inconsistent hyperrealism.
EXACT CHARACTER: Same Latino man throughout, ages 22 to 27: short dark brown hair, lean build, simple expressive face, readable eyes, clean linework, not a model, not a cartoon mascot. Age 22: cheap office collared shirt, dark trousers, worn backpack. After ownership: same face, slightly sharper haircut, dark green-and-gold team jacket over a casual shirt. Age 27: same person five years older, faint stubble, more tired eyes, same hairline and jaw. Never swap ethnicity, never redesign the face. Age now: 26. State: full-time owner, sold-out arena. Wardrobe matches age/state from the protagonist bible.
EXACT ACTION: in this story world: Primera ronda. Se acaba ahí.
EXACT ENVIRONMENT: Night streets of a mid-size fictional city near the municipal arena.
STORY TIME: AGE 26 · season 5
CAMERA: profile medium
COMPOSITION: 16:9 widescreen, strong foreground/midground/background, one clear subject Foreground: a distinct near-plane object for this beat. Background: deep environment, different depth than the previous still.
LIGHTING: cinematic motivated light, strong depth
IMPORTANT OBJECTS: story-specific props only
CONTINUITY: Same protagonist face and hair. Same Halcones arena architecture when in stadium. Wardrobe matches age/state from the protagonist bible. Do not invent a new man or a new building.
AVOID: anime, stock photo, photoreal random faces, clipart, collage, readable UI text, watermarks.
```

## 095 — P0

- shot_id: `095`
- priority: `P0` (generation order)
- requires_own_still: `true`
- protagonist_era: `late_story`
- location: `city`
- mood: `reflection`
- story_function: `ending`
- visual_bible_refs: protagonist_visual_bible
- reuse_slots (fallback only): —

```
2D cinematic illustrated storytelling, simple expressive protagonist, detailed environments, clean linework, cinematic lighting, strong depth, consistent proportions, mature not childish. Not anime, not clipart, not stock-photo look, not hyperrealistic random humans.
STYLE LOCK (Check): 2D cinematic illustrated storytelling: clean linework, expressive simple characters, detailed environments, strong lighting, readable silhouettes, consistent proportions. Not childish, not clipart, not stock, not anime, not inconsistent hyperrealism.
EXACT CHARACTER: Same Latino man throughout, ages 22 to 27: short dark brown hair, lean build, simple expressive face, readable eyes, clean linework, not a model, not a cartoon mascot. Age 22: cheap office collared shirt, dark trousers, worn backpack. After ownership: same face, slightly sharper haircut, dark green-and-gold team jacket over a casual shirt. Age 27: same person five years older, faint stubble, more tired eyes, same hairline and jaw. Never swap ethnicity, never redesign the face. Age now: 27. State: owner, paper millionaire, empty arena. Wardrobe matches age/state from the protagonist bible.
EXACT ACTION: Oferta de adquisición
EXACT ENVIRONMENT: Night streets of a mid-size fictional city near the municipal arena.
STORY TIME: AGE 27 · season 6
CAMERA: wide shot
COMPOSITION: 16:9 widescreen, strong foreground/midground/background, one clear subject
LIGHTING: cinematic motivated light, strong depth
IMPORTANT OBJECTS: smartphone with an email on screen, unreadable tiny type
CONTINUITY: Same protagonist face and hair. Same Halcones arena architecture when in stadium. Wardrobe matches age/state from the protagonist bible. Do not invent a new man or a new building.
AVOID: anime, stock photo, photoreal random faces, clipart, collage, readable UI text, watermarks.
```
