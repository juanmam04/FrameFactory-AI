/* Built-in creative feedback agent, available in editorial and production. */
const STORE="ff_agent_global_rules_v1",CURRENT="ff_agent_active_project";
const $=id=>document.getElementById(id);
const rules=()=>{try{return JSON.parse(localStorage.getItem(STORE)||"[]")}catch{return []}};
const saveRules=list=>localStorage.setItem(STORE,JSON.stringify(list));
const activeId=()=>{const hash=decodeURIComponent(location.hash||"");return hash.startsWith("#project/")?hash.slice(9):localStorage.getItem(CURRENT)};
function snapshot(id){try{return JSON.parse(localStorage.getItem("ff_editorial_v1")||"{}")[id]||null}catch{return null}}
const esc=t=>String(t||"").replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;");
let suggestion=null,busy=false;
const style=document.createElement("style");style.textContent=`
#ff-agent-open{position:fixed;right:22px;bottom:23px;z-index:1100;background:#0e1e2d;color:#fff;border:0;border-radius:40px;box-shadow:0 12px 35px #102d4c32;padding:13px 18px;font-weight:750;cursor:pointer}
#ff-agent-panel{position:fixed;right:20px;bottom:83px;width:min(430px,calc(100vw - 25px));max-height:min(750px,85vh);z-index:1101;background:#fff;border-radius:20px;border:1px solid #dfe9ed;box-shadow:0 20px 70px #102d4c33;display:flex;flex-direction:column;overflow:hidden;font:inherit;color:#172938}
#ff-agent-panel[hidden]{display:none}#ff-agent-top{padding:16px 20px;background:#f2f8fb;display:flex;justify-content:space-between;gap:12px;align-items:center}
#ff-agent-top strong{font-size:16px}#ff-agent-close{border:0;background:transparent;font-size:24px;cursor:pointer}
#ff-agent-log{padding:16px;overflow:auto;flex:1;min-height:130px;display:flex;flex-direction:column;gap:14px}
.ff-agent-msg{line-height:1.5;font-size:14px;border-radius:14px;padding:12px 14px;white-space:pre-wrap;background:#f1f5f7}
.ff-agent-msg.user{background:#dbf0f8;align-self:flex-end}.ff-agent-msg.agent{align-self:stretch}
.ff-agent-proposal{border:1px solid #b6dce8;background:#f7fcfe;border-radius:12px;padding:12px;font-size:13px;display:grid;gap:10px}
.ff-agent-proposal button,#ff-agent-send{border:0;border-radius:10px;background:#0e1e2d;color:white;padding:11px 13px;cursor:pointer;font-weight:700;text-align:center}
.ff-agent-proposal button.secondary{color:#143248;background:#e7f1f5}#ff-agent-entry{border-top:1px solid #e6eef1;padding:12px;display:grid;gap:8px}
#ff-agent-feedback{width:100%;resize:vertical;min-height:72px;border:1px solid #cadae0;border-radius:10px;padding:10px;box-sizing:border-box;font:inherit}
.ff-agent-foot{display:flex;justify-content:space-between;align-items:center;font-size:12px;color:#607889}
#ff-agent-send:disabled,.ff-agent-proposal button:disabled{opacity:.55;cursor:wait}
`;document.head.appendChild(style);
const open=document.createElement("button");open.id="ff-agent-open";open.textContent="✦ Agente IA";open.type="button";document.body.appendChild(open);
const panel=document.createElement("aside");panel.id="ff-agent-panel";panel.hidden=true;panel.setAttribute("aria-label","Agente editorial FrameFactory");
panel.innerHTML='<div id="ff-agent-top"><div><strong>✦ Agente editorial</strong><div style="font-size:12px;color:#5c7485">Comentarios, guiones y mejoras futuras</div></div><button type="button" id="ff-agent-close" aria-label="Cerrar">×</button></div><div id="ff-agent-log" aria-live="polite"><div class="ff-agent-msg agent">Decime qué está fallando. Voy a revisar el proyecto y proponer una corrección. Nada se modifica sin tu aprobación.</div></div><div id="ff-agent-entry"><textarea id="ff-agent-feedback" placeholder="Por ejemplo: el video arranca dentro del gimnasio y nunca explica cómo lo compré."></textarea><div class="ff-agent-foot"><span id="ff-agent-status">Reglas futuras: '+rules().length+'</span><button id="ff-agent-send" type="button">Enviar</button></div></div>';document.body.appendChild(panel);
const log=$("ff-agent-log"),status=$("ff-agent-status");
function message(text,who="agent"){const div=document.createElement("div");div.className="ff-agent-msg "+who;div.textContent=text;log.appendChild(div);log.scrollTop=log.scrollHeight;return div}
const loadId=()=>{let id=activeId();if(!id){message("Abrí primero el proyecto sobre el que querés trabajar. El agente necesita conocer su historia y guion.");return null}return id};
async function call(id,route,payload){const res=await fetch("/api/projects/"+encodeURIComponent(id)+"/agent/"+route,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({...payload,project_snapshot:snapshot(id),creative_rules:rules()})});const json=await res.json().catch(()=>({}));if(!res.ok)throw Error(typeof json.detail==="string"?json.detail:"No se pudo ejecutar la acción.");return json}
function setBusy(value,text){busy=value;$("ff-agent-send").disabled=value;status.textContent=value?(text||"Trabajando…"):"Reglas futuras: "+rules().length}
async function executeFeedback(){if(busy)return;const id=loadId();if(!id)return;const box=$("ff-agent-feedback"),txt=box.value.trim();if(txt.length<3){message("Describime el problema un poco más.");return}box.value="";message(txt,"user");setBusy(true,"Analizando el proyecto…");try{const response=await call(id,"chat",{message:txt});message(response.reply);suggestion={id,...response};const actions=document.createElement("div");actions.className="ff-agent-proposal";
if(response.suggested_edit){const p=document.createElement("div");p.textContent="Corrección propuesta: "+response.suggested_edit;actions.appendChild(p);const btn=document.createElement("button");btn.textContent=response.suggested_scope==="full"?"Aplicar corrección al guion":"Corregir inicio del guion";btn.onclick=async()=>{if(busy)return;if(!confirm("¿Aplicar esta corrección al guion? Se reiniciará la aprobación y auditoría."))return;setBusy(true,"Reescribiendo el guion…");try{const r=await call(id,"revise",{instruction:response.suggested_edit,scope:response.suggested_scope});message(r.note+" Recargá el proyecto para revisar la nueva versión.");btn.disabled=true}catch(e){message(e.message)}finally{setBusy(false)}};actions.appendChild(btn)}
if(response.proposed_rule){const p=document.createElement("div");p.textContent="Regla propuesta para futuros videos: "+response.proposed_rule;actions.appendChild(p);const btn=document.createElement("button");btn.className="secondary";btn.textContent="Guardar como regla permanente";btn.onclick=async()=>{if(busy)return;setBusy(true,"Guardando regla…");try{await call(id,"rule",{rule:response.proposed_rule});const updated=[...rules(),response.proposed_rule].filter((v,i,a)=>a.findIndex(x=>x.toLowerCase()===v.toLowerCase())===i);saveRules(updated);btn.disabled=true;btn.textContent="✓ Regla guardada";message("Regla aplicada a este proyecto y guardada para las próximas producciones en este navegador.")}catch(e){message(e.message)}finally{setBusy(false)}};actions.appendChild(btn)}
if(actions.childElementCount)log.appendChild(actions);log.scrollTop=log.scrollHeight
}catch(e){message("No se pudo analizar: "+e.message)}finally{setBusy(false)}}
open.onclick=()=>{panel.hidden=!panel.hidden;if(!panel.hidden)$("ff-agent-feedback").focus()};
$("ff-agent-close").onclick=()=>panel.hidden=true;
$("ff-agent-send").onclick=executeFeedback;
$("ff-agent-feedback").onkeydown=e=>{if(e.key==="Enter"&&(e.ctrlKey||e.metaKey)){e.preventDefault();executeFeedback()}};
