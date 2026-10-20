// Client recovery contract, without browser automation or paid providers.
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
const values=new Map();
globalThis.localStorage={getItem:k=>values.get(k)??null,setItem:(k,v)=>values.set(k,v)};
const source=await readFile(new URL('../studio/static/creative-studio.js',import.meta.url),'utf8');
const module=await import('data:text/javascript;base64,'+Buffer.from(source+'\nexport {mergeProjects,loadEditorial,cachedProjects};').toString('base64'));
const project={id:'qa-recovery',title:'QA',editorial:{active_stage:'concepts',stages:{brief:{data:{language:'es'},approved:true}}}};
module.mergeProjects([project]);
assert.equal(module.cachedProjects()['qa-recovery'].title,'QA');
let restored=false;
let calls=[];
globalThis.fetch=async (url,options)=>{
 calls.push({url,method:options.method});
 if(url.endsWith('/restore')){assert.equal(JSON.parse(options.body).project.id,project.id);restored=true;return {ok:true,json:async()=>({})};}
 if(!restored)return {ok:false,status:404,json:async()=>({detail:'Project not found'})};
 return {ok:true,json:async()=>({editorial:project.editorial})};
};
assert.equal((await module.loadEditorial(project.id)).editorial.active_stage,'concepts');
assert.equal(calls.filter(x=>x.url.endsWith('/restore')).length,1);
// A server error must never overwrite an existing project with an old backup.
calls=[];
globalThis.fetch=async (url,options)=>{calls.push(url);return {ok:false,status:500,json:async()=>({detail:'Unavailable'})}};
await assert.rejects(module.loadEditorial(project.id),/Unavailable/);
assert.equal(calls.length,1);
console.log('Client recovery passed: cached project restores after 404; 500 preserves server state.');
