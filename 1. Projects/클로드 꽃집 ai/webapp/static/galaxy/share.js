(async()=>{
 const status=document.querySelector('#status'),send=document.querySelector('#send'),select=document.querySelector('#queue');let pending,installEvent;
 window.addEventListener('beforeinstallprompt',e=>{e.preventDefault();installEvent=e;document.querySelector('#install').disabled=false;});
 document.querySelector('#install').onclick=async()=>{if(installEvent){await installEvent.prompt();installEvent=null;}};
 async function load(id){const rows=await shareStore('list');select.replaceChildren();
 for(const r of rows){const option=document.createElement('option');option.value=r.id;option.textContent=`${new Date(r.created).toLocaleString()} · ${r.state}`;select.append(option);}
 pending=rows.find(r=>r.id===id)||rows.find(r=>!['completed','deleted'].includes(r.state));
 if(pending)select.value=pending.id;
 const textFile=pending?.files?.find(f=>f.type==='text/plain'||/\.txt$/i.test(f.name));
 document.querySelector('#transcript').value=[pending?.text,textFile&&!pending.edited?await textFile.text():''].filter(Boolean).join('\n');
 document.querySelector('#file-name').textContent=pending?.files?.map(f=>f.name).join(', ')||'파일 없음';
 send.disabled=!pending||['completed','deleted'].includes(pending.state);
 }
 try{
 if(!isSecureContext||!navigator.serviceWorker||!window.indexedDB)throw Error('HTTPS·서비스워커·IndexedDB 필요');
 await navigator.serviceWorker.register('/galaxy-sw.js',{scope:'/'});await navigator.serviceWorker.ready;
 const m=await(await fetch('/galaxy.webmanifest')).json();
 if(![192,512].every(n=>m.icons.some(i=>i.sizes===`${n}x${n}`&&i.type==='image/png')))throw Error('설치 아이콘 누락');
 document.querySelector('#install-status').textContent=matchMedia('(display-mode: standalone)').matches?'설치 앱 실행 중':'설치 기본 요건 확인. Chrome 메뉴의 앱 설치를 확인하세요. 설치 가능 판정은 Chrome이 결정합니다.';
 await load();status.textContent='공유 대기열 준비 완료. 미접수 자료는 자동 삭제하지 않습니다.';
 }catch(e){status.textContent='공유 준비 실패: '+e.message;return;}
 select.onchange=()=>load(select.value);
 document.querySelector('#discard').onclick=async()=>{if(pending){await shareStore('delete',pending.id);await load();}};
 document.querySelector('#transfer').onsubmit=async e=>{e.preventDefault();if(!pending)return;send.disabled=true;const id=pending.id;
 try{
 const form=new FormData(e.target),text=String(form.get('raw_text')||'');
 await shareStore('update',{id,text,edited:true,state:'sending'});
 const audio=pending.files.filter(f=>!(f.type==='text/plain'||/\.txt$/i.test(f.name)));
 if(audio.length>1)throw Error('녹음은 한 개씩 보내주세요.');
 if(!document.querySelector('#use-text').checked&&audio[0])form.set('audio',audio[0],audio[0].name);
 if(!text.trim()&&!form.get('audio'))throw Error('내용이 필요합니다.');
 const response=await fetch('/intakes',{method:'POST',body:form,credentials:'same-origin'}),target=new URL(response.url);
 if(!response.ok||!/^\/intake\/[a-z0-9]+$/.test(target.pathname))throw Error('로그인 만료 또는 접수 실패. 로그인 후 재시도하세요.');
 await shareStore('update',{id,state:'completed',text:'',files:[],receipt:target.pathname});location.assign(target.pathname);
 }catch(e){await shareStore('update',{id,state:'retry'});status.textContent=e.message;await load(id);}
 };
})();
