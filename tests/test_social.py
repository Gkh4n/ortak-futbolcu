import uuid
import pytest
from fastapi.testclient import TestClient
from server import app, ROOMS
from game import Match


def account(client):
    username='p'+uuid.uuid4().hex[:13]
    data=client.post('/api/auth/register',json={'username':username,'password':'testPassword42'}).json()
    assert data['token']
    return data, {'Authorization':'Bearer '+data['token']}


def test_11_seconds_and_one_attempt_even_when_wrong():
    with TestClient(app) as c:
        assert c.get('/api/config').json()['answer_seconds']==11
    m=Match()
    assert m.choose(0,'Real Madrid')=='waiting'
    assert m.choose(1,'Fenerbahçe')=='answer'
    with pytest.raises(ValueError,match='Yanlış cevap'):
        m.answer(0,'Lionel Messi')
    assert 0 in m.attempted
    with pytest.raises(ValueError,match='tek cevap hakkını'):
        m.answer(0,'Roberto Carlos')
    assert m.answer(1,'Roberto Carlos')=='Roberto Carlos'
    assert m.scores==[0,1]


def test_two_wrong_answers_end_round_without_points():
    m=Match()
    m.choose(0,'Real Madrid');m.choose(1,'Fenerbahçe')
    for player in (0,1):
        with pytest.raises(ValueError):m.answer(player,'Dünyada olmayan oyuncu')
    assert m.attempted=={0,1}
    m.timeout()
    assert m.phase=='result' and m.scores==[0,0]
    m.advance()
    assert m.round_number==2 and not m.attempted


def test_friend_request_notification_acceptance_and_invite():
    with TestClient(app) as c:
        a,ha=account(c);b,hb=account(c);other,ho=account(c)
        results=c.get('/api/users/search',params={'q':b['username'][:5]},headers=ha).json()['results']
        assert any(x['username']==b['username'] for x in results)
        assert c.post('/api/social/invite',headers=ha,json={'user_id':b['user_id']}).status_code==400
        with c.websocket_connect('/ws/social?session='+b['token']) as social_ws:
            initial=social_ws.receive_json();assert initial['type']=='social'
            sent=c.post('/api/social/requests',headers=ha,json={'user_id':b['user_id']})
            assert sent.status_code==200
            notice=social_ws.receive_json()
            assert notice['notifications'][0]['category']=='friend_request'
            assert notice['relationships']['incoming'][0]['username']==a['username']
            assert c.post('/api/social/requests',headers=ha,json={'user_id':b['user_id']}).status_code==400
            assert c.post('/api/social/respond',headers=ho,json={'user_id':a['user_id'],'accept':True}).status_code==400
            accepted=c.post('/api/social/respond',headers=hb,json={'user_id':a['user_id'],'accept':True})
            assert accepted.status_code==200
            accepted_push=social_ws.receive_json()
            assert accepted_push['relationships']['friends'][0]['username']==a['username']
            invite=c.post('/api/social/invite',headers=ha,json={'user_id':b['user_id']})
            assert invite.status_code==200
            code=invite.json()['code'];assert code in ROOMS
            match_notice=social_ws.receive_json()
            assert match_notice['notifications'][0]['room_code']==code
            joined=c.post(f'/api/rooms/{code}/join',headers=hb)
            assert joined.status_code==200
            assert len(ROOMS[code].players)==2
            read=c.post('/api/social/read',headers=hb)
            assert read.status_code==200
            read_notice=social_ws.receive_json()
            assert not any(n['unread'] for n in read_notice['notifications'])


def test_friend_request_denied_prevents_invite():
    with TestClient(app) as c:
        a,ha=account(c);b,hb=account(c)
        c.post('/api/social/requests',headers=ha,json={'user_id':b['user_id']})
        assert c.post('/api/social/respond',headers=hb,json={'user_id':a['user_id'],'accept':False}).status_code==200
        assert c.post('/api/social/invite',headers=ha,json={'user_id':b['user_id']}).status_code==400
