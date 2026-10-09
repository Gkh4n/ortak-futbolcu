"""Persistent public match histories, user profiles and 3/1/0 standings.

Recorded once per completed room. For a knockout draw, the tied match is
recorded as a draw and the bracket starts a *new match* between the same two
users; the new rematch has its own room code.
"""
import time
from accounts import _connection, _username_key


def _init(db):
    db.execute('''CREATE TABLE IF NOT EXISTS match_records (
        room_code TEXT PRIMARY KEY,
        player_a TEXT NOT NULL REFERENCES users(id),
        player_b TEXT NOT NULL REFERENCES users(id),
        score_a INTEGER NOT NULL,
        score_b INTEGER NOT NULL,
        winner_id TEXT,
        finish_reason TEXT NOT NULL,
        tournament_code TEXT,
        played_at BIGINT NOT NULL)''')
    db.execute('''CREATE TABLE IF NOT EXISTS user_stats (
        user_id TEXT PRIMARY KEY REFERENCES users(id),
        played INTEGER NOT NULL DEFAULT 0,
        wins INTEGER NOT NULL DEFAULT 0,
        draws INTEGER NOT NULL DEFAULT 0,
        losses INTEGER NOT NULL DEFAULT 0,
        points INTEGER NOT NULL DEFAULT 0)''')


def record_match(code, players, match, tournament_code=None):
    if len(players) != 2 or match.phase != 'finished':
        return False
    first, second = players
    ids = (first.user_id, second.user_id)
    winner_id = ids[match.winner] if match.winner is not None else None
    with _connection() as db:
        _init(db)
        existing = db.execute('SELECT room_code FROM match_records WHERE room_code=?', (code,)).fetchone()
        if existing:
            return False
        db.execute('''INSERT INTO match_records
            (room_code,player_a,player_b,score_a,score_b,winner_id,finish_reason,tournament_code,played_at)
            VALUES (?,?,?,?,?,?,?,?,?)''',
            (code, *ids, int(match.scores[0]), int(match.scores[1]), winner_id,
             match.finish_reason or 'normal', tournament_code, int(time.time())))
        for uid in ids:
            is_draw = winner_id is None
            win = not is_draw and winner_id == uid
            played, w, d, l, pts = (1, int(win), int(is_draw), int(not win and not is_draw),
                                     1 if is_draw else (3 if win else 0))
            db.execute('''INSERT INTO user_stats(user_id,played,wins,draws,losses,points)
                VALUES(?,?,?,?,?,?) ON CONFLICT(user_id) DO UPDATE SET
                played=user_stats.played+excluded.played,
                wins=user_stats.wins+excluded.wins,
                draws=user_stats.draws+excluded.draws,
                losses=user_stats.losses+excluded.losses,
                points=user_stats.points+excluded.points''',
                (uid, played, w, d, l, pts))
    return True


def user_profile(username):
    with _connection() as db:
        _init(db)
        user = db.execute('SELECT id,username,created_at FROM users WHERE username_key=?',
                          (_username_key(username),)).fetchone()
        if user is None:
            return None
        uid = user['id']
        stat = db.execute('SELECT played,wins,draws,losses,points FROM user_stats WHERE user_id=?',
                          (uid,)).fetchone()
        recent = db.execute('''SELECT room_code,player_a,player_b,score_a,score_b,winner_id,
                                   finish_reason,tournament_code,played_at
            FROM match_records WHERE player_a=? OR player_b=? ORDER BY played_at DESC,room_code DESC LIMIT 12''',
                            (uid,uid)).fetchall()
        entries=[]
        for m in recent:
            other_uid = m['player_b'] if uid == m['player_a'] else m['player_a']
            opponent=db.execute('SELECT username FROM users WHERE id=?',(other_uid,)).fetchone()
            a_side = uid == m['player_a']
            result = 'draw' if m['winner_id'] is None else ('win' if m['winner_id']==uid else 'loss')
            entries.append({'room':m['room_code'],'opponent':opponent['username'] if opponent else '?',
                            'for':m['score_a'] if a_side else m['score_b'],
                            'against':m['score_b'] if a_side else m['score_a'],
                            'result':result,'reason':m['finish_reason'],'date':m['played_at'],
                            'tournament':bool(m['tournament_code'])})
        return {'username':user['username'],'joined':user['created_at'],
                'played':stat['played'] if stat else 0,'wins':stat['wins'] if stat else 0,
                'draws':stat['draws'] if stat else 0,'losses':stat['losses'] if stat else 0,
                'points':stat['points'] if stat else 0,'history':entries}


def standings(limit=50):
    with _connection() as db:
        _init(db)
        rows = db.execute('''SELECT u.username,s.played,s.wins,s.draws,s.losses,s.points
            FROM user_stats s JOIN users u ON u.id=s.user_id
            ORDER BY s.points DESC,s.wins DESC,s.draws DESC,u.username_key ASC LIMIT ?''',(limit,)).fetchall()
        return [dict(row) for row in rows]
