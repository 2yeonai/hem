/* Only shared inputs, never auth tokens. One day TTL; explicit discard and successful send purge. */
function openShareDB() {
  return new Promise((resolve,reject)=>{
    const r=indexedDB.open('flower-shared-input',1);
    r.onupgradeneeded=()=>r.result.createObjectStore('pending');
    r.onsuccess=()=>resolve(r.result);r.onerror=()=>reject(r.error);
  });
}
async function shareStore(mode,value) {
  const db=await openShareDB();
  try {return await new Promise((resolve,reject)=>{
    const tx=db.transaction('pending',mode==='get'?'readonly':'readwrite');
    const s=tx.objectStore('pending');
    const r=mode==='get'?s.get('current'):mode==='put'?s.put(value,'current'):s.delete('current');
    tx.oncomplete=()=>resolve(r.result);tx.onerror=()=>reject(tx.error);tx.onabort=()=>reject(tx.error);
  });} finally {db.close();}
}
