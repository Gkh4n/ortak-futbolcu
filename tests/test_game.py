from game import Match, normalize, valid_player_for_pair, PAIR_PLAYERS


def clash(m, team):
    assert m.choose(0, team) == 'waiting'
    assert m.choose(1, team) == 'same'
    assert m.phase == 'result'
    m.advance()


def score(m, a, b, side=0, name=None):
    assert m.choose(0, a) == 'waiting'
    assert m.choose(1, b) == 'answer'
    name = name or PAIR_PLAYERS[frozenset((a,b))][0]
    assert m.answer(side, name) == name
    m.advance()


def test_same_team_skips_question_and_eliminates():
    m=Match()
    clash(m,'Real Madrid')
    assert m.round_number == 2
    assert m.scores == [0,0]
    assert m.used_clubs == {'Real Madrid'}
    try:
        m.choose(0,'Real Madrid')
    except ValueError:
        pass
    else:
        assert False, 'Eliminated club can never be picked again'


def test_three_points_wins_before_seventh():
    m=Match()
    pairs=[('Real Madrid','Fenerbahçe'),('Ajax','Barcelona'),('Inter','PSG')]
    for a,b in pairs:score(m,a,b)
    assert m.phase == 'finished'
    assert m.winner == 0
    assert m.round_number == 3


def test_seven_rounds_unequal_score_wins_even_without_three():
    m=Match()
    score(m,'Real Madrid','Fenerbahçe')
    clash(m,'Ajax');clash(m,'Barcelona');clash(m,'Chelsea')
    clash(m,'Inter');clash(m,'Juventus')
    assert m.round_number == 7
    assert m.choose(0,'PSG') == 'waiting'
    assert m.choose(1,'PSG') == 'same'
    assert m.advance() is True
    assert m.winner == 0 and m.scores == [1,0]


def test_equal_after_seven_goes_into_overtime_and_plus_one_wins():
    m=Match()
    score(m,'Real Madrid','Fenerbahçe',0)
    score(m,'Ajax','Barcelona',1)
    for team in ['Chelsea','Inter','Bayern Münih','Juventus','PSG']:
        clash(m,team)
    assert m.phase == 'choose' and m.overtime and m.round_number == 8
    score(m,'Arsenal','Liverpool',0)
    assert m.winner == 0 and m.phase == 'finished'
    assert m.scores == [2,1]


def test_no_known_overlap_still_starts_valid_round():
    m=Match()
    assert m.choose(0,'Vitória Setúbal')=='waiting'
    assert m.choose(1,'Ascoli')=='answer'
    assert m.phase=='answer'
    assert {'Vitória Setúbal','Ascoli'} <= m.used_clubs
    m.timeout()
    assert m.event['kind']=='timeout'
    assert m.event['clubs']==['Vitória Setúbal','Ascoli']
    assert m.event['revealed_players']==[]
    assert m.advance() is False
    assert m.round_number==2


def test_turkish_accents_and_surname():
    assert normalize('MESUT ÖZİL')=='mesut ozil'
    assert valid_player_for_pair('Roberto Carlos','Real Madrid','Fenerbahçe')=='Roberto Carlos'
    assert valid_player_for_pair('Özil','Real Madrid','Fenerbahçe')=='Mesut Özil'
    assert valid_player_for_pair('Ronaldo','Real Madrid','Juventus')=='Cristiano Ronaldo'
    assert valid_player_for_pair('Ronaldo','Barcelona','Inter')=='Ronaldo Nazário'
