"""Club selection: same fixed sixty and genuine local crest in multiplayer + practice."""
import json
import re
from pathlib import Path
from game import FEATURED_CLUBS, CLUBS

ROOT=Path(__file__).resolve().parents[1]

def test_60_clubs_in_designer_order():
    assert len(FEATURED_CLUBS)==60
    assert len(set(FEATURED_CLUBS))==60
    assert all(c in CLUBS for c in FEATURED_CLUBS)
    assert FEATURED_CLUBS[:6]==['Real Madrid','Barcelona','Manchester United','Manchester City','Liverpool','Arsenal']

def test_each_club_has_local_svg_logo():
    js=(ROOT/'static'/'app.js').read_text(encoding='utf8')
    match=re.search(r'const TEAM_CRESTS = (\\{.*?\\});',js,flags=re.S)
    assert match, 'club-crest map not found in JS'
    logos=json.loads(match.group(1))
    assert list(logos)==FEATURED_CLUBS
    assert len(logos)==60
    for club,icon in logos.items():
        path=ROOT/'static'/icon.lstrip('/')
        assert path.exists(),f'{club}: {icon}'
        content=path.read_text(encoding='utf8')
        assert '<svg' in content and '</svg>' in content,f'{club}: malformed svg'

def test_both_team_pick_screens_use_60_team_list():
    js=(ROOT/'static'/'app.js').read_text(encoding='utf8')
    assert 'function selectionPool()' in js
    assert js.count('selectionPool().filter(c=>!s.used.includes(c))')==2
