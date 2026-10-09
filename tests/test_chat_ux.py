"""UX wiring assertions: messaging, answer reveal, and crest name flow."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def test_chat_interface_exists_and_messages_escape_html():
    js=(ROOT/'static'/'app.js').read_text(encoding='utf8')
    assert "function renderMessages()" in js
    assert "function renderChat()" in js
    assert "function refreshChat()" in js
    assert "function sendChat()" in js
    assert 'data-action="messages"' in js
    assert 'data-action="chat"' in js
    assert 'chatMessagesHtml' in js
    assert 'esc(m.body)' in js
    assert "if(event.target.id==='dm-form')" in js

def test_club_text_separate_from_crest():
    js=(ROOT/'static'/'app.js').read_text(encoding='utf8')
    css=(ROOT/'static'/'styles.css').read_text(encoding='utf8')
    assert js.count('class="club-name"')==2
    assert '.club-grid .club-btn .club-name' in css
    assert '.club-grid .club-btn .club-emblem' in css
    assert 'position:static' in css

def test_silent_round_when_no_common_players():
    js=(ROOT/'static'/'app.js').read_text(encoding='utf8')
    assert "if(event?.kind!=='timeout'||!list.length)return ''" in js
    assert 'Veritabanımızda bu iki takımda' not in js
