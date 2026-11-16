(async()=>{
  const status=document.querySelector('#status'),send=document.querySelector('#send');
  let pending;
  try{
    await navigator.serviceWorker.register('/galaxy-sw.js',{scope:'/'});
    await navigator.serviceWorker.ready;
    pending=await shareStore('get');
    if(pending&&Date.now()-pending.created>86400000){await shareStore('delete');pending=null;}
    const textFile=pending?.files.find(f=>f.type==='text/plain'||/\.txt$/i.test(f.name));
    document.querySelector('#transcript').value=[pending?.text,textFile?await textFile.text():''].filter(Boolean).join('\n');
    document.querySelector('#file-name').textContent=pending?.files.map(f=>f.name).join(', ')||'공유된 파일 없음';
    status.textContent='공유 준비 완료. 자료는 확인 후 접수를 누를 때 서버로 전달됩니다.';
    send.disabled=false;
  }catch(e){status.textContent='공유 준비 실패. Chrome/HTTPS에서 다시 열어주세요.';return;}
  document.querySelector('#discard').onclick=async()=>{await shareStore('delete');location.reload();};
  document.querySelector('#transfer').onsubmit=async event=>{
    event.preventDefault();send.disabled=true;
    try{
      const form=new FormData(event.target);
      const audio=pending?.files.filter(f=>!(f.type==='text/plain'||/\.txt$/i.test(f.name)))||[];
      if(audio.length>1)throw Error('녹음은 한 개씩 보내주세요.');
      if(!document.querySelector('#use-text').checked&&audio[0])form.set('audio',audio[0],audio[0].name);
      if(!String(form.get('raw_text')||'').trim()&&!form.get('audio'))throw Error('전사문 또는 녹음이 필요합니다.');
      const response=await fetch('/intakes',{method:'POST',body:form,credentials:'same-origin'});
      const target=new URL(response.url);
      if(response.ok&&/^\/intake\/[a-z0-9]+$/.test(target.pathname)){
        await shareStore('delete');location.assign(target.pathname);
      }else{throw Error('접수 실패 또는 로그인 만료. 로그인 후 이 화면에서 다시 보내주세요. 자료는 기기에 남아 있습니다.');}
    }catch(e){status.textContent=e.message;send.disabled=false;}
  };
})();
