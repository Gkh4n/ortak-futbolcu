"""Direct 1v1 supports all database clubs, while practice and tournaments keep 60."""
from game import CLUBS, FEATURED_CLUBS, Match
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def test_more_than_60_clubs_available():
    assert len(CLUBS)>60
    extra=[name for name in CLUBS if name not in FEATURED_CLUBS]
    assert len(extra)>0

def test_direct_match_allows_non_featured_clubs():
    extra=[name for name in CLUBS if name not in FEATURED_CLUBS]
    m=Match()
    assert m.choose(0,extra[0])=='waiting'
    assert m.choose(1,extra[1])=='answer'
    assert extra[0] in m.used_clubs and extra[1] in m.used_clubs

def test_full_search_and_progressive_render_in_direct_rooms():
    js=(ROOT/'static'/'app.js').read_text(encoding='utf8')
    assert "function multiplayerClubs()" in js
    assert "function updateRoomClubPicker()" in js
    assert "data-action=\"more-clubs\"" in js
    assert "const pool=s.tournament?selectionPool():multiplayerClubs()" in js
    assert "const matched=query?available.filter" in js
    assert "app.clubShowCount=60;updateRoomClubPicker()" in js
    assert "const free=selectionPool().filter(c=>!s.used.includes(c));" in js

def test_club_search_does_not_ignore_extended_roster():
    js=(ROOT/'static'/'app.js').read_text(encoding='utf8')
    assert "function clubSearchKey(value)" in js
    assert "replaceAll('ı','i')" in js
    assert "s.tournament?selectionPool():multiplayerClubs()" in js
