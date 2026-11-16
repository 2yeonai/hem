/* Durable per-origin queue. Unsubmitted items never expire or get overwritten automatically. */
function openShareDB(){return new Promise((resolve,reject)=>{
 const r=indexedDB.open('flower-shared-input',2);
 r.onupgradeneeded=()=>{if(!r.result.objectStoreNames.contains('pending'))r.result.createObjectStore('pending');};
 r.onsuccess=()=>resolve(r.result);r.onerror=()=>reject(r.error);
});}
async function shareStore(mode,value){const db=await openShareDB();try{return await new Promise((resolve,reject)=>{
 const tx=db.transaction('pending',mode==='get'||mode==='list'?'readonly':'readwrite'),s=tx.objectStore('pending');let result;
 const old=s.get('current');old.onsuccess=()=>{
  if(old.result&&mode!=='get'&&mode!=='list'){s.put({...old.result,id:'legacy',state:'pending'},'legacy');s.delete('current');}
  if(mode==='put'){const item={...value,id:crypto.randomUUID(),state:'pending'};s.put(item,item.id);result=item;}
  else if(mode==='update'){const r=s.get(value.id);r.onsuccess=()=>{if(r.result){result={...r.result,...value};s.put(result,value.id);}};}
  else if(mode==='delete'){const r=s.get(value);r.onsuccess=()=>{if(r.result){const {id,created}=r.result;s.put({id,created,state:'deleted',files:[],text:''},id);}};}
  else {const r=s.getAll();r.onsuccess=()=>{result=r.result;if(old.result)result=result.filter(i=>i!==old.result);result=result.map(i=>i.id?i:{...i,id:'legacy',state:'pending'});if(mode==='get')result=result.find(i=>!['completed','deleted'].includes(i.state));};}
 };
 tx.oncomplete=()=>resolve(result);tx.onerror=()=>reject(tx.error);tx.onabort=()=>reject(tx.error);
});}finally{db.close();}}
