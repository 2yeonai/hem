// Chromium integration, not real Galaxy hardware.
const {chromium}=require('playwright');const assert=require('node:assert/strict');
(async()=>{const b=await chromium.launch({executablePath:'/usr/bin/chromium',args:['--no-sandbox']});try{
const p=await b.newPage();await p.goto('http://127.0.0.1:5099/login');
await p.locator('[name=username]').fill('synthetic');await p.locator('[name=password]').fill('Synthetic-password-123');await Promise.all([p.waitForURL('**/'),p.locator('button').click()]);
async function home(){await p.goto('http://127.0.0.1:5099/galaxy');await p.waitForFunction(()=>!document.querySelector('#send').disabled);}
await home();await p.reload();await p.waitForFunction(()=>!!navigator.serviceWorker.controller);
await p.evaluate(()=>{for(const state of ['ringing','offhook','idle'])window.dispatchEvent(new CustomEvent('synthetic-call-state',{detail:state}));});assert.equal(await p.evaluate(()=>shareStore('get')),undefined);
async function share(text,audio=false){await home();const url=await p.evaluate(async({text,audio})=>{const f=new FormData();f.set('text',text);if(audio)f.append('files',new File(['synthetic-audio'],'test.wav',{type:'audio/wav'}));return(await fetch('/galaxy-share',{method:'POST',body:f})).url;},{text,audio});assert(url.endsWith('/galaxy'));await home();assert.equal(await p.locator('#transcript').inputValue(),text);}
async function send(){await p.locator('#send').click();await p.waitForURL('**/intake/*');return p.url();}
await share('가상 전사문');const first=await send();await home();assert.equal(await p.evaluate(()=>shareStore('get')),undefined);
await share('가상 전사문');assert.equal(await send(),first);
await share('가상 음성',true);assert((await p.locator('#file-name').textContent()).includes('test.wav'));await send();
await share('가상 폐기');await p.locator('#discard').click();await p.waitForFunction(()=>!document.querySelector('#send').disabled);assert.equal(await p.evaluate(()=>shareStore('get')),undefined);
console.log('PASS: SW text/audio, confirmation, deduplication, purge, virtual call events inert');
}finally{await b.close();}})().catch(e=>{console.error(e);process.exitCode=1;});
