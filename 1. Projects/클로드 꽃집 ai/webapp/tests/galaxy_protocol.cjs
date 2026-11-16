const vm=require('node:vm'),fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const listeners={};let stored;
const ctx={URL,Response,Date,console,importScripts:()=>{},shareStore:async(mode,value)=>{if(mode==='put')stored=value;},self:{location:{origin:'https://flower.test'},addEventListener:(name,fn)=>listeners[name]=fn}};
vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../static/galaxy/sw.js'),'utf8'),ctx);
async function share(text,files=[]){const form=new FormData();if(text)form.set('text',text);for(const f of files)form.append('files',f);const req=new Request('https://flower.test/galaxy-share',{method:'POST',body:form});let result;listeners.fetch({request:req,respondWith:p=>result=p});return await result;}
(async()=>{
assert.equal((await share('가상 전사문')).status,303);assert.equal(stored.text,'가상 전사문');
assert.equal((await share('',[new File(['synthetic'],'call.wav',{type:'audio/wav'})])).status,303);assert.equal(stored.files[0].name,'call.wav');
assert.equal((await share('',[new File(['가상 전사문'],'call.txt',{type:'text/plain'})])).status,303);
assert.equal((await share('')).status,400);
assert.equal((await share('',[new File(['x'],'bad.exe',{type:'application/octet-stream'})])).status,400);
assert.equal((await share('x'.repeat(100001))).status,400);
let intercepted=false;listeners.fetch({request:new Request('https://flower.test/galaxy'),respondWith:()=>intercepted=true});assert.equal(intercepted,false);
// No telephony listener exists. Virtual call state events alone never produce an intake.
assert.equal(listeners['callstatechange'],undefined);
console.log('8 protocol checks PASS: text/audio/txt, empty/type/size rejection, ordinary navigation, no call capture');
})().catch(e=>{console.error(e);process.exitCode=1;});
