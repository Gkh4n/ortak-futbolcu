"""Accepted friend requests must not show actionable stale notifications."""
import uuid
from fastapi.testclient import TestClient
from server import app

def new_account(client):
    name='fn'+uuid.uuid4().hex[:12]
    data=client.post('/api/auth/register',json={'username':name,'password':'testPassword42'}).json()
    return data, {'Authorization':'Bearer '+data['token']}

def test_accepted_request_notification_stays_historical_but_not_actionable():
    with TestClient(app) as c:
        alice,ha=new_account(c);bob,hb=new_account(c)
        r=c.post('/api/social/requests',headers=ha,json={'user_id':bob['user_id']})
        assert r.status_code==200
        notice=c.get('/api/social',headers=hb).json()['notifications'][0]
        assert notice['category']=='friend_request'
        assert notice['request_status']=='pending'
        response=c.post('/api/social/respond',headers=hb,json={'user_id':alice['user_id'],'accept':True})
        assert response.status_code==200
        accepted=c.get('/api/social',headers=hb).json()
        stale=next(n for n in accepted['notifications'] if n['category']=='friend_request' and n['sender_id']==alice['user_id'])
        assert stale['request_status']=='accepted'
        assert not stale['unread']
        assert alice['user_id'] in {x['id'] for x in accepted['relationships']['friends']}
        again=c.post('/api/social/respond',headers=hb,json={'user_id':alice['user_id'],'accept':True})
        assert again.status_code==200
        assert again.json()['already_friends'] is True
        assert c.get('/api/social',headers=hb).json()['notifications'][0]['request_status']=='accepted'

def test_closed_request_not_actionable():
    with TestClient(app) as c:
        a,ha=new_account(c);b,hb=new_account(c)
        c.post('/api/social/requests',headers=ha,json={'user_id':b['user_id']})
        assert c.post('/api/social/respond',headers=hb,json={'user_id':a['user_id'],'accept':False}).status_code==200
        notices=c.get('/api/social',headers=hb).json()['notifications']
        assert any(n['category']=='friend_request' and n['sender_id']==a['user_id'] and n['request_status']=='closed' for n in notices)
        assert c.post('/api/social/respond',headers=hb,json={'user_id':a['user_id'],'accept':True}).status_code==400

def test_mobile_chat_shell_is_keyboard_safe():
    from pathlib import Path
    root=Path(__file__).resolve().parents[1]
    html=(root/'static/index.html').read_text()
    js=(root/'static/app.js').read_text()
    css=(root/'static/styles.css').read_text()
    assert 'interactive-widget=resizes-content' in html
    assert 'window.scrollTo({top:0' in js
    assert 'dm-header' in js and 'dm-empty-state' in js
    assert 'body[data-mode="chat"] .footer{display:none}' in css
    assert 'body[data-mode="chat"] .dm-messages' in css
    assert 'body[data-mode="chat"] .dm-input' in css
