import time
import uuid
import pytest
from fastapi.testclient import TestClient
from server import app, PRACTICES, ROOMS
from game import Match, CLUBS, PAIR_PLAYERS, PLAYER_NAMES, valid_player_for_pair


def register(client):
    username='test'+uuid.uuid4().hex[:12]
    payload=client.post('/api/auth/register', json={'username': username,'password':'somePassword123'})
    assert payload.status_code == 200
    data=payload.json()
    return data, {'Authorization': 'Bearer '+data['token']}


def test_unknown_pairs_always_accepted_reveal_none_and_elimination():
    m=Match()
    assert m.choose(0,'Vitória Setúbal')=='waiting'
    assert m.choose(1,'Ascoli')=='answer'
    assert m.phase=='answer'
    assert 'Vitória Setúbal' in m.used_clubs and 'Ascoli' in m.used_clubs
    assert 'revealed_players' not in m.event
    m.timeout()
    assert m.event['revealed_players']==[]
    m.advance()
    with pytest.raises(ValueError):m.choose(0,'Ascoli')


def test_both_pass_instant_and_reveal_only_after_ending():
    m=Match()
    m.choose(0,'Real Madrid');m.choose(1,'Barcelona')
    assert m.phase=='answer'
    assert m.pass_turn(0) is False
    with pytest.raises(ValueError):m.answer(0,'Ronaldo')
    assert m.pass_turn(1) is True
    m.timeout()
    assert m.event['kind']=='timeout'
    assert m.event['headline']=='İki oyuncu da pas geçti!'
    assert 'Ronaldo Nazário' in m.event['revealed_players']


def test_one_wrong_and_one_pass_ends_round():
    m=Match();m.choose(0,'Real Madrid');m.choose(1,'Barcelona')
    with pytest.raises(ValueError):m.answer(0,'NOT A PLAYER')
    assert m.pass_turn(1)
    m.timeout()
    assert m.scores==[0,0]


def test_new_players_and_club_order():
    assert len(PLAYER_NAMES)>=350
    assert len(CLUBS)>=300
    assert CLUBS[:6]==['Real Madrid','Barcelona','Manchester United','Manchester City','Liverpool','Arsenal']
    assert valid_player_for_pair('Salah','Trabzonspor','Liverpool')=='Mohamed Salah'
    assert valid_player_for_pair('Leão','Galatasaray','AC Milan')=='Rafael Leão'
    assert valid_player_for_pair('Ronaldo','Barcelona','Real Madrid')=='Ronaldo Nazário'


def test_practice_choose_answer_pass_timeout_and_leaderboard_isolation():
    with TestClient(app) as client:
        user, headers=register(client)
        start=client.post('/api/practice/start',headers=headers)
        assert start.status_code==200
        assert start.json()['phase']=='choose'
        picked=client.post('/api/practice/pick',headers=headers,json={'club':'Real Madrid'})
        assert picked.status_code==200
        selection=picked.json()
        assert selection['phase']=='answer'
        assert selection['clubs'][0]=='Real Madrid'
        assert selection['clubs'][1]!='Real Madrid'
        assert selection['deadline'] > time.time()
        assert selection['event']=={}
        valid=PAIR_PLAYERS[frozenset(selection['clubs'])][0]
        answer=client.post('/api/practice/answer',headers=headers,json={'name':valid})
        assert answer.status_code==200
        assert answer.json()['score']==1
        assert valid in answer.json()['event']['revealed_players']
        assert client.post('/api/practice/answer',headers=headers,json={'name':valid}).status_code==409
        next_round=client.post('/api/practice/next',headers=headers)
        assert next_round.json()['round']==2
        pick=client.post('/api/practice/pick',headers=headers,json={'club':'Barcelona'})
        assert pick.status_code==200
        passed=client.post('/api/practice/pass',headers=headers)
        assert passed.json()['phase']=='result'
        assert passed.json()['event']['revealed_players']
        assert client.post('/api/practice/pass',headers=headers).status_code==409
        profile=client.get(f'/api/users/{user["username"]}/profile',headers=headers).json()
        assert profile['played']==0 and profile['points']==0
        assert client.post('/api/practice/next',headers=headers).json()['round']==3
        pick=client.post('/api/practice/pick',headers=headers,json={'club':'Fenerbahçe'})
        assert pick.status_code==200
        obj=PRACTICES[user['user_id']]
        obj.deadline=time.time()-1
        expired=client.get('/api/practice',headers=headers)
        assert expired.json()['phase']=='result'
        assert expired.json()['event']['headline']=='Süre doldu!'
