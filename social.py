"""Persistent friends, friend requests and inbox; authenticated actions only."""
import secrets
import time
from accounts import _connection


def _init(db):
    db.execute('''CREATE TABLE IF NOT EXISTS friend_links (
        user_low TEXT NOT NULL REFERENCES users(id),
        user_high TEXT NOT NULL REFERENCES users(id),
        status TEXT NOT NULL,
        requested_by TEXT NOT NULL REFERENCES users(id),
        updated_at BIGINT NOT NULL,
        PRIMARY KEY (user_low, user_high))''')
    db.execute('''CREATE TABLE IF NOT EXISTS social_notifications (
        id TEXT PRIMARY KEY,
        recipient TEXT NOT NULL REFERENCES users(id),
        sender TEXT NOT NULL REFERENCES users(id),
        category TEXT NOT NULL,
        room_code TEXT,
        unread INTEGER NOT NULL DEFAULT 1,
        created_at BIGINT NOT NULL)''')


def _pair(a, b):
    if a == b:
        raise ValueError('Kendine arkadaşlık isteği gönderemezsin.')
    return tuple(sorted((a, b)))


def _notification(db, recipient, sender, category, room_code=None):
    nid = f'{time.time_ns():020d}{secrets.token_hex(3)}'
    db.execute('INSERT INTO social_notifications (id,recipient,sender,category,room_code,unread,created_at) VALUES (?,?,?,?,?,1,?)',
               (nid,recipient,sender,category,room_code,int(time.time())))
    return nid


def find_users(user_id, term):
    term = (term or '').strip()
    if len(term) < 2 or len(term) > 20:
        return []
    # Escape LIKE wildcards; only registered username chars are allowed for search.
    if not all(c.isascii() and (c.isalnum() or c == '_') for c in term):
        return []
    with _connection() as db:
        _init(db)
        rows = db.execute('''SELECT id, username FROM users
            WHERE username_key LIKE ? AND id<>? ORDER BY username_key LIMIT 15''',
                          (term.lower()+'%',user_id)).fetchall()
        res=[]
        for row in rows:
            a,b=_pair(user_id,row['id'])
            link=db.execute('SELECT status,requested_by FROM friend_links WHERE user_low=? AND user_high=?',(a,b)).fetchone()
            status = 'none'
            if link:
                if link['status']=='accepted': status='friend'
                elif link['status']=='pending': status='sent' if link['requested_by']==user_id else 'received'
            res.append({'id':row['id'],'username':row['username'],'status':status})
        return res


def send_request(user_id, target_id):
    a,b=_pair(user_id,target_id)
    with _connection() as db:
        _init(db)
        user=db.execute('SELECT username FROM users WHERE id=?',(target_id,)).fetchone()
        if not user: raise ValueError('Kullanıcı bulunamadı.')
        link=db.execute('SELECT status, requested_by FROM friend_links WHERE user_low=? AND user_high=?',(a,b)).fetchone()
        if link and link['status']=='accepted': raise ValueError('Zaten arkadaşsınız.')
        if link and link['status']=='pending':
            raise ValueError('Bu kullanıcıyla bekleyen bir arkadaşlık isteği var.')
        db.execute('''INSERT INTO friend_links (user_low,user_high,status,requested_by,updated_at)
                VALUES (?,?,?,?,?) ON CONFLICT (user_low,user_high) DO UPDATE SET
                status='pending', requested_by=excluded.requested_by, updated_at=excluded.updated_at''',
                (a,b,'pending',user_id,int(time.time())))
        _notification(db,target_id,user_id,'friend_request')
        return {'ok': True,'target_id':target_id}


def respond_request(user_id, sender_id, accept):
    a,b=_pair(user_id,sender_id)
    with _connection() as db:
        _init(db)
        link=db.execute('SELECT status,requested_by FROM friend_links WHERE user_low=? AND user_high=?',(a,b)).fetchone()
        if not link or link['status']!='pending' or link['requested_by']!=sender_id:
            raise ValueError('Yanıtlanabilecek bir arkadaşlık isteği bulunamadı.')
        if accept:
            db.execute('UPDATE friend_links SET status=?, updated_at=? WHERE user_low=? AND user_high=?',
                       ('accepted',int(time.time()),a,b))
            _notification(db,sender_id,user_id,'friend_accepted')
        else:
            db.execute('DELETE FROM friend_links WHERE user_low=? AND user_high=?',(a,b))
        db.execute("UPDATE social_notifications SET unread=0 WHERE recipient=? AND sender=? AND category='friend_request'",(user_id,sender_id))
        return {'ok':True,'accepted':bool(accept),'other_id':sender_id}


def is_friend(user_id, other_id):
    a,b=_pair(user_id,other_id)
    with _connection() as db:
        _init(db)
        item=db.execute('SELECT 1 FROM friend_links WHERE user_low=? AND user_high=? AND status=?',(a,b,'accepted')).fetchone()
        return item is not None


def friends_and_requests(user_id):
    with _connection() as db:
        _init(db)
        links=db.execute('SELECT user_low,user_high,status,requested_by FROM friend_links WHERE user_low=? OR user_high=?',(user_id,user_id)).fetchall()
        people=[]; incoming=[]; outgoing=[]
        for link in links:
            other=link['user_high'] if link['user_low']==user_id else link['user_low']
            row=db.execute('SELECT id,username FROM users WHERE id=?',(other,)).fetchone()
            if not row: continue
            person={'id':row['id'],'username':row['username']}
            if link['status']=='accepted':people.append(person)
            elif link['status']=='pending':(outgoing if link['requested_by']==user_id else incoming).append(person)
        key=lambda u:u['username'].lower()
        return {'friends':sorted(people,key=key),'incoming':sorted(incoming,key=key),'outgoing':sorted(outgoing,key=key)}


def notifications(user_id):
    with _connection() as db:
        _init(db)
        rows=db.execute('''SELECT n.id,n.category,n.room_code,n.unread,n.created_at,u.username AS sender_name,u.id AS sender_id
          FROM social_notifications n JOIN users u ON n.sender=u.id
          WHERE n.recipient=? ORDER BY n.id DESC LIMIT 40''',(user_id,)).fetchall()
        return [{'id':r['id'],'category':r['category'],'room_code':r['room_code'],
                 'unread':bool(r['unread']),'created_at':r['created_at'],
                 'sender_name':r['sender_name'],'sender_id':r['sender_id']} for r in rows]


def mark_read(user_id):
    with _connection() as db:
        _init(db)
        db.execute('UPDATE social_notifications SET unread=0 WHERE recipient=?',(user_id,))
    return {'ok':True}


def invite_friend(user_id, friend_id, code):
    if not is_friend(user_id,friend_id): raise ValueError('Yalnızca arkadaşlarını davet edebilirsin.')
    with _connection() as db:
        _init(db)
        _notification(db,friend_id,user_id,'game_invite',code)
    return {'ok':True,'recipient_id':friend_id,'room_code':code}
