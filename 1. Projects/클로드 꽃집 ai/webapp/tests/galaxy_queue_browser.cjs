const {chromium}=require('playwright'),assert=require('node:assert/strict'),fs=require('node:fs'),os=require('node:os');
(async()=>{const profile=fs.mkdtempSync(os.tmpdir()+'/flower-queue-');let context;
async function launch(){return chromium.launchPersistentContext(profile,{executablePath:process.env.TEST_CHROMIUM,args:['--no-sandbox','--no-zygote','--single-process']});}
try{
context=await launch();let p=await context.newPage();
async function login(){await p.goto('http://127.0.0.1:5099/login');await p.locator('[name=username]').fill('synthetic');await p.locator('[name=password]').fill('Synthetic-password-123');await Promise.all([p.waitForURL('**/'),p.locator('button').click()]);}
async function home(){await p.goto('http://127.0.0.1:5099/galaxy');await p.waitForFunction(()=>document.querySelector('#status').textContent.includes('준비 완료'));}
await login();await home();await p.reload();await p.waitForFunction(()=>!!navigator.serviceWorker.controller);
for(const text of ['가상 첫째','가상 둘째']){await p.evaluate(async text=>{const f=new FormData();f.set('text',text);await fetch('/galaxy-share',{method:'POST',body:f});},text);}
await home();assert.equal(await p.locator('#queue option').count(),2);
await context.setOffline(true);await p.locator('#send').click();await p.waitForFunction(()=>document.querySelector('#status').textContent.includes('fetch'));
assert.equal(await p.evaluate(async()=>(await shareStore('list'))[0].state),'retry');await context.setOffline(false);
await context.clearCookies();await p.locator('#send').click();await p.waitForFunction(()=>document.querySelector('#status').textContent.includes('로그인 만료'));assert.equal(await p.evaluate(async()=>(await shareStore('list')).length),2);
await login();await home();await p.locator('#send').click();await p.waitForURL('**/intake/*');
await home();assert.equal(await p.evaluate(async()=>(await shareStore('list')).filter(r=>r.state==='completed').length),1);
await context.close();context=await launch();p=await context.newPage();await login();await home();assert.equal(await p.locator('#transcript').inputValue(),'가상 둘째');
await p.locator('#discard').click();await p.waitForFunction(async()=>(await shareStore('list')).some(r=>r.state==='deleted'));
console.log('PASS browser queue: two shares, offline retry, expired login, completion, browser restart restore, delete');
}finally{if(context)await context.close();fs.rmSync(profile,{recursive:true,force:true});}})().catch(e=>{console.error(e);process.exitCode=1;});
