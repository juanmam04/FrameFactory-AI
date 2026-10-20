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
let calls=[];
globalThis.fetch=async (url,options)=>{
 calls.push({url,method:options.method});
 if(url.endsWith('/editorial/load')){
  assert.equal(JSON.parse(options.body).project_snapshot.id,project.id);
  return {ok:true,json:async()=>({editorial:project.editorial})};
 }
 return {ok:false,status:404,json:async()=>({detail:'Project not found'})};
};
assert.equal((await module.loadEditorial(project.id)).editorial.active_stage,'concepts');
assert.equal(calls.filter(x=>x.url.endsWith('/editorial/load')).length,1);
assert.equal(calls[1].method,'POST');
// A server error must never overwrite an existing project with an old backup.
calls=[];
globalThis.fetch=async (url,options)=>{calls.push(url);return {ok:false,status:500,json:async()=>({detail:'Unavailable'})}};
await assert.rejects(module.loadEditorial(project.id),/Unavailable/);
assert.equal(calls.length,1);
console.log('Client recovery passed: cached snapshot loads in one serverless request; 500 preserves server state.');
