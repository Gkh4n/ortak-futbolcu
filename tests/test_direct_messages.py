"""Private DMs persist for accepted friends; unauthorized users cannot view or write."""
import uuid
from fastapi.testclient import TestClient
from server import app
from accounts import _connection

def new_user(c):
    u='dm_'+uuid.uuid4().hex[:10]
    body=c.post('/api/auth/register',json={'username':u,'password':'examplePass123'}).json()
    return body, {'Authorization':'Bearer '+body['token']}

def test_chat_friend_only_and_persists_in_db():
    with TestClient(app) as c:
        a,ha=new_user(c);b,hb=new_user(c);stranger,hs=new_user(c)
        url='/api/chat/'+b['user_id']
        assert c.get(url,headers=ha).status_code==403
        assert c.post(url,headers=ha,json={'body':'hi'}).status_code==400
        c.post('/api/social/requests',headers=ha,json={'user_id':b['user_id']})
        c.post('/api/social/respond',headers=hb,json={'user_id':a['user_id'],'accept':True})
        with c.websocket_connect('/ws/social?session='+b['token']) as ws:
            ws.receive_json()  # initial social payload
            r=c.post(url,headers=ha,json={'body':'Selam! <script>alert(1)</script>'})
            assert r.status_code==200
            push=ws.receive_json()
            assert push['chat_unreads'][a['user_id']]==1
            assert push['notifications'][0]['category']=='message'
        assert c.get('/api/chat/'+a['user_id'],headers=hs).status_code==403
        assert c.post('/api/chat/'+a['user_id'],headers=hs,json={'body':'hello'}).status_code==400
        history=c.get('/api/chat/'+a['user_id'],headers=hb)
        assert history.status_code==200
        assert history.json()['messages'][-1]['body']=='Selam! <script>alert(1)</script>'
        assert c.get('/api/social',headers=hb).json()['chat_unreads'].get(a['user_id'],0)==0
        assert c.post(url,headers=ha,json={'body':'  '}).status_code in (400,422)
        assert c.post(url,headers=ha,json={'body':'a'*501}).status_code==422

def test_chat_isolated_between_friend_pairs():
    with TestClient(app) as c:
        a,ha=new_user(c); b,hb=new_user(c); x,hx=new_user(c)
        c.post('/api/social/requests',headers=ha,json={'user_id':b['user_id']})
        c.post('/api/social/respond',headers=hb,json={'user_id':a['user_id'],'accept':True})
        c.post('/api/chat/'+b['user_id'],headers=ha,json={'body':'Özel mesaj'})
        assert c.get('/api/chat/'+a['user_id'],headers=hx).status_code==403
        assert c.get('/api/chat/'+b['user_id'],headers=ha).json()['messages'][-1]['body']=='Özel mesaj'
