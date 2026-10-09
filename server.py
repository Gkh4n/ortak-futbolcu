"""Zero-build FastAPI server for realtime pair-matching and elimination brackets.
Run: python server.py
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
import os
import secrets
import string
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Header, Depends, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
import uvicorn

from game import CLUBS, PLAYER_NAMES, Match
import accounts
import social
import stats

ROOT = Path(__file__).parent
app = FastAPI(title='Ortak Futbolcu MVP', docs_url='/api/docs')
app.mount('/static', StaticFiles(directory=ROOT / 'static'), name='static')

ROOMS: dict[str, 'Room'] = {}
TOURNAMENTS: dict[str, 'Tournament'] = {}
CODE_SYMBOLS = string.ascii_uppercase + string.digits
ANSWER_SECONDS = 11
RESULT_SECONDS = 2.3


def unique_code(existing: dict, length: int = 6) -> str:
    while True:
        code = ''.join(secrets.choice(CODE_SYMBOLS) for _ in range(length))
        if code not in existing:
            return code


def new_token() -> str:
    return secrets.token_urlsafe(24)


class Credentials(BaseModel):
    username: str = Field(min_length=3, max_length=20)
    password: str = Field(min_length=8, max_length=128)


def auth_token(authorization: str | None = Header(default=None)):
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(401, 'Önce giriş yapmalısın.')
    user = accounts.identify(authorization.removeprefix('Bearer '))
    if not user:
        raise HTTPException(401, 'Oturum süresi doldu. Yeniden giriş yap.')
    return user


class TournamentRequest(BaseModel):
    size: int = 4


@dataclass
class Player:
    token: str
    name: str
    user_id: str
    socket: WebSocket | None = None


@dataclass
class Room:
    code: str
    players: list[Player] = field(default_factory=list)
    match: Match | None = None
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    timer_task: asyncio.Task | None = None
    next_task: asyncio.Task | None = None
    last_attempt: dict[int, float] = field(default_factory=dict)
    tournament_code: str | None = None

    def index(self, token: str) -> int | None:
        for i, p in enumerate(self.players):
            if secrets.compare_digest(p.token, token):
                return i
        return None

    def public_state(self, player_idx: int) -> dict:
        m = self.match
        return {
            'type': 'state', 'code': self.code,
            'phase': 'lobby' if not m else m.phase,
            'me': player_idx,
            'players': [{'name': p.name, 'online': p.socket is not None,
                         'ready': bool(m and i in m.picks)} for i, p in enumerate(self.players)],
            'round': m.round_number if m else 1,
            'overtime': m.overtime if m else False,
            'scores': list(m.scores) if m else [0, 0],
            'used': sorted(m.used_clubs) if m else [],
            # No opponent choice leaks while choosing.
            'my_pick': m.picks.get(player_idx) if m and m.phase == 'choose' else None,
            'clubs': list(m.pair) if m and m.phase in ('answer', 'result') and m.pair else (
                m.event.get('clubs') if m and m.phase == 'result' else None),
            'event': dict(m.event) if m else {},
            'deadline': m.timeout_at if m else None,
            'my_answered': player_idx in m.attempted if m else False,
            'answers_submitted': len(m.attempted) if m else 0,
            'winner': m.winner if m else None,
            'tournament': self.tournament_code,
        }

    async def broadcast(self) -> None:
        for i, player in enumerate(self.players):
            if player.socket:
                try:
                    await player.socket.send_json(self.public_state(i))
                except (RuntimeError, WebSocketDisconnect, OSError):
                    player.socket = None

    async def schedule_advance(self) -> None:
        if self.next_task:
            self.next_task.cancel()
        self.next_task = asyncio.create_task(self._advance_after_delay())

    async def _advance_after_delay(self) -> None:
        try:
            await asyncio.sleep(RESULT_SECONDS)
            async with self.lock:
                if not self.match or self.match.phase != 'result':
                    return
                ended = self.match.advance()
                self.last_attempt.clear()
                await self.broadcast()
                if ended:
                    await self.finish_match()
        except asyncio.CancelledError:
            pass

    async def finish_match(self) -> None:
        """Persist once and advance the bracket. Invoked under room lock."""
        if not self.match or self.match.phase != 'finished':
            return
        stats.record_match(self.code, self.players, self.match, self.tournament_code)
        if self.tournament_code:
            tournament = TOURNAMENTS.get(self.tournament_code)
            if tournament:
                winner_token = self.players[self.match.winner].token if self.match.winner is not None else None
                await tournament.record_result(self.code, winner_token)

    def schedule_timeout(self) -> None:
        if self.timer_task:
            self.timer_task.cancel()
        self.timer_task = asyncio.create_task(self._timeout_after_delay())

    async def _timeout_after_delay(self) -> None:
        try:
            await asyncio.sleep(ANSWER_SECONDS)
            async with self.lock:
                if self.match and self.match.phase == 'answer' and self.match.timeout_at and time.time() >= self.match.timeout_at - .1:
                    self.match.timeout()
                    await self.broadcast()
                    await self.schedule_advance()
        except asyncio.CancelledError:
            pass


@dataclass
class Tournament:
    code: str
    size: int
    players: list[Player] = field(default_factory=list)
    rounds: list[list[dict]] = field(default_factory=list)
    status: str = 'lobby'
    champion: str | None = None

    def token_allowed(self, token: str) -> bool:
        return any(secrets.compare_digest(p.token, token) for p in self.players)

    def name_of(self, token: str | None) -> str | None:
        return next((p.name for p in self.players if p.token == token), None)

    def spawn_round(self, tokens: list[str]) -> None:
        round_matches: list[dict] = []
        for j in range(0, len(tokens), 2):
            pair = tokens[j:j + 2]
            code = unique_code(ROOMS)
            members = [next(p for p in self.players if p.token == x) for x in pair]
            ROOMS[code] = Room(code=code, players=[Player(p.token, p.name, p.user_id) for p in members], match=Match(), tournament_code=self.code)
            round_matches.append({'code': code, 'players': pair, 'winner': None})
        self.rounds.append(round_matches)

    def start(self) -> None:
        if self.status != 'lobby' or len(self.players) != self.size:
            raise ValueError('Turnuva henüz dolmadı.')
        self.status = 'active'
        self.spawn_round([p.token for p in self.players])

    async def record_result(self, room_code: str, winner_token: str | None) -> None:
        if self.status != 'active' or not self.rounds:
            return
        current = self.rounds[-1]
        item = next((m for m in current if m['code'] == room_code), None)
        if item is None or item['winner'] is not None:
            return
        if winner_token is None:
            # A drawn match *ends* at round 11 and yields 1 point to each.
            # Knockout bracket cannot eliminate fairly on a draw: start a separate rematch.
            new_code = unique_code(ROOMS)
            old_room = ROOMS[room_code]
            ROOMS[new_code] = Room(code=new_code,
                players=[Player(p.token, p.name, p.user_id) for p in old_room.players],
                match=Match(), tournament_code=self.code)
            item['code'] = new_code
            item['replays'] = item.get('replays', 0) + 1
            return
        if winner_token not in item['players']:
            return
        item['winner'] = winner_token
        if all(m['winner'] is not None for m in current):
            winners = [m['winner'] for m in current]
            if len(winners) == 1:
                self.status = 'finished'
                self.champion = winners[0]
            else:
                self.spawn_round(winners)

    def public_state(self, token: str) -> dict:
        if not self.token_allowed(token):
            raise HTTPException(403, 'Turnuva erişimi reddedildi.')
        my_match = None
        for matches in reversed(self.rounds):
            for match in matches:
                if token in match['players'] and match['winner'] is None:
                    my_match = match['code']
                    break
            if my_match:
                break
        return {
            'code': self.code, 'size': self.size, 'status': self.status,
            'players': [p.name for p in self.players], 'mine': self.name_of(token),
            'rounds': [[{
                'room': m['code'],
                'players': [self.name_of(x) for x in m['players']],
                'winner': self.name_of(m['winner']), 'replays': m.get('replays', 0)
            } for m in matches] for matches in self.rounds],
            'my_match': my_match,
            'champion': self.name_of(self.champion),
        }


@app.middleware('http')
async def security_headers(req: Request, call_next):
    response = await call_next(req)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Cache-Control'] = 'no-store' if req.url.path.startswith('/api/') else 'no-cache'
    return response


@app.get('/')
async def home():
    return FileResponse(ROOT / 'static' / 'index.html')


@app.get('/api/health')
async def health():
    return {'ok': True}


@app.get('/api/config')
async def config():
    return {'clubs': CLUBS, 'player_count': len(PLAYER_NAMES), 'answer_seconds': ANSWER_SECONDS}


@app.post('/api/auth/register')
async def create_account(data: Credentials):
    try:
        return accounts.register(data.username, data.password)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from None


@app.post('/api/auth/login')
async def enter_account(data: Credentials):
    try:
        return accounts.login(data.username, data.password)
    except ValueError as exc:
        raise HTTPException(401, str(exc)) from None


@app.get('/api/auth/me')
async def my_account(user=Depends(auth_token)):
    return user


@app.get('/api/users/{username}/profile')
async def get_user_profile(username: str, user=Depends(auth_token)):
    if not 3 <= len(username) <= 20:
        raise HTTPException(400, 'Geçersiz kullanıcı adı.')
    profile = stats.user_profile(username)
    if not profile:
        raise HTTPException(404, 'Kullanıcı profili bulunamadı.')
    return profile


@app.get('/api/leaderboard')
async def leaderboard(user=Depends(auth_token)):
    return {'rules': {'win':3,'draw':1,'loss':0}, 'players':stats.standings()}


@app.post('/api/auth/logout')
async def leave_account(authorization: str | None = Header(default=None)):
    if authorization and authorization.startswith('Bearer '):
        accounts.logout(authorization.removeprefix('Bearer '))
    return {'ok': True}


# Social notifications are persisted in PostgreSQL and fanned out via WebSocket
# to every active signed-in device of the recipient.
SOCIAL_CONNECTIONS: dict[str, set[WebSocket]] = {}


async def push_social(user_id: str) -> None:
    sockets = SOCIAL_CONNECTIONS.get(user_id)
    if not sockets:
        return
    payload = {'type': 'social', 'notifications': social.notifications(user_id),
               'relationships': social.friends_and_requests(user_id)}
    for ws in list(sockets):
        try:
            await ws.send_json(payload)
        except Exception:
            sockets.discard(ws)


class FriendTarget(BaseModel):
    user_id: str = Field(min_length=16, max_length=64)


class FriendDecision(FriendTarget):
    accept: bool


@app.get('/api/users/search')
async def search_users(q: str = '', user=Depends(auth_token)):
    return {'results': social.find_users(user['id'], q)}


@app.get('/api/social')
async def get_social(user=Depends(auth_token)):
    return {'relationships': social.friends_and_requests(user['id']),
            'notifications': social.notifications(user['id'])}


@app.post('/api/social/requests')
async def send_friend_request(data: FriendTarget, user=Depends(auth_token)):
    try:
        result = social.send_request(user['id'], data.user_id)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from None
    await push_social(data.user_id)
    await push_social(user['id'])
    return result


@app.post('/api/social/respond')
async def respond_friend_request(data: FriendDecision, user=Depends(auth_token)):
    try:
        result = social.respond_request(user['id'], data.user_id, data.accept)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from None
    await push_social(data.user_id)
    await push_social(user['id'])
    return result


@app.post('/api/social/read')
async def read_social(user=Depends(auth_token)):
    result = social.mark_read(user['id'])
    await push_social(user['id'])
    return result


@app.post('/api/social/invite')
async def invite_to_room(data: FriendTarget, user=Depends(auth_token)):
    try:
        # Invitations must create real playable 1v1 rooms and link the inviter.
        if not social.is_friend(user['id'], data.user_id):
            raise ValueError('Yalnızca arkadaşlarını maça davet edebilirsin.')
        code, token = unique_code(ROOMS), new_token()
        ROOMS[code] = Room(code, [Player(token, user['username'], user['id'])])
        social.invite_friend(user['id'], data.user_id, code)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from None
    await push_social(data.user_id)
    return {'code': code, 'token': token}


@app.websocket('/ws/social')
async def social_websocket(ws: WebSocket, session: str = ''):
    user = accounts.identify(session)
    if not user:
        await ws.close(code=1008)
        return
    await ws.accept()
    user_id = user['id']
    SOCIAL_CONNECTIONS.setdefault(user_id, set()).add(ws)
    try:
        await push_social(user_id)
        while True:
            await ws.receive_text()  # ping messages; no unauthenticated writes
            if not accounts.identify(session):
                await ws.close(code=1008)
                return
    except (WebSocketDisconnect, RuntimeError):
        pass
    finally:
        SOCIAL_CONNECTIONS.get(user_id, set()).discard(ws)
        if not SOCIAL_CONNECTIONS.get(user_id):
            SOCIAL_CONNECTIONS.pop(user_id, None)


@app.post('/api/rooms')
async def create_room(user=Depends(auth_token)):
    code, token = unique_code(ROOMS), new_token()
    ROOMS[code] = Room(code, [Player(token, user['username'], user['id'])])
    return {'code': code, 'token': token}


@app.post('/api/rooms/{code}/join')
async def join_room(code: str, user=Depends(auth_token)):
    code = code.upper()
    room = ROOMS.get(code)
    if not room:
        raise HTTPException(404, 'Oda bulunamadı.')
    async with room.lock:
        if room.tournament_code:
            raise HTTPException(403, 'Turnuva maçına yalnızca eşleşen oyuncular katılabilir.')
        existing = next((p for p in room.players if p.user_id == user['id']), None)
        if existing:
            return {'code': code, 'token': existing.token}
        if len(room.players) >= 2:
            raise HTTPException(409, 'Oda dolu.')
        token = new_token()
        room.players.append(Player(token, user['username'], user['id']))
        room.match = Match()
        await room.broadcast()
    return {'code': code, 'token': token}


@app.post('/api/rooms/{code}/forfeit')
async def forfeit_room(code: str, user=Depends(auth_token)):
    room = ROOMS.get(code.upper())
    if not room:
        raise HTTPException(404, 'Maç odası bulunamadı.')
    async with room.lock:
        idx = next((i for i,p in enumerate(room.players) if p.user_id == user['id']), None)
        if idx is None:
            raise HTTPException(403, 'Bu maçın oyuncusu değilsin.')
        if not room.match or len(room.players) < 2:
            return {'ok':True, 'status':'lobby-left'}
        if room.match.phase == 'finished':
            return {'ok':True, 'status':'already-finished'}
        room.match.forfeit(idx)
        if room.timer_task:
            room.timer_task.cancel()
        if room.next_task:
            room.next_task.cancel()
        await room.broadcast()
        await room.finish_match()
        return {'ok':True, 'status':'forfeit', 'winner':room.players[1-idx].name,'score':room.match.scores}


@app.get('/api/rooms/{code}/state')
async def room_state(code: str, token: str, user=Depends(auth_token)):
    room = ROOMS.get(code.upper())
    if not room or room.index(token) is None or room.players[room.index(token)].user_id != user['id']:
        raise HTTPException(403, 'Odaya erişilemiyor.')
    return room.public_state(room.index(token))


@app.websocket('/ws/rooms/{code}')
async def room_websocket(ws: WebSocket, code: str, token: str, session: str = ""):
    room = ROOMS.get(code.upper())
    idx = room.index(token) if room else None
    user = accounts.identify(session)
    if idx is None or not user or room.players[idx].user_id != user['id']:
        await ws.close(code=1008)
        return
    await ws.accept()
    async with room.lock:
        previous = room.players[idx].socket
        if previous and previous != ws:
            try:
                await previous.close(code=1000)
            except Exception:
                pass
        room.players[idx].socket = ws
        await room.broadcast()
    try:
        while True:
            message = await ws.receive_json()
            if not accounts.identify(session):
                await ws.close(code=1008)
                return
            async with room.lock:
                m = room.match
                if not m:
                    await ws.send_json({'type': 'error', 'message': 'Rakip bekleniyor.'})
                    continue
                action = message.get('type') if isinstance(message, dict) else None
                try:
                    if action == 'choose':
                        club = message.get('club')
                        if not isinstance(club, str):
                            raise ValueError('Takım seçimi geçersiz.')
                        result = m.choose(idx, club)
                        await room.broadcast()
                        if result == 'same':
                            await room.schedule_advance()
                        elif result == 'answer':
                            m.timeout_at = time.time() + ANSWER_SECONDS
                            room.schedule_timeout()
                            await room.broadcast()
                    elif action == 'answer':
                        if m.phase == 'answer' and m.timeout_at and time.time() >= m.timeout_at:
                            m.timeout()
                            await room.broadcast()
                            await room.schedule_advance()
                            continue
                        answer = message.get('name', '')
                        try:
                            m.answer(idx, answer)
                        except ValueError as exc:
                            # The first incorrect answer consumes the player's turn.
                            # Broadcast the lock and close a round early when both miss.
                            if m.phase == 'answer' and idx in m.attempted:
                                if len(m.attempted) == 2:
                                    m.timeout()
                                    if room.timer_task: room.timer_task.cancel()
                                    await room.broadcast()
                                    await room.schedule_advance()
                                else:
                                    await room.broadcast()
                            raise exc
                        if room.timer_task:
                            room.timer_task.cancel()
                        await room.broadcast()
                        await room.schedule_advance()
                    else:
                        raise ValueError('Bilinmeyen işlem.')
                except ValueError as exc:
                    await ws.send_json({'type': 'error', 'message': str(exc)})
    except (WebSocketDisconnect, RuntimeError):
        pass
    finally:
        async with room.lock:
            # An older socket must not clear a more recent reconnection.
            if room.players[idx].socket is ws:
                room.players[idx].socket = None
                await room.broadcast()


@app.post('/api/tournaments')
async def create_tournament(data: TournamentRequest, user=Depends(auth_token)):
    if data.size not in (4, 8, 16):
        raise HTTPException(400, 'Turnuva 4, 8 veya 16 kişilik olmalı.')
    code, token = unique_code(TOURNAMENTS), new_token()
    TOURNAMENTS[code] = Tournament(code, data.size, [Player(token, user['username'], user['id'])])
    return {'code': code, 'token': token}


@app.post('/api/tournaments/{code}/join')
async def join_tournament(code: str, user=Depends(auth_token)):
    tournament = TOURNAMENTS.get(code.upper())
    if not tournament:
        raise HTTPException(404, 'Turnuva bulunamadı.')
    existing = next((p for p in tournament.players if p.user_id == user['id']), None)
    if existing:
        return {'code': tournament.code, 'token': existing.token}
    if tournament.status != 'lobby' or len(tournament.players) >= tournament.size:
        raise HTTPException(409, 'Turnuva dolmuş veya başlamış.')
    token = new_token()
    tournament.players.append(Player(token, user['username'], user['id']))
    if len(tournament.players) == tournament.size:
        tournament.start()
    return {'code': tournament.code, 'token': token}


@app.get('/api/tournaments/{code}')
async def get_tournament(code: str, token: str, user=Depends(auth_token)):
    tournament = TOURNAMENTS.get(code.upper())
    if not tournament:
        raise HTTPException(404, 'Turnuva bulunamadı.')
    if not any(p.token == token and p.user_id == user['id'] for p in tournament.players):
        raise HTTPException(403, 'Bu turnuvaya erişimin yok.')
    return tournament.public_state(token)


if __name__ == '__main__':
    uvicorn.run(app, host=os.environ.get('HOST', '0.0.0.0'), port=int(os.environ.get('PORT', '8000')))
