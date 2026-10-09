'use strict';
const screen = document.getElementById('screen');
const toastEl = document.getElementById('toast');
const app = {
  mode: 'home', config: {clubs:[],player_count:0,answer_seconds:30},
  name: '', user:null, session: localStorage.getItem('of_session') || '', room:null, tournament:null,
  socket:null, pingInterval:null, tournamentInterval:null, connectSeq:0,
};
function esc(x){return String(x ?? '').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
function urlParam(key, val){const u=new URL(location.href);u.search='';if(key)u.searchParams.set(key,val);history.replaceState(null,'',u.pathname+u.search);}
function toast(message){toastEl.textContent=message;toastEl.style.display='block';clearTimeout(toast.timer);toast.timer=setTimeout(()=>toastEl.style.display='none',3500);}
function currentName(){return app.user?.username || null;}
async function api(path,opts={}){const response=await fetch(path,{...opts,headers:{'Content-Type':'application/json',...(app.session ? {Authorization:`Bearer ${app.session}`} : {}),...(opts.headers||{})}});let data;try{data=await response.json();}catch{throw Error('Sunucuya ulaşılamadı.');}if(!response.ok)throw Error(typeof data.detail==='string'?data.detail:'Bir işlem başarısız oldu.');return data;}
function enc(v){return encodeURIComponent(v);}
function badgeLabel(code){return esc(code.split(/\s+/).map(x=>x[0]).slice(0,2).join('').toLocaleUpperCase('tr-TR'));}
function clubShield(name,kind=''){return `<div class="crest ${kind}"><strong>${badgeLabel(name)}</strong><small>${esc(name)}</small></div>`;}
function stopPolling(){if(app.tournamentInterval){clearInterval(app.tournamentInterval);app.tournamentInterval=null;}}
function closeSocket(){app.connectSeq++;if(app.socket){const s=app.socket;app.socket=null;s.onclose=null;s.close();}if(app.pingInterval){clearInterval(app.pingInterval);app.pingInterval=null;}}
function goHome(){closeSocket();stopPolling();app.room=null;app.tournament=null;app.mode='home';urlParam();app.user?renderHome():renderAuth();}

function renderAuth(kind='login'){
 app.mode='auth';const register=kind==='register';
 const params=new URLSearchParams(location.search);
 const from=params.get('room')?'Bir maç davetine katılacaksın.':params.get('turnuva')?'Turnuvaya katılacaksın.':'Herkes kendi kullanıcı adıyla oynar.';
 screen.innerHTML=`<div class="panel narrow auth-panel"><span class="overline">OYUNCU HESABI</span><h2>${register?'Yeni hesap oluştur':'Sahaya giriş yap'}</h2><p class="helper">${from} Kullanıcı adın sana özel olacak.</p>
 <form id="auth-form" autocomplete="on"><div class="form-group"><label for="auth-username">KULLANICI ADI</label><input class="input" id="auth-username" autocomplete="username" minlength="3" maxlength="20" pattern="[A-Za-z0-9_]{3,20}" required placeholder="örn: kartal1903"></div>
 <div class="form-group"><label for="auth-password">ŞİFRE</label><input class="input" id="auth-password" type="password" autocomplete="${register?'new-password':'current-password'}" minlength="8" maxlength="128" required placeholder="En az 8 karakter"></div>
 <button class="btn block" type="submit">${register?'HESABIMI OLUŞTUR':'GİRİŞ YAP'} →</button></form>
 <p class="helper center" style="margin-top:20px">${register?'Zaten hesabın var mı?':'Hesabın yok mu?'} <button type="button" class="btn ghost small" data-action="${register?'show-login':'show-register'}">${register?'GİRİŞ YAP':'ÜCRETSİZ KAYIT OL'}</button></p>
 <p class="helper center">Kullanıcı adları benzersizdir. Şifreni unutursan bu ilk sürümde sıfırlama bulunmuyor.</p></div>`;
 app.authKind=kind;
}
async function doAuth(){
 const username=document.getElementById('auth-username')?.value.trim();
 const password=document.getElementById('auth-password')?.value;
 if(!username||!password)return;
 const endpoint=app.authKind==='register'?'register':'login';
 const data=await api(`/api/auth/${endpoint}`,{method:'POST',body:JSON.stringify({username,password})});
 app.session=data.token;localStorage.setItem('of_session',data.token);
 app.user={id:data.user_id,username:data.username};app.name=data.username;
 toast(`Hoş geldin, ${data.username}!`);await resumeInvite();
}
async function resumeInvite(){
 const params=new URLSearchParams(location.search),room=params.get('room')?.toUpperCase(),tournament=params.get('turnuva')?.toUpperCase();
 if(room){const data=await api(`/api/rooms/${enc(room)}/join`,{method:'POST'});localStorage.setItem(`of_room_${room}`,data.token);connectRoom(room,data.token);}
 else if(tournament){const data=await api(`/api/tournaments/${enc(tournament)}/join`,{method:'POST'});localStorage.setItem(`of_tournament_${tournament}`,data.token);await loadTournament(tournament,data.token);}
 else renderHome();
}

function renderHome(){app.mode='home';screen.innerHTML=`
  <section class="hero"><div>
    <span class="overline">⚡ FUTBOLUN YENİ DÜELLOSU</span>
    <h1>İKİ TAKIM.<br><span class="accent">TEK İSİM.</span><br>BÜYÜK ZAFER.</h1>
    <p>Birbirinizden gizli takım seçin. İki formayı da giymiş futbolcuyu rakibinden önce bul. Kazanmak için yalnızca futbol bilgin değil, stratejin de gerekecek.</p>
    <div class="hero-actions"><button class="btn" data-action="create-room">⚔ 1V1 ODA KUR</button><button class="btn secondary" data-action="create-tournament">🏆 TURNUVA KUR</button></div>
    <div class="hero-badges"><span>Gerçek zamanlı eşli</span><span>7 turluk maçlar</span><span>Ani ölüm uzatması</span></div>
  </div><div class="hero-visual"><div class="field-lines"></div><div class="visual-top"><span>● 03 / 07 TUR</span><strong>1 — 1</strong></div><div class="duel-visual">${clubShield('Beşiktaş','a')}<div class="vs">VS</div>${clubShield('Real Madrid','b')}</div><div class="visual-prompt">ORTAK FUTBOLCUYU BUL ↗</div></div></section>
  <div class="stats-strip"><div class="stat-tile"><strong>1V1</strong><span>Arkadaşına meydan oku</span></div><div class="stat-tile"><strong>4 / 8 / 16</strong><span>Kişilik turnuvalar</span></div><div class="stat-tile"><strong>${app.config.player_count}+</strong><span>Başlangıç futbolcu verisi</span></div></div>
  <section class="panel" style="margin-top:24px"><div class="panel-header"><div><span class="overline">OYUNCU PROFİLİ</span><h2>Hoş geldin, ${esc(app.name)}!</h2></div><span class="pill">HESABIN AÇIK</span></div>
    <p class="helper">Bu kullanıcı adı yalnızca sana ait. Arkadaşlarını odaya veya turnuvaya davet et.</p>
    <div class="form-row"><button class="btn secondary" data-action="join-room-open">ODA KODUYLA KATIL →</button><button class="btn ghost" data-action="join-tournament-open">TURNUVAYA KATIL →</button></div>
    <div class="center" style="margin-top:18px"><button class="btn ghost small" data-action="logout">↪ HESAPTAN ÇIK</button></div>
    <p class="helper" style="margin:16px 0 0">Beta sürümü: gerçek oyuncularla eşli maç ve turnuvalar. Futbolcu veritabanı genişletiliyor.</p>
  </section>`;
}
function renderJoin(kind,known=''){const tournament=kind==='tournament';app.mode='join';app.joinKind=kind;screen.innerHTML=`<div class="panel narrow"><button class="back" data-action="home">← ANA SAYFA</button><span class="overline">${tournament?'🏆 TURNUVAYA KATIL':'⚔ DÜELLOYA KATIL'}</span><h2>${tournament?'Turnuva kodunu gir':'Oda kodunu gir'}</h2><p class="helper">${tournament?'Arkadaşlarının bulunduğu turnuvaya dahil ol.':'Rakibinle aynı odaya bağlan ve maç başlasın.'}</p>
  <div class="form-group"><label>${tournament?'TURNUVA':'ODA'} KODU</label><input class="input" id="join-code" maxlength="6" placeholder="ÖR: A8B3N9" style="text-transform:uppercase;letter-spacing:3px;font-weight:900" value="${esc(known)}"></div>
  <button class="btn block" data-action="${tournament?'join-tournament':'join-room'}">KATIL →</button></div>`;}
function renderTournamentCreate(){app.mode='create-tournament';screen.innerHTML=`<div class="panel narrow"><button class="back" data-action="home">← ANA SAYFA</button><span class="overline">🏆 ELEME ARENASI</span><h2>Yeni turnuva oluştur</h2><p class="helper">Oyuncu sayısı dolunca turnuva otomatik başlar. Her eşleşme farklı bir 7 turluk maçtır.</p>
<div class="form-group"><label>OYUNCU SAYISI</label><select id="tournament-size" class="input"><option value="4">4 Oyuncu · 2 Yarı Final + Final</option><option value="8">8 Oyuncu · Çeyrek Final + Yarı Final + Final</option><option value="16">16 Oyuncu · Son 16 + Final</option></select></div><button class="btn block" data-action="confirm-tournament">TURNUVAYI OLUŞTUR →</button></div>`;}
function readyPlayers(state){return `<div class="players-grid">${state.players.map((p,i)=>`<div class="player-mini"><div class="avatar">${esc(p.name.charAt(0).toUpperCase())}</div><div style="min-width:0"><strong>${esc(p.name)} ${i===state.me?'(Sen)':''}</strong><small class="${p.ready?'ready':(p.online?'':'offline')}">${p.ready?'✓ Seçim tamam':p.online?'● Bağlı':'○ Çevrimdışı'}</small></div></div>`).join('')}</div>`;}
function usedBlock(state){return `<div class="panel side-block"><h3>◌ ELENEN TAKIMLAR · ${state.used.length}</h3>${state.used.length?`<div class="used-list">${state.used.map(n=>`<span class="used-item">${esc(n)}</span>`).join('')}</div>`:'<p class="helper">Henüz takım elenmedi. Seçilen her takım tüm maç boyunca kilitlenecek.</p>'}<div class="hint-box">💡 <strong>Kural:</strong> İki oyuncu aynı takımı seçerse futbolcu sorusu açılmaz. Takım elenir ve tur puansız geçilir.</div></div>`;}
function renderRoom(){if(!app.room||!app.room.state)return;app.mode='room';const s=app.room.state, me=s.me;
const label=s.overtime?'UZATMA · ALTIN PUAN':`TUR ${s.round} / 7`;
const progress=s.overtime?`<div class="pill gold">⚡ İLK +1 KAZANIR</div>`:`<div class="round-progress">${Array.from({length:7},(_,i)=>`<div class="round-dot ${i<s.round-1?'done':i===s.round-1?'current':''}"></div>`).join('')}</div>`;
let board='';
if(s.phase==='lobby'){
 board=`<div class="center"><div class="lobby-illustration">⚔️</div><span class="overline">ODA HAZIR</span><h2>Rakibini bekliyorsun</h2><div class="lobby-code">${esc(s.code)}</div><p class="helper">Aşağıdaki bağlantıyı arkadaşına gönder. Odaya katılınca gizli takım seçimleri açılacak.</p><button class="btn block" data-action="copy-room">↗ DAVET BAĞLANTISINI KOPYALA</button></div>`;
}else if(s.phase==='choose'){
 const chosen=Boolean(s.my_pick);const free=app.config.clubs.filter(c=>!s.used.includes(c));
 board=`<span class="overline">${s.overtime?'⚡ ALTIN PUAN TURU':'TAKIM SEÇİMİ'}</span><h2>${chosen?'Seçimin kilitlendi':'Takımını gizlice seç'}</h2><p class="helper">${chosen?`<strong>${esc(s.my_pick)}</strong> seçtin. Rakibin hazırlanıyor. Takımlar iki seçim de tamamlanınca gösterilecek.`:'Rakibin seçimini göremezsin. Daha önce elenen takımlar kullanılamaz.'}</p>${readyPlayers(s)}
 ${!chosen?`<input class="input club-search" type="search" id="club-search" placeholder="🔎 Takım ara..." autocomplete="off"><div class="club-grid" id="club-grid">${free.map(c=>`<button class="club-btn" data-action="choose" data-club="${esc(c)}"><span class="club-emblem">${badgeLabel(c)}</span><span>${esc(c)}</span></button>`).join('')}</div>`:`<div class="center" style="padding:30px 0 16px"><span class="pill">✓ SEÇİMİN ONAYLANDI</span></div>`}
 ${s.event?.kind==='invalid'?`<p class="helper" style="color:var(--gold)">⚠ ${esc(s.event.detail)}</p>`:''}`;
}else if(s.phase==='answer'){
 const [a,b]=s.clubs||['',''];
 board=`<div class="center"><span class="overline">İLK DOĞRU CEVAP +1 PUAN</span><h2>Ortak futbolcuyu bul!</h2></div><div class="two-crests">${clubShield(a,'a')}<div class="vs">VS</div>${clubShield(b,'b')}</div><p class="match-label">Bu iki takımın A takımında da forma giymiş bir oyuncu yaz.</p>
 <div class="timer-wrap"><div class="timer" id="countdown">00:${String(app.config.answer_seconds).padStart(2,'0')}</div><div class="timer-label">SANİYE<br>KALDI</div></div><form id="answer-form" class="answer-bar"><input id="answer" class="input" placeholder="Futbolcu adı yaz..." autocomplete="off" maxlength="100" aria-label="Futbolcu adı"><button type="submit" class="btn">GÖNDER →</button></form><p class="helper center" style="margin-top:13px">Cevabı ilk doğrulanan oyuncu turu kazanır.</p>`;
}else if(s.phase==='result'){
 const e=s.event||{},same=e.kind==='same';board=`<div class="result-hero"><div class="result-symbol ${same?'same':''}">${same?'⟷':e.kind==='point'?'✓':'⌛'}</div><span class="overline">${same?'ÇAKIŞAN TAKIMLAR':e.kind==='point'?'TUR TAMAMLANDI':'PUANSIZ TUR'}</span><h2>${esc(e.headline||'Tur tamamlandı')}</h2><p>${esc(e.detail||'')}</p>${e.kind==='point'?`<span class="pill">+1 PUAN · ${esc(s.players[e.scorer]?.name||'Oyuncu')}</span>`:''}<p class="helper" style="margin-top:24px">Sonraki tura geçiliyor...</p></div>`;
}else if(s.phase==='finished'){
 const won=s.winner===me;board=`<div class="result-hero"><div class="champion">${won?'🏆':'🏁'}</div><span class="overline">MAÇ SONA ERDİ</span><h2>${won?'ZAFER SENİN!':'MAÇ TAMAMLANDI'}</h2><div class="win-name">${esc(s.players[s.winner]?.name||'Oyuncu')} kazandı</div><p>${s.scores[0]} – ${s.scores[1]} · ${s.round}. tur${s.overtime?' · Uzatma':''}</p>${s.tournament?'<button class="btn block" data-action="back-to-tournament">🏆 TURNUVA TABLOSUNA DÖN</button>':'<button class="btn block" data-action="home">ANA SAYFAYA DÖN</button>'}</div>`;
}
const opponent=s.players[1-me];screen.innerHTML=`<div class="arena-top"><div><span class="eyebrow">● MAÇ ODASI ${esc(s.code)}</span><h2 style="margin:5px 0 0;font-size:21px">${s.overtime?'⚡ Altın Puan':'Futbol Düellosu'}</h2></div><span class="pill ${s.overtime?'gold':''}">${esc(label)}</span></div>
 <div class="arena-layout"><div><div class="scoreboard"><div class="score-player ${me===0?'self':''}"><div class="score-name">${esc(s.players[0]?.name||'Bekleniyor')}</div><div class="score-number">${s.scores[0]}</div></div><div class="score-center">SKOR<strong>:</strong></div><div class="score-player ${me===1?'self':''}"><div class="score-name">${esc(s.players[1]?.name||'Rakip bekleniyor')}</div><div class="score-number">${s.scores[1]}</div></div></div>${progress}<div class="panel">${board}</div></div>${usedBlock(s)}</div>
 <div class="center" style="margin-top:18px"><button class="btn ghost small" data-action="copy-room">↗ ODA BAĞLANTISINI PAYLAŞ</button>${s.tournament?'<button class="btn ghost small" data-action="back-to-tournament" style="margin-left:7px">TURNUVAYI GÖR</button>':''}</div>`;
 if(s.phase==='answer'){updateCountdown();document.getElementById('answer')?.focus({preventScroll:true});}
}
function updateCountdown(){const s=app.room?.state,el=document.getElementById('countdown');if(!s||s.phase!=='answer'||!el)return;const sec=Math.max(0,Math.ceil((s.deadline*1000-Date.now())/1000));el.textContent=`00:${String(sec).padStart(2,'0')}`;el.classList.toggle('urgent',sec<=10);}
function connectRoom(code,token){closeSocket();stopPolling();app.mode='room';app.room={code,token,state:null};urlParam('room',code);screen.innerHTML=`<div class="panel narrow center"><h2>Maça bağlanılıyor...</h2><p class="helper">Oda: ${esc(code)}</p></div>`;
 const seq=++app.connectSeq;
 function connect(){if(seq!==app.connectSeq||app.mode!=='room')return;
  const protocol=location.protocol==='https:'?'wss':'ws';const ws=new WebSocket(`${protocol}://${location.host}/ws/rooms/${enc(code)}?token=${enc(token)}&session=${enc(app.session)}`);app.socket=ws;
  ws.onmessage=(event)=>{if(seq!==app.connectSeq)return;const msg=JSON.parse(event.data);if(msg.type==='state'){app.room.state=msg;renderRoom();}else if(msg.type==='error')toast(msg.message);};
  ws.onclose=(e)=>{if(seq!==app.connectSeq||app.mode!=='room')return;if(e.code===1008){toast('Oda erişim bilgisi geçersiz.');goHome();return;}toast('Bağlantı koptu, tekrar bağlanılıyor...');setTimeout(connect,1800);};
  ws.onerror=()=>{};
 }
 connect();app.pingInterval=setInterval(updateCountdown,160);
}
function tournamentInvite(t){return `${location.origin}/?turnuva=${enc(t.code)}`;}
function renderTournament(){if(!app.tournament||!app.tournament.state)return;app.mode='tournament';const t=app.tournament.state;
 const rounds=t.rounds.map((list,i)=>`<section class="bracket-round"><h3>${i===t.rounds.length-1&&list.length===1?'FINAL':`${i+1}. AŞAMA`}</h3>${list.map(match=>`<div class="bracket-match">${match.players.map(p=>`<div class="bracket-line ${p===match.winner?'winner':''}"><span>${esc(p)}</span><small>${match.winner?(p===match.winner?'✓ KAZANDI':'ELENDİ'):'BEKLİYOR'}</small></div>`).join('')}</div>`).join('')}</section>`).join('');
 screen.innerHTML=`<div class="arena-top"><div><span class="overline">🏆 ELEME ŞAMPİYONASI</span><h2 style="font-size:25px;margin:0">Turnuva · ${esc(t.code)}</h2></div><span class="pill ${t.status==='finished'?'gold':''}">${t.status==='lobby'?'OYUNCULAR BEKLENİYOR':t.status==='active'?'DEVAM EDİYOR':'BİTTİ'}</span></div>
 <div class="panel"><div class="panel-header"><div><span class="eyebrow">${t.players.length} / ${t.size} OYUNCU</span><h2 style="margin-top:9px">${t.status==='lobby'?'Turnuva lobisi':t.status==='finished'?'Şampiyon belli oldu!':'Turnuva ağacı'}</h2></div>${t.status==='finished'?'<span style="font-size:30px">🏆</span>':''}</div>
 ${t.status==='lobby'?`<p class="helper">Turnuva ${t.size} kişiye ulaşınca otomatik başlayacak. Davet bağlantısını paylaş.</p><div class="lobby-code center">${esc(t.code)}</div><button class="btn block" data-action="copy-tournament">↗ TURNUVA DAVETİNİ KOPYALA</button><div class="tournament-users">${t.players.map(n=>`<span class="tournament-user">● ${esc(n)}</span>`).join('')}</div>`:''}
 ${t.status==='active'?`<p class="helper">Eşleşmeler tamamlandıkça kazananlar otomatik sonraki tura yükselir.</p>${t.my_match?`<button class="btn block gold" data-action="play-tournament">⚔ SIRADAKİ MAÇINA GİR →</button>`:`<div class="pill">Eşleşmeni bekliyorsun veya elendin.</div>`}`:''}
 ${t.status==='finished'?`<div class="result-hero"><div class="champion">🏆</div><span class="overline">TURNUVA ŞAMPİYONU</span><div class="win-name">${esc(t.champion)}</div></div>`:''}
 ${t.rounds.length?`<div class="tournament-grid">${rounds}</div>`:''}</div><div class="center" style="margin-top:20px"><button class="btn ghost small" data-action="home">← ANA SAYFAYA DÖN</button></div>`;
}
async function loadTournament(code,token){closeSocket();stopPolling();app.mode='tournament';app.tournament={code,token,state:null};urlParam('turnuva',code);screen.innerHTML='<div class="panel narrow center"><h2>Turnuva yükleniyor...</h2></div>';
 async function refresh(){if(app.mode!=='tournament'||!app.tournament||app.tournament.code!==code)return;try{const state=await api(`/api/tournaments/${enc(code)}?token=${enc(token)}`);if(app.mode==='tournament'){app.tournament.state=state;renderTournament();}}catch(err){toast(err.message);}}
 await refresh();app.tournamentInterval=setInterval(refresh,2400);
}
async function handleClick(button){const action=button.dataset.action;try{
 if(action==='home'){goHome();return;}
 if(action==='show-register'){renderAuth('register');return;}
 if(action==='show-login'){renderAuth('login');return;}
 if(action==='logout'){await api('/api/auth/logout',{method:'POST'});localStorage.removeItem('of_session');app.session='';app.user=null;app.name='';closeSocket();stopPolling();urlParam();renderAuth();return;}
 if(action==='create-room'){const data=await api('/api/rooms',{method:'POST'});localStorage.setItem(`of_room_${data.code}`,data.token);connectRoom(data.code,data.token);return;}
 if(action==='join-room-open'){renderJoin('room');return;}
 if(action==='join-tournament-open'){renderJoin('tournament');return;}
 if(action==='join-room'||action==='join-tournament'){
 const code=document.getElementById('join-code')?.value.trim().toUpperCase();if(!code||code.length!==6){toast('6 karakterli davet kodunu gir.');return;}
 if(action==='join-room'){const data=await api(`/api/rooms/${enc(code)}/join`,{method:'POST'});localStorage.setItem(`of_room_${code}`,data.token);connectRoom(code,data.token);}
 else{const data=await api(`/api/tournaments/${enc(code)}/join`,{method:'POST'});localStorage.setItem(`of_tournament_${code}`,data.token);await loadTournament(code,data.token);}return;
 }
 if(action==='create-tournament'){renderTournamentCreate();return;}
 if(action==='confirm-tournament'){const size=Number(document.getElementById('tournament-size')?.value);const data=await api('/api/tournaments',{method:'POST',body:JSON.stringify({size})});localStorage.setItem(`of_tournament_${data.code}`,data.token);await loadTournament(data.code,data.token);return;}
 if(action==='choose'){if(!app.socket||app.socket.readyState!==WebSocket.OPEN){toast('Sunucuyla bağlantı kurulamadı.');return;}app.socket.send(JSON.stringify({type:'choose',club:button.dataset.club}));return;}
 if(action==='copy-room'||action==='copy-tournament'){
 const link=action==='copy-room'?`${location.origin}/?room=${enc(app.room.code)}`:tournamentInvite(app.tournament);
 try{await navigator.clipboard.writeText(link);toast('Davet bağlantısı kopyalandı!');}catch{window.prompt('Bağlantıyı kopyala:',link);}return;
 }
 if(action==='back-to-tournament'){const code=app.room?.state?.tournament;const token=localStorage.getItem(`of_tournament_${code}`);if(!code||!token){toast('Turnuva bilgisi bulunamadı.');return;}await loadTournament(code,token);return;}
 if(action==='play-tournament'){const code=app.tournament?.state?.my_match;if(!code)return;const token=app.tournament.token;connectRoom(code,token);return;}
}catch(err){toast(err.message||'Bir hata oluştu.');}}
document.addEventListener('click',(event)=>{const button=event.target.closest('[data-action]');if(button)handleClick(button);});
document.addEventListener('submit',(event)=>{if(event.target.id==='auth-form'){event.preventDefault();doAuth().catch(err=>toast(err.message));return;}if(event.target.id==='answer-form'){event.preventDefault();const text=document.getElementById('answer')?.value.trim();if(!text){toast('Futbolcu adını yaz.');return;}if(!app.socket||app.socket.readyState!==WebSocket.OPEN){toast('Bağlantı kurulamadı.');return;}app.socket.send(JSON.stringify({type:'answer',name:text}));document.getElementById('answer').value='';document.getElementById('answer').focus();}});
document.addEventListener('input',(event)=>{if(event.target.id==='club-search'){const q=event.target.value.toLocaleLowerCase('tr-TR');document.querySelectorAll('.club-btn').forEach(b=>{b.hidden=!b.dataset.club.toLocaleLowerCase('tr-TR').includes(q);});}});
async function boot(){try{app.config=await api('/api/config');}catch{toast('Sunucuya ulaşılamadı.');}
 if(app.session){try{app.user=await api('/api/auth/me');app.name=app.user.username;}catch{app.session='';localStorage.removeItem('of_session');}}
 if(!app.user){renderAuth();return;}
 try{await resumeInvite();}catch(err){toast(err.message);goHome();}
}
boot();
