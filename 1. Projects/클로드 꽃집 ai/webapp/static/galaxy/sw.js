importScripts('/static/galaxy/store.js');
self.addEventListener('install',event=>event.waitUntil(self.skipWaiting()));
self.addEventListener('activate',event=>event.waitUntil(self.clients.claim()));
self.addEventListener('fetch',event=>{
  const url=new URL(event.request.url);
  if(url.origin!==self.location.origin || url.pathname!=='/galaxy-share' || event.request.method!=='POST')return;
  event.respondWith((async()=>{
    try {
      const form=await event.request.formData();
      const files=form.getAll('files').filter(f=>typeof f!=='string'&&f.size);
      const text=String(form.get('text')||'');
      if(files.length>2 || text.length>100000 || files.reduce((n,f)=>n+f.size,0)>24*1024*1024)throw Error('size');
      if(files.some(f=>!f.type.startsWith('audio/')&&f.type!=='text/plain'&&!/\.(m4a|wav|mp3|txt)$/i.test(f.name)))throw Error('type');
      if(!files.length&&!text.trim())throw Error('empty');
      await shareStore('put',{text,files,created:Date.now()});
      return Response.redirect(new URL('/galaxy',self.location.origin).href,303);
    }catch(e){return new Response('공유 자료를 받지 못했습니다. 텍스트나 24MB 이하 녹음 1개를 공유해주세요.',{status:400});}
  })());
});
