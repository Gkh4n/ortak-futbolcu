import asyncio
import uuid
import pytest
from fastapi.testclient import TestClient
from game import Match, PLAYER_NAMES, CLUBS, valid_player_for_pair
from server import app, ROOMS, TOURNAMENTS
import stats


def _account(client):
    name = 'p'+uuid.uuid4().hex[:14]
    out = client.post('/api/auth/register', json={'username':name,'password':'StrongPass123'}).json()
    return out, {'Authorization':'Bearer '+out['token']}


def test_round_eleven_ends_in_draw():
    m=Match()
    teams=CLUBS[:11]
    for number,club in enumerate(teams,1):
        assert m.choose(0,club)=='waiting'
        assert m.choose(1,club)=='same'
        assert m.advance()==(number==11)
    assert m.phase=='finished'
    assert m.round_number==11
    assert m.overtime and m.winner is None and m.finish_reason=='draw'
    assert m.scores==[0,0]


def test_win_in_eighth_round_and_forfeit():
    m=Match()
    for club in CLUBS[:7]:
        m.choose(0,club);m.choose(1,club);m.advance()
    assert m.round_number==8 and m.overtime
    assert m.choose(0,'Real Madrid')=='waiting'
    assert m.choose(1,'Barcelona')=='answer'
    assert m.answer(1,'Ronaldo')=='Ronaldo Nazário'
    assert m.advance() and m.winner==1
    assert m.finish_reason=='normal'
    n=Match()
    n.forfeit(0)
    assert n.phase=='finished' and n.scores==[0,3] and n.winner==1
    with pytest.raises(ValueError): n.forfeit(1)


def test_contextual_names_and_expanded_pool():
    assert len(PLAYER_NAMES)>=220 and len(CLUBS)>=80
    assert valid_player_for_pair('Ronaldo','Real Madrid','Barcelona')=='Ronaldo Nazário'
    assert valid_player_for_pair('Cristiano Ronaldo','Real Madrid','Barcelona') is None
    assert valid_player_for_pair('Ronaldo','Real Madrid','Juventus')=='Cristiano Ronaldo'
    assert valid_player_for_pair('Gabriel','Barcelona','Arsenal')=='Gabriel Jesus'
    assert valid_player_for_pair('Gabriel Jesus','Barcelona','Arsenal')=='Gabriel Jesus'


def test_record_once_public_profiles_leaderboard_and_forfeit():
    with TestClient(app) as client:
        a,ha=_account(client);b,hb=_account(client)
        roominfo=client.post('/api/rooms',headers=ha).json()
        code=roominfo['code']
        client.post(f'/api/rooms/{code}/join',headers=hb)
        assert client.post(f'/api/rooms/{code}/forfeit',headers=ha).json()['score']==[0,3]
        state=ROOMS[code].match
        assert state.winner==1 and state.finish_reason=='forfeit'
        assert client.post(f'/api/rooms/{code}/forfeit',headers=ha).json()['status']=='already-finished'
        assert stats.record_match(code,ROOMS[code].players,state) is False
        profa=client.get('/api/users/'+a['username']+'/profile',headers=hb).json()
        profb=client.get('/api/users/'+b['username']+'/profile',headers=ha).json()
        assert (profa['played'],profa['losses'],profa['points'])==(1,1,0)
        assert (profb['played'],profb['wins'],profb['points'])==(1,1,3)
        assert profa['history'][0]['reason']=='forfeit'
        assert profb['history'][0]['opponent']==a['username']
        leaders=client.get('/api/leaderboard',headers=ha).json()['players']
        assert any(x['username']==b['username'] and x['points']>=3 for x in leaders)


def test_draw_persists_and_tournament_rematches():
    with TestClient(app) as client:
        a,ha=_account(client);b,hb=_account(client)
        roomdata=client.post('/api/rooms',headers=ha).json()
        code=roomdata['code'];client.post(f'/api/rooms/{code}/join',headers=hb)
        room=ROOMS[code]
        for club in CLUBS[:11]:
            room.match.choose(0,club);room.match.choose(1,club);room.match.advance()
        assert stats.record_match(code,room.players,room.match)
        pa=client.get('/api/users/'+a['username']+'/profile',headers=ha).json()
        pb=client.get('/api/users/'+b['username']+'/profile',headers=hb).json()
        assert pa['draws']==pb['draws']==1 and pa['points']==pb['points']==1
        leader=client.get('/api/leaderboard',headers=ha).json()
        assert leader['rules']=={'win':3,'draw':1,'loss':0}

        tinfo=client.post('/api/tournaments',headers=ha,json={'size':4}).json()
        tcode=tinfo['code']; tc=TOURNAMENTS[tcode]
        for _ in range(3):
            u,h=_account(client);client.post(f'/api/tournaments/{tcode}/join',headers=h)
        old=tc.rounds[0][0]['code']
        asyncio.run(tc.record_result(old,None))
        changed=tc.rounds[0][0]['code']
        assert changed!=old and tc.status=='active'
        assert tc.rounds[0][0]['replays']==1 and ROOMS[changed].match.round_number==1
