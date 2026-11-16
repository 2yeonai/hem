const vm=require('node:vm'),fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {indexedDB}=require('fake-indexeddb');const crypto=require('node:crypto');const ctx={indexedDB,crypto};vm.createContext(ctx);vm.runInContext(fs.readFileSync(path.join(__dirname,'../static/galaxy/store.js'),'utf8'),ctx);
(async()=>{const q=ctx.shareStore;
const a=await q('put',{text:'가상1',files:[],created:1}),b=await q('put',{text:'가상2',files:[],created:2});assert.equal((await q('list')).length,2);
await q('update',{id:a.id,state:'retry'});assert.equal((await q('get')).state,'retry');
await q('update',{id:a.id,state:'completed',text:'',files:[]});assert.equal((await q('get')).id,b.id);
await q('delete',b.id);assert.equal((await q('list')).find(r=>r.id===b.id).state,'deleted');assert.equal(await q('get'),undefined);
console.log('queue persistence/state checks PASS (fake-indexeddb, not browser restart)');})().catch(e=>{console.error(e);process.exitCode=1;});
