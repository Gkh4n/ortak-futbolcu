'use strict';
const screen = document.getElementById('screen');
const toastEl = document.getElementById('toast');
const app = {
  mode: 'home', config: {clubs:[],player_count:0,answer_seconds:11},
  name: '', user:null, session: localStorage.getItem('of_session') || '', room:null, tournament:null,
  socket:null, pingInterval:null, tournamentInterval:null, connectSeq:0, socialSocket:null, socialTimer:null, social:null, searchResults:[], backDialog:false, profile:null,
};
function esc(x){return String(x ?? '').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
function urlParam(key, val){const u=new URL(location.href);u.search='';if(key)u.searchParams.set(key,val);history.replaceState({game:true},'',u.pathname+u.search);}
function matchInProgress(){return app.mode==='room' && app.room?.state && !['finished','lobby'].includes(app.room.state.phase);}
function showLeave(){
  if(document.getElementById('leave-overlay'))return;
  const match=matchInProgress(), home=app.mode==='home'||app.mode==='auth';
  const heading=match?'Maçtan ayrılacak mısın?':home?'Oyundan çıkmak istiyor musun?':'Ana ekrana dön';
  const detail=match?'Maçtan ayrılırsan rakibin hükmen 3–0 kazanacak. Bu sonuç profilinde mağlubiyet olarak kaydedilecek.':
    home?'Ortak Futbolcu uygulamasından çıkmak istediğine emin misin?':'Bu sayfadan ayrılmak istiyor musun?';
  const overlay=document.createElement('div');overlay.id='leave-overlay';overlay.className='leave-overlay';
  overlay.innerHTML=`<div class="leave-dialog" role="dialog" aria-modal="true"><span class="overline">ARENA</span><h2>${heading}</h2><p>${detail}</p><div class="form-row"><button class="btn secondary" data-action="cancel-leave">VAZGEÇ</button><button class="btn" data-action="confirm-leave">${match?'HÜKMEN AYRIL':home?'ÇIKIŞ':'GERİ DÖN'}</button></div></div>`;
  document.body.append(overlay);
}
function exitOverlay(){document.getElementById('leave-overlay')?.remove();}
function goBack(){
 if(document.getElementById('leave-overlay')){exitOverlay();return;}
 if(app.mode==='room'){
   if(app.room?.state?.phase==='finished'&&app.room?.state?.tournament){
     const code=app.room.state.tournament, token=localStorage.getItem(`of_tournament_${code}`);
     if(token){loadTournament(code,token);return;}
   }
   if(app.room?.state?.phase==='finished'||app.room?.state?.phase==='lobby'){goHome();return;}
   showLeave();return;
 }
 if(app.mode==='home'||app.mode==='auth'){showLeave();return;}
 if(app.mode==='profile'){
   if(app.profileReturnMode==='friends'){fetchSocial().then(renderFriends).catch(()=>goHome());return;}
   if(app.profileReturnMode==='leaderboard'){showLeaderboard().catch(()=>goHome());return;}
 }
 goHome();
}
// Browser and Android back both follow the current in-app screen.
history.replaceState({gameBase:true},'',location.href);
history.pushState({game:true},'',location.href);
window.addEventListener('popstate',()=>{history.pushState({game:true},'',location.href);goBack();});
window.ortakBack=()=>{goBack();return true;};
function toast(message){toastEl.textContent=message;toastEl.style.display='block';clearTimeout(toast.timer);toast.timer=setTimeout(()=>toastEl.style.display='none',3500);}
function currentName(){return app.user?.username || null;}
async function api(path,opts={}){const response=await fetch(path,{...opts,headers:{'Content-Type':'application/json',...(app.session ? {Authorization:`Bearer ${app.session}`} : {}),...(opts.headers||{})}});let data;try{data=await response.json();}catch{throw Error('Sunucuya ulaşılamadı.');}if(!response.ok)throw Error(typeof data.detail==='string'?data.detail:'Bir işlem başarısız oldu.');return data;}
function enc(v){return encodeURIComponent(v);}
function badgeLabel(code){return esc(code.split(/\s+/).map(x=>x[0]).slice(0,2).join('').toLocaleUpperCase('tr-TR'));}
function clubShield(name,kind=''){return `<div class="crest ${kind}"><strong>${badgeLabel(name)}</strong><small>${esc(name)}</small></div>`;}
function stopPolling(){if(app.tournamentInterval){clearInterval(app.tournamentInterval);app.tournamentInterval=null;}}
function closeSocket(){app.connectSeq++;if(app.socket){const s=app.socket;app.socket=null;s.onclose=null;s.close();}if(app.pingInterval){clearInterval(app.pingInterval);app.pingInterval=null;}}
function goHome(){exitOverlay();closeSocket();stopPolling();app.room=null;app.tournament=null;app.mode='home';urlParam();app.user?renderHome():renderAuth();}

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
 toast(`Hoş geldin, ${data.username}!`);connectSocial();await resumeInvite();
}
async function resumeInvite(){
 const params=new URLSearchParams(location.search),room=params.get('room')?.toUpperCase(),tournament=params.get('turnuva')?.toUpperCase();
 if(room){const data=await api(`/api/rooms/${enc(room)}/join`,{method:'POST'});localStorage.setItem(`of_room_${room}`,data.token);connectRoom(room,data.token);}
 else if(tournament){const data=await api(`/api/tournaments/${enc(tournament)}/join`,{method:'POST'});localStorage.setItem(`of_tournament_${tournament}`,data.token);await loadTournament(tournament,data.token);}
 else renderHome();
}

function noticeCount(){return app.social?.notifications?.filter(n=>n.unread).length||0;}
function friendCount(){return app.social?.relationships?.friends?.length||0;}
function friendsButton(){return `<button class="friend-shortcut" data-action="friends" aria-label="Arkadaşlar ve bildirimler">♧ ARKADAŞLAR <span class="friend-count">${friendCount()}</span>${noticeCount()?`<span class="notice-count">${noticeCount()}</span>`:''}</button>`;}
function renderHome(){app.mode='home';document.body.dataset.mode='home';screen.innerHTML=`
  <section class="home-hero">
    <span class="overline">⚡ FUTBOL BİLGİNİ KONUŞTUR</span>
    <h1>İKİ TAKIM.<br><span class="accent">TEK İSİM.</span><br>BÜYÜK ZAFER.</h1>
    <p>Takımını gizlice seç. Ortak futbolcuyu ilk sen bul, düelloyu kazan!</p>
    <div class="hero-actions"><button class="btn" data-action="create-room">⚔ 1V1 ODA KUR <span>→</span></button><button class="btn secondary" data-action="create-tournament">🏆 TURNUVA KUR <span>→</span></button></div>
  </section>
  <section class="home-main-actions">
    <div class="welcome-card"><span class="avatar big-avatar">${esc(app.name.charAt(0).toUpperCase())}</span><div class="profile-head"><span class="overline">OYUNCU PROFİLİ</span><h2>Hoş geldin, ${esc(app.name)}!</h2><p>Bir arkadaşına meydan oku veya turnuvaya katıl.</p></div></div>
    <div class="home-profile-actions"><button class="btn secondary" data-action="my-profile">◉ PROFİLİM</button><button class="btn secondary" data-action="leaderboard">🏆 PUAN DURUMU</button></div>
    <button class="btn friend-card-btn" data-action="friends"><span>♧</span><span><strong>Arkadaşlarım</strong><small>${friendCount()} arkadaş · İstekler ve davetler</small></span><span class="friend-alert">${noticeCount()?noticeCount()+' yeni':'→'}</span></button>
    <div class="home-join-row"><button class="btn secondary" data-action="join-room-open">⌁ ODA KODUYLA KATIL</button><button class="btn secondary" data-action="join-tournament-open">🏆 TURNUVAYA KATIL</button></div>
    <div class="home-mini-stats"><span>⚔ 1V1 DÜELLO</span><span>♛ 4 / 8 / 16</span><span>⏱ 11 SANİYE</span></div>
    <button class="logout-link" data-action="logout">↪ Hesaptan çık</button>
  </section>`;
}
function profileResultBadge(v){return v==='win'?'GALİBİYET':v==='draw'?'BERABERLİK':'MAĞLUBİYET';}
async function showProfile(username){
  const origin=app.mode;
  const data=await api('/api/users/'+enc(username)+'/profile');
  app.profileReturnMode=origin==='friends'||origin==='leaderboard'?origin:'home';
  app.mode='profile';app.profile=data;urlParam();document.body.dataset.mode='profile';
  screen.innerHTML=`<section class="profile-page"><button class="back" data-action="back">← GERİ</button>
  <div class="panel profile-hero"><div class="avatar big-avatar">${esc(data.username[0].toUpperCase())}</div><div><span class="overline">OYUNCU KARTI</span><h1>${esc(data.username)}</h1><p>Toplam <strong>${data.points}</strong> lig puanı</p></div></div>
  <div class="profile-stats"><div><strong>${data.played}</strong><small>MAÇ</small></div><div><strong>${data.wins}</strong><small>GALİBİYET</small></div><div><strong>${data.draws}</strong><small>BERABERLİK</small></div><div><strong>${data.losses}</strong><small>MAĞLUBİYET</small></div></div>
  <div class="panel"><span class="overline">MAÇ GEÇMİŞİ</span>${data.history.length?data.history.map(m=>`<div class="history-row"><span class="result-mark ${esc(m.result)}">${profileResultBadge(m.result)}</span><span class="history-other">${esc(m.opponent)}</span><strong>${m.for} – ${m.against}</strong><small>${m.reason==='forfeit'?'Hükmen':''}</small></div>`).join(''):'<p class="helper">Henüz tamamlanmış maç bulunmuyor.</p>'}</div>
  <p class="helper center">Galibiyet 3 · Beraberlik 1 · Mağlubiyet 0 puan</p></section>`;
}
async function showLeaderboard(){
  const data=await api('/api/leaderboard');app.mode='leaderboard';urlParam();document.body.dataset.mode='leaderboard';
  screen.innerHTML=`<section class="standings-page"><button class="back" data-action="back">← GERİ</button><span class="overline">CANLI SIRALAMA</span><h1>PUAN <span class="accent">DURUMU</span></h1><p class="helper">Galibiyet 3 · Beraberlik 1 · Mağlubiyet 0 puan</p><div class="panel table-scroll"><table class="league-table"><thead><tr><th>#</th><th>OYUNCU</th><th>O</th><th>G</th><th>B</th><th>M</th><th>PUAN</th></tr></thead><tbody>${data.players.map((p,i)=>`<tr><td>${i+1}</td><td><button class="profile-name-link" data-action="profile" data-name="${esc(p.username)}">${esc(p.username)}</button></td><td>${p.played}</td><td>${p.wins}</td><td>${p.draws}</td><td>${p.losses}</td><td><strong>${p.points}</strong></td></tr>`).join('')||'<tr><td colspan="7">Henüz tamamlanmış maç yok.</td></tr>'}</tbody></table></div></section>`;
}
function notificationContent(n){
  const name=esc(n.sender_name);
  if(n.category==='friend_request')return `<strong>${name}</strong> sana arkadaşlık isteği gönderdi.`;
  if(n.category==='friend_accepted')return `<strong>${name}</strong> arkadaşlık isteğini kabul etti.`;
  return `<strong>${name}</strong> seni 1v1 maça davet etti.`;
}
function renderFriends(){app.mode='friends';document.body.dataset.mode='friends';const d=app.social||{relationships:{friends:[],incoming:[],outgoing:[]},notifications:[]};
  const r=d.relationships; const search=app.searchResults||[];
  screen.innerHTML=`<section class="social-page"><button class="back" data-action="home">← ANA SAYFA</button><div class="social-heading"><div><span class="overline">SOSYAL ARENA</span><h1>Arkadaşlarım <span class="accent">${r.friends.length}</span></h1><p class="helper">Kullanıcı adını arat, arkadaş ekle ve tek dokunuşla düelloya çağır.</p></div><div class="social-icon">♧</div></div>
  <div class="panel social-panel"><span class="overline">OYUNCU ARA</span><form id="friend-search-form" class="social-search"><input class="input" id="friend-search" placeholder="Kullanıcı adı yaz..." minlength="2" maxlength="20" value="${esc(app.searchTerm||'')}" autocomplete="off"><button type="submit" class="btn">ARA</button></form><div id="search-results">${search.map(u=>socialUserRow(u)).join('')||'<p class="helper">En az 2 harf yazarak oyuncu ara.</p>'}</div></div>
  ${r.incoming.length?`<div class="panel social-panel"><span class="overline">GELEN İSTEKLER · ${r.incoming.length}</span>${r.incoming.map(u=>`<div class="social-row"><span class="avatar">${esc(u.username[0])}</span><div class="social-identity"><strong>${esc(u.username)}</strong><small>Arkadaşlık isteği</small></div><button class="btn small" data-action="accept-friend" data-id="${esc(u.id)}">KABUL</button><button class="btn ghost small" data-action="decline-friend" data-id="${esc(u.id)}">✕</button></div>`).join('')}</div>`:''}
  <div class="panel social-panel"><span class="overline">ARKADAŞ LİSTESİ · ${r.friends.length}</span>${r.friends.length?r.friends.map(u=>`<div class="social-row"><span class="avatar">${esc(u.username[0])}</span><div class="social-identity"><button class="profile-name-link" data-action="profile" data-name="${esc(u.username)}">${esc(u.username)}</button><small>Arkadaşın</small></div><button class="btn small" data-action="invite-friend" data-id="${esc(u.id)}">⚔ DAVET ET</button></div>`).join(''):'<p class="helper">Henüz arkadaşın yok. Yukarıdan kullanıcı arayabilirsin.</p>'}</div>
  ${r.outgoing.length?`<div class="panel social-panel"><span class="overline">YANIT BEKLENENLER</span>${r.outgoing.map(u=>`<div class="social-row"><span class="avatar">${esc(u.username[0])}</span><div class="social-identity"><strong>${esc(u.username)}</strong><small>Arkadaşlık isteği gönderildi</small></div><span class="pill">BEKLİYOR</span></div>`).join('')}</div>`:''}
  <div class="panel social-panel"><div class="panel-header"><div><span class="overline">BİLDİRİMLER</span><p class="helper">İstek ve maç davetlerin burada saklanır.</p></div>${noticeCount()?'<button class="btn small secondary" data-action="read-notifications">OKUNDU</button>':''}</div>
  ${(typeof Notification!=='undefined'&&Notification.permission==='default'&&typeof AndroidBridge==='undefined')?'<button class="btn small secondary" data-action="enable-notifications">🔔 SİSTEM BİLDİRİMLERİNİ AÇ</button>':''}${d.notifications.length?d.notifications.slice(0,24).map(n=>`<div class="social-row notification-row ${n.unread?'is-unread':''}"><span class="avatar">${n.category==='game_invite'?'⚔':'♧'}</span><div class="social-identity"><span>${notificationContent(n)}</span><small>${new Date(n.created_at*1000).toLocaleString('tr-TR')}</small></div>${n.category==='game_invite'&&n.room_code?`<button class="btn small" data-action="open-invite" data-code="${esc(n.room_code)}">KATIL</button>`:n.category==='friend_request'?`<button class="btn small" data-action="accept-friend" data-id="${esc(n.sender_id)}">KABUL</button>`:''}</div>`).join(''):'<p class="helper">Henüz bildirim bulunmuyor.</p>'}</div></section>`;
}
function socialUserRow(u){const status=u.status;return `<div class="social-row"><span class="avatar">${esc(u.username[0])}</span><div class="social-identity"><button class="profile-name-link" data-action="profile" data-name="${esc(u.username)}">${esc(u.username)}</button><small>${status==='friend'?'Arkadaşın':status==='sent'?'İstek gönderildi':status==='received'?'Sana istek gönderdi':'Oyuncu'}</small></div>${status==='none'?`<button class="btn small" data-action="add-friend" data-id="${esc(u.id)}">+ EKLE</button>`:status==='received'?`<button class="btn small" data-action="accept-friend" data-id="${esc(u.id)}">KABUL</button>`:`<span class="pill">${status==='friend'?'ARKADAŞ':'BEKLİYOR'}</span>`}</div>`;}
async function fetchSocial(){if(!app.session)return;app.social=await api('/api/social');if(app.mode==='friends')renderFriends();else if(app.mode==='home')renderHome();}
function closeSocial(){if(app.socialSocket){app.socialSocket.onclose=null;app.socialSocket.close();app.socialSocket=null;}if(app.socialTimer){clearInterval(app.socialTimer);app.socialTimer=null;}}
function connectSocial(){closeSocial();if(!app.session)return;let cancelled=false;
  async function connect(){if(!app.session||cancelled)return;const proto=location.protocol==='https:'?'wss':'ws';
    const ws=new WebSocket(`${proto}://${location.host}/ws/social?session=${enc(app.session)}`);app.socialSocket=ws;
    ws.onmessage=(ev)=>{let data;try{data=JSON.parse(ev.data);}catch{return;}if(data.type!=='social')return;
      const previous=new Set((app.social?.notifications||[]).map(n=>n.id));
      const fresh=(data.notifications||[]).filter(n=>n.unread&&!previous.has(n.id));
      app.social={notifications:data.notifications,relationships:data.relationships};
      for(const item of fresh){toast(item.category==='game_invite'?`${item.sender_name} seni maça davet etti!`:`${item.sender_name} yeni bildirim gönderdi!`);
        if(typeof AndroidBridge!=='undefined'&&AndroidBridge.notify)AndroidBridge.notify(item.category==='game_invite'?'Maç daveti':'Arkadaşlık bildirimi',item.sender_name+' • Ortak Futbolcu');
        else if(typeof Notification!=='undefined'&&Notification.permission==='granted'&&document.visibilityState!=='visible'){new Notification('Ortak Futbolcu',{body:item.sender_name+' sana bildirim gönderdi.'});}}
      if(app.mode==='friends')renderFriends();else if(app.mode==='home')renderHome();
    };
    ws.onclose=()=>{if(!cancelled&&app.session)setTimeout(connect,2500);};
  }
  connect();fetchSocial().catch(()=>{});
  app.socialTimer=setInterval(()=>{if(app.socialSocket?.readyState===WebSocket.OPEN)app.socialSocket.send('ping');else fetchSocial().catch(()=>{});},25000);
}
function renderJoin(kind,known=''){const tournament=kind==='tournament';app.mode='join';app.joinKind=kind;screen.innerHTML=`<div class="panel narrow"><button class="back" data-action="home">← ANA SAYFA</button><span class="overline">${tournament?'🏆 TURNUVAYA KATIL':'⚔ DÜELLOYA KATIL'}</span><h2>${tournament?'Turnuva kodunu gir':'Oda kodunu gir'}</h2><p class="helper">${tournament?'Arkadaşlarının bulunduğu turnuvaya dahil ol.':'Rakibinle aynı odaya bağlan ve maç başlasın.'}</p>
  <div class="form-group"><label>${tournament?'TURNUVA':'ODA'} KODU</label><input class="input" id="join-code" maxlength="6" placeholder="ÖR: A8B3N9" style="text-transform:uppercase;letter-spacing:3px;font-weight:900" value="${esc(known)}"></div>
  <button class="btn block" data-action="${tournament?'join-tournament':'join-room'}">KATIL →</button></div>`;}
function renderTournamentCreate(){app.mode='create-tournament';screen.innerHTML=`<div class="panel narrow"><button class="back" data-action="home">← ANA SAYFA</button><span class="overline">🏆 ELEME ARENASI</span><h2>Yeni turnuva oluştur</h2><p class="helper">Oyuncu sayısı dolunca turnuva otomatik başlar. Her eşleşme farklı bir 7 turluk maçtır.</p>
<div class="form-group"><label>OYUNCU SAYISI</label><select id="tournament-size" class="input"><option value="4">4 Oyuncu · 2 Yarı Final + Final</option><option value="8">8 Oyuncu · Çeyrek Final + Yarı Final + Final</option><option value="16">16 Oyuncu · Son 16 + Final</option></select></div><button class="btn block" data-action="confirm-tournament">TURNUVAYI OLUŞTUR →</button></div>`;}
function readyPlayers(state){return `<div class="players-grid compact-ready">${state.players.map((p,i)=>`<div class="player-mini"><div class="avatar">${esc(p.name.charAt(0).toUpperCase())}</div><div><strong>${esc(p.name)}${i===state.me?' (Sen)':''}</strong><small class="${p.ready?'ready':p.online?'':'offline'}">${p.ready?'✓ Hazır':p.online?'● Çevrim içi':'○ Çevrimdışı'}</small></div></div>`).join('')}</div>`;}
function usedBlock(state){return `<details class="used-panel"><summary>⊘ &nbsp; Elenen takımlar <strong>${state.used.length}</strong><span>⌄</span></summary>${state.used.length?`<div class="used-list">${state.used.map(n=>`<span class="used-item">${esc(n)}</span>`).join('')}</div>`:'<p class="helper">Henüz elenen takım yok.</p>'}</details>`;}
function matchClub(name){return `<div class="match-club"><div class="club-badge large-badge">${badgeLabel(name)}</div><strong>${esc(name)}</strong></div>`;}
function renderRoom(){if(!app.room||!app.room.state)return;app.mode='room';document.body.dataset.mode='room';const s=app.room.state,me=s.me;
const label=s.overtime?`UZATMA · ${s.round}/11`:`TUR ${s.round} / 7`;
const progress=s.overtime?'':`<div class="round-progress">${Array.from({length:7},(_,i)=>`<div class="round-dot ${i<s.round-1?'done':i===s.round-1?'current':''}"></div>`).join('')}</div>`;
let board='';
if(s.phase==='lobby'){
board=`<div class="center room-lobby"><div class="lobby-illustration">⚔</div><span class="overline">MAÇ ODASI HAZIR</span><h2>Rakibini bekliyorsun</h2><div class="lobby-code">${esc(s.code)}</div><p class="helper">Arkadaşına davet bağlantısını gönder veya arkadaş listesinden davet et.</p><button class="btn block" data-action="copy-room">⌁ DAVET BAĞLANTISINI KOPYALA</button><button class="btn secondary block" data-action="friends">♧ ARKADAŞLARIM</button></div>`;
}else if(s.phase==='choose'){
const chosen=Boolean(s.my_pick),free=app.config.clubs.filter(c=>!s.used.includes(c));
board=`<div class="arena-intro"><span class="overline">GİZLİ TAKIM SEÇİMİ</span><h2>${chosen?'Seçimin kilitlendi':'Bir takım seç'}</h2><p class="helper">${chosen?`<strong>${esc(s.my_pick)}</strong> seçtin. Rakibinin seçimi bekleniyor.`:'Rakibin hangi kulübü seçtiğini göremezsin. Elenen takımlar kullanılamaz.'}</p></div>${readyPlayers(s)}
${!chosen?`<input class="input club-search" type="search" id="club-search" placeholder="⌕  Takım ara..." autocomplete="off"><div class="club-grid">${free.map(c=>`<button class="club-btn" data-action="choose" data-club="${esc(c)}"><span class="club-emblem">${badgeLabel(c)}</span><span>${esc(c)}</span></button>`).join('')}</div>`:`<div class="waiting-pick"><span class="spinner-ring"></span><strong>Rakip bekleniyor</strong><small>İki seçim tamamlanınca soru açılır.</small></div>`}
${s.event?.kind==='invalid'?`<p class="helper warning-text">⚠ ${esc(s.event.detail)}</p>`:''}`;
}else if(s.phase==='answer'){
const [a,b]=s.clubs||['',''];const done=!!s.my_answered;
board=`<div class="duel-stage"><div class="two-crests">${matchClub(a)}<div class="vs">VS</div>${matchClub(b)}</div><div class="timer-wrap"><span class="timer-icon">◷</span><div class="timer" id="countdown">${String(app.config.answer_seconds).padStart(2,'0')}</div><span class="timer-label">SANİYE</span></div><h2 class="answer-title">Ortak oyuncu <span class="accent">kim?</span></h2><p class="helper center">${done?'Tek cevap hakkını kullandın. Rakibini bekle.':'11 saniye • Tek cevap hakkın var!'}</p>
${!done?`<form id="answer-form" class="answer-bar"><input id="answer" class="input" placeholder="Futbolcu adı" autocomplete="off" maxlength="100" aria-label="Futbolcu adı" enterkeyhint="send"><button type="submit" class="btn block">➤ GÖNDER</button></form>`:`<div class="submitted-box">✓ CEVABIN GÖNDERİLDİ</div>`}</div>`;
}else if(s.phase==='result'){
const e=s.event||{},same=e.kind==='same';board=`<div class="result-hero"><div class="result-symbol ${same?'same':''}">${same?'⟷':e.kind==='point'?'✓':'⌛'}</div><span class="overline">${same?'AYNI TAKIM SEÇİLDİ':e.kind==='point'?'PUAN KAZANILDI':'PUANSIZ TUR'}</span><h2>${esc(e.headline||'Tur tamamlandı')}</h2><p>${esc(e.detail||'')}</p>${e.kind==='point'?`<span class="pill">+1 PUAN · ${esc(s.players[e.scorer]?.name||'Oyuncu')}</span>`:''}<p class="helper">Sonraki tur hazırlanıyor...</p></div>`;
}else if(s.phase==='finished'){
const won=s.winner===me,draw=s.winner===null;board=`<div class="result-hero"><div class="champion">${draw?'🤝':won?'🏆':'⚔'}</div><span class="overline">MAÇ BİTTİ</span><h2>${draw?'BERABERE!':won?'ZAFER SENİN!':'MAÇ TAMAMLANDI'}</h2><div class="win-name">${draw?'İki oyuncu da +1 lig puanı kazandı':esc(s.players[s.winner]?.name||'Oyuncu')+' kazandı'}</div>${s.event?.kind==='forfeit'?'<p>Hükmen 3–0</p>':''}<p>${s.scores[0]} — ${s.scores[1]} • ${s.round}. tur</p>${s.tournament?'<button class="btn block" data-action="back-to-tournament">TURNUVA TABLOSUNA DÖN</button>':'<button class="btn block" data-action="home">ANA SAYFA</button>'}</div>`;
}
screen.innerHTML=`<section class="game-page"><div class="game-head"><button class="leave-match" data-action="leave-match" aria-label="Maçtan çık">✕</button><div class="compact-scoreboard"><div class="score-player ${me===0?'self':''}"><span class="avatar">${esc((s.players[0]?.name||'O')[0].toUpperCase())}</span><button class="score-name profile-name-link" data-action="profile" data-name="${esc(s.players[0]?.name||'')}">${esc(s.players[0]?.name||'Bekleniyor')}</button></div><div class="score-center"><strong>${s.scores[0]} - ${s.scores[1]}</strong></div><div class="score-player right ${me===1?'self':''}"><button class="score-name profile-name-link" data-action="profile" data-name="${esc(s.players[1]?.name||'')}">${esc(s.players[1]?.name||'Rakip bekleniyor')}</button><span class="avatar">${esc((s.players[1]?.name||'R')[0].toUpperCase())}</span></div></div></div><div class="game-meta"><span class="pill ${s.overtime?'gold':''}">${esc(label)}</span><span class="room-tag">ODA · ${esc(s.code)}</span></div>${progress}<div class="game-board">${board}</div>${usedBlock(s)}<div class="room-extras"><button class="btn ghost small" data-action="copy-room">⌁ ODA BAĞLANTISINI PAYLAŞ</button>${s.tournament?'<button class="btn ghost small" data-action="back-to-tournament">🏆 TURNUVA</button>':''}</div></section>`;
if(s.phase==='answer')updateCountdown();
}
function updateCountdown(){const s=app.room?.state,el=document.getElementById('countdown');if(!s||s.phase!=='answer'||!el)return;const sec=Math.max(0,Math.ceil((s.deadline*1000-Date.now())/1000));el.textContent=String(sec).padStart(2,'0');el.classList.toggle('urgent',sec<=3);}
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
function renderTournament(){if(!app.tournament||!app.tournament.state)return;app.mode='tournament';document.body.dataset.mode='tournament';const t=app.tournament.state;
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
 if(action==='home'){if(matchInProgress()){showLeave();return;}goHome();return;}
 if(action==='back'){goBack();return;}
 if(action==='my-profile'){await showProfile(app.name);return;}
 if(action==='profile'){if(matchInProgress()){toast('Profilini maç bittikten sonra görüntüleyebilirsin.');return;}await showProfile(button.dataset.name);return;}
 if(action==='leaderboard'){await showLeaderboard();return;}
 if(action==='leave-match'){goBack();return;}
 if(action==='cancel-leave'){exitOverlay();return;}
 if(action==='confirm-leave'){
  if(matchInProgress()){
    button.disabled=true;
    try{await api('/api/rooms/'+enc(app.room.code)+'/forfeit',{method:'POST'});goHome();}
    catch(e){button.disabled=false;toast('Maçtan ayrılamadın: '+e.message);}
  }else if(app.mode==='home'||app.mode==='auth'){
    exitOverlay();
    if(typeof AndroidBridge!=='undefined'&&AndroidBridge.exitApp){AndroidBridge.exitApp();}
    else{location.replace('about:blank');}
  }else{goHome();}
  return;
 }
 if(action==='friends'){if(matchInProgress()){showLeave();return;}closeSocket();stopPolling();app.room=null;app.tournament=null;urlParam();await fetchSocial();renderFriends();return;}
 if(action==='add-friend'){await api('/api/social/requests',{method:'POST',body:JSON.stringify({user_id:button.dataset.id})});toast('Arkadaşlık isteği gönderildi!');await fetchSocial();return;}
 if(action==='accept-friend'||action==='decline-friend'){await api('/api/social/respond',{method:'POST',body:JSON.stringify({user_id:button.dataset.id,accept:action==='accept-friend'})});toast(action==='accept-friend'?'Artık arkadaşsınız!':'İstek reddedildi.');await fetchSocial();return;}
 if(action==='enable-notifications'){if(typeof Notification!=='undefined'){const result=await Notification.requestPermission();toast(result==='granted'?'Bildirimlere izin verildi.':'Bildirim izni verilmedi.');renderFriends();}return;}
 if(action==='read-notifications'){await api('/api/social/read',{method:'POST'});await fetchSocial();return;}
 if(action==='invite-friend'){const data=await api('/api/social/invite',{method:'POST',body:JSON.stringify({user_id:button.dataset.id})});localStorage.setItem(`of_room_${data.code}`,data.token);toast('Maç daveti anında gönderildi!');connectRoom(data.code,data.token);return;}
 if(action==='open-invite'){const code=button.dataset.code;const data=await api(`/api/rooms/${enc(code)}/join`,{method:'POST'});localStorage.setItem(`of_room_${code}`,data.token);await api('/api/social/read',{method:'POST'});connectRoom(code,data.token);return;}

 if(action==='show-register'){renderAuth('register');return;}
 if(action==='show-login'){renderAuth('login');return;}
 if(action==='logout'){await api('/api/auth/logout',{method:'POST'});localStorage.removeItem('of_session');app.session='';app.user=null;app.name='';closeSocket();closeSocial();stopPolling();urlParam();renderAuth();return;}
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
 if(action==='back-to-tournament'){if(matchInProgress()){showLeave();return;}const code=app.room?.state?.tournament;const token=localStorage.getItem(`of_tournament_${code}`);if(!code||!token){toast('Turnuva bilgisi bulunamadı.');return;}await loadTournament(code,token);return;}
 if(action==='play-tournament'){const code=app.tournament?.state?.my_match;if(!code)return;const token=app.tournament.token;connectRoom(code,token);return;}
}catch(err){toast(err.message||'Bir hata oluştu.');}}
document.addEventListener('click',(event)=>{const button=event.target.closest('[data-action]');if(button)handleClick(button);});
document.addEventListener('submit',(event)=>{if(event.target.id==='friend-search-form'){event.preventDefault();const term=document.getElementById('friend-search')?.value?.trim()||'';app.searchTerm=term;api('/api/users/search?q='+enc(term)).then(x=>{app.searchResults=x.results;renderFriends();}).catch(e=>toast(e.message));return;}if(event.target.id==='auth-form'){event.preventDefault();doAuth().catch(err=>toast(err.message));return;}if(event.target.id==='answer-form'){event.preventDefault();const text=document.getElementById('answer')?.value.trim();if(!text){toast('Futbolcu adını yaz.');return;}if(!app.socket||app.socket.readyState!==WebSocket.OPEN){toast('Bağlantı kurulamadı.');return;}app.socket.send(JSON.stringify({type:'answer',name:text}));const field=document.getElementById('answer');if(field){field.disabled=true;field.blur();}const submit=document.querySelector('#answer-form button[type=submit]');if(submit)submit.disabled=true;}});
document.addEventListener('input',(event)=>{if(event.target.id==='club-search'){const q=event.target.value.toLocaleLowerCase('tr-TR');document.querySelectorAll('.club-btn').forEach(b=>{b.hidden=!b.dataset.club.toLocaleLowerCase('tr-TR').includes(q);});}});
async function boot(){try{app.config=await api('/api/config');}catch{toast('Sunucuya ulaşılamadı.');}
 if(app.session){try{app.user=await api('/api/auth/me');app.name=app.user.username;}catch{app.session='';localStorage.removeItem('of_session');}}
 if(!app.user){renderAuth();return;}
 connectSocial();try{await resumeInvite();}catch(err){toast(err.message);goHome();}
}
boot();
