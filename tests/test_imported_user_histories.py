"""Regression for user-submitted missing-player file and TFF-confirmed Ömer Şişmanoğlu."""
from game import PLAYER_HISTORIES, CLUBS, PAIR_PLAYERS, valid_player_for_pair, normalize
from imported_missing_players import MISSING_HISTORIES


def test_user_file_deduped_and_new_players_added():
    assert len(MISSING_HISTORIES) == 157
    keys = [normalize(name) for name, _ in PLAYER_HISTORIES]
    assert len(keys) == len(set(keys))
    assert len(PLAYER_HISTORIES) >= 532
    assert 'Zinedine Zidane' in {n for n, _ in PLAYER_HISTORIES}
    assert 'Gianluigi Buffon' in {n for n, _ in PLAYER_HISTORIES}
    assert 'Dani Carvajal' in {n for n, _ in PLAYER_HISTORIES}


def test_omer_sismanoglu_matches_besiktas_kayserispor():
    assert 'Ömer Şişmanoğlu' in PAIR_PLAYERS[frozenset(('Beşiktaş','Kayserispor'))]
    assert valid_player_for_pair('Ömer', 'Beşiktaş', 'Kayserispor') == 'Ömer Şişmanoğlu'
    assert valid_player_for_pair('ömer şişmanoğlu','Kayserispor','Beşiktaş') == 'Ömer Şişmanoğlu'
    assert valid_player_for_pair('Sismanoglu','Kayserispor','Beşiktaş') == 'Ömer Şişmanoğlu'
    assert valid_player_for_pair('Ömer','Fenerbahçe','Galatasaray') is None


def test_source_aliases_share_single_team_id():
    assert 'West Ham United' in CLUBS
    assert 'Al Nassr' in CLUBS
    assert 'PSV' in CLUBS
    assert 'Newcastle United' in CLUBS


def test_existing_histories_are_not_replaced_by_uploaded_shorter_lists():
    assert valid_player_for_pair('roberto carlos','Palmeiras','Real Madrid') == 'Roberto Carlos'
    assert valid_player_for_pair('Ronaldo','Barcelona','Real Madrid') == 'Ronaldo Nazário'