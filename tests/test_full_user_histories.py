"""Regression: all teams in the user-supplied file must count for returning players."""
from game import PLAYER_HISTORIES, PAIR_PLAYERS, valid_player_for_pair, canonical_club, normalize
from user_supplied_histories import PLAYER_HISTORIES as USER_HISTORIES

def test_all_supplied_team_spells_are_included():
    combined = {normalize(n): set(clubs) for n,clubs in PLAYER_HISTORIES}
    missing = [(name,club) for name,clubs in USER_HISTORIES for club in clubs if canonical_club(club) not in combined.get(normalize(name),set())]
    assert not missing, f'Missing user club associations: {missing[:10]}'

def test_caner_erkin_besiktas_eyupspor():
    assert 'Caner Erkin' in PAIR_PLAYERS[frozenset(('Beşiktaş','Eyüpspor'))]
    assert valid_player_for_pair('Caner Erkin','Beşiktaş','Eyüpspor') == 'Caner Erkin'
    assert valid_player_for_pair('Caner','Beşiktaş','Eyüpspor') == 'Caner Erkin'
    assert 'Caner Erkin' in PAIR_PLAYERS[frozenset(('Fenerbahçe','Eyüpspor'))]

def test_existing_careers_enriched():
    assert valid_player_for_pair('Wesley Sneijder','Ajax','Nice') == 'Wesley Sneijder'
    assert valid_player_for_pair('Cristiano Ronaldo','Sporting CP','Al Nassr') == 'Cristiano Ronaldo'
