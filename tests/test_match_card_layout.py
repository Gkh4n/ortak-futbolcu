"""Protect duel and practice match card crests from oversized club logos."""
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]

def test_match_club_logo_separates_name_and_image():
    js=(ROOT/'static'/'app.js').read_text(encoding='utf8')
    markup=js[js.index('function matchClub(name){'):js.index('function revealedAnswers(')]
    assert 'class="match-club-crest"' in markup
    assert 'class="match-club-img"' in markup
    assert 'class="match-club-name"' in markup
    assert 'width="64" height="64"' in markup
    assert 'class="club-badge large-badge"' not in markup

def test_duel_logo_has_hard_bounds_and_overflow_clip():
    css=(ROOT/'static'/'styles.css').read_text(encoding='utf8')
    assert '.two-crests .match-club .match-club-crest' in css
    assert '.two-crests .match-club .match-club-img' in css
    assert 'max-width:64px;' in css and 'max-height:64px;' in css
    assert 'overflow:hidden;' in css
    assert '.two-crests .match-club .match-club-name' in css

def test_all_different_game_modes_share_safe_duel_markup():
    js=(ROOT/'static'/'app.js').read_text(encoding='utf8')
    assert js.count('matchClub(a)')>=2
    assert js.count('matchClub(b)')>=2
