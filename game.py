"""Deterministic two-player football crossover game rules.

Everything here is server-authoritative; client events cannot decide a result.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import re
import unicodedata


def normalize(value: str) -> str:
    # Unicode Turkish I/ı and diacritics; consistent between DB and answers.
    value = value.strip().replace('ı', 'i').replace('İ', 'i')
    value = unicodedata.normalize('NFKD', value)
    value = ''.join(x for x in value if not unicodedata.combining(x))
    return re.sub(r'[^a-z0-9]+', ' ', value.lower()).strip()


# Curated sample player histories: SENIOR competitive club spells only.
# For production, augment with licensed transfer-history data + verification.
PLAYER_HISTORIES: list[tuple[str, tuple[str, ...]]] = [
    ('Roberto Carlos', ('Real Madrid', 'Fenerbahçe', 'Inter')),
    ('Mesut Özil', ('Real Madrid', 'Arsenal', 'Fenerbahçe')),
    ('Nani', ('Manchester United', 'Fenerbahçe')),
    ('Robin van Persie', ('Arsenal', 'Manchester United', 'Fenerbahçe')),
    ('Fred', ('Manchester United', 'Fenerbahçe')),
    ('Altay Bayındır', ('Fenerbahçe', 'Manchester United')),
    ('Nicolas Anelka', ('Arsenal', 'Real Madrid', 'PSG', 'Liverpool', 'Manchester City', 'Fenerbahçe', 'Chelsea', 'Juventus')),
    ('Raul Meireles', ('Liverpool', 'Chelsea', 'Fenerbahçe')),
    ('Edin Džeko', ('Manchester City', 'Roma', 'Inter', 'Fenerbahçe')),
    ('Diego Ribas', ('Juventus', 'Atletico Madrid', 'Fenerbahçe')),
    ('Mauro Icardi', ('Inter', 'PSG', 'Galatasaray')),
    ('Victor Osimhen', ('Napoli', 'Galatasaray')),
    ('Hakim Ziyech', ('Ajax', 'Chelsea', 'Galatasaray')),
    ('Dries Mertens', ('Napoli', 'Galatasaray')),
    ('Juan Mata', ('Chelsea', 'Manchester United', 'Galatasaray')),
    ('Lucas Torreira', ('Arsenal', 'Atletico Madrid', 'Galatasaray')),
    ('Davinson Sánchez', ('Ajax', 'Tottenham', 'Galatasaray')),
    ('Tanguy Ndombele', ('Tottenham', 'Napoli', 'Galatasaray')),
    ('Sergio Oliveira', ('Roma', 'Galatasaray')),
    ('Fernando Muslera', ('Lazio', 'Galatasaray')),
    ('Felipe Melo', ('Juventus', 'Inter', 'Galatasaray')),
    ('Wesley Sneijder', ('Ajax', 'Real Madrid', 'Inter', 'Galatasaray')),
    ('Didier Drogba', ('Chelsea', 'Galatasaray')),
    ('Ryan Babel', ('Ajax', 'Liverpool', 'Beşiktaş', 'Galatasaray')),
    ('Cenk Tosun', ('Beşiktaş', 'Fenerbahçe')),
    ('Miralem Pjanić', ('Roma', 'Juventus', 'Barcelona', 'Beşiktaş')),
    ('Wout Weghorst', ('Beşiktaş', 'Manchester United', 'Ajax')),
    ('Dele Alli', ('Tottenham', 'Beşiktaş')),
    ('Mario Gómez', ('Bayern Münih', 'Beşiktaş')),
    ('Pepe', ('Real Madrid', 'Beşiktaş')),
    ('Vincent Aboubakar', ('Beşiktaş', 'Porto')),
    ('Anderson Talisca', ('Benfica', 'Beşiktaş', 'Fenerbahçe')),
    ('Gedson Fernandes', ('Benfica', 'Galatasaray', 'Beşiktaş')),
    ('Rafa Silva', ('Benfica', 'Beşiktaş')),
    ('Alex Oxlade-Chamberlain', ('Arsenal', 'Liverpool', 'Beşiktaş')),
    ('Michy Batshuayi', ('Chelsea', 'Borussia Dortmund', 'Fenerbahçe', 'Galatasaray')),
    ('João Mário', ('Inter', 'Benfica', 'Beşiktaş')),
    ('Sadio Mané', ('Liverpool', 'Bayern Münih')),
    ('Philippe Coutinho', ('Liverpool', 'Barcelona', 'Bayern Münih', 'Inter')),
    ('Luis Suárez', ('Ajax', 'Liverpool', 'Barcelona', 'Atletico Madrid')),
    ('Zlatan Ibrahimović', ('Ajax', 'Juventus', 'Inter', 'Barcelona', 'AC Milan', 'PSG', 'Manchester United')),
    ('Samuel Eto’o', ('Real Madrid', 'Barcelona', 'Inter', 'Chelsea')),
    ('Ronaldo Nazário', ('Barcelona', 'Inter', 'Real Madrid', 'AC Milan')),
    ('Cristiano Ronaldo', ('Manchester United', 'Real Madrid', 'Juventus')),
    ('Ángel Di María', ('Real Madrid', 'Manchester United', 'PSG', 'Juventus', 'Benfica')),
    ('Neymar', ('Barcelona', 'PSG')),
    ('Kylian Mbappé', ('PSG', 'Real Madrid')),
    ('Ousmane Dembélé', ('Borussia Dortmund', 'Barcelona', 'PSG')),
    ('Achraf Hakimi', ('Real Madrid', 'Borussia Dortmund', 'Inter', 'PSG')),
    ('Sergio Ramos', ('Real Madrid', 'PSG')),
    ('Keylor Navas', ('Real Madrid', 'PSG')),
    ('David Beckham', ('Manchester United', 'Real Madrid', 'PSG', 'AC Milan')),
    ('Kaká', ('AC Milan', 'Real Madrid')),
    ('Brahim Díaz', ('Manchester City', 'Real Madrid', 'AC Milan')),
    ('Álvaro Morata', ('Real Madrid', 'Juventus', 'Chelsea', 'Atletico Madrid', 'AC Milan', 'Galatasaray')),
    ('Gonzalo Higuaín', ('Real Madrid', 'Napoli', 'Juventus', 'AC Milan', 'Chelsea')),
    ('Fernando Torres', ('Atletico Madrid', 'Liverpool', 'Chelsea', 'AC Milan')),
    ('Diego Costa', ('Atletico Madrid', 'Chelsea')),
    ('João Félix', ('Benfica', 'Atletico Madrid', 'Chelsea', 'Barcelona', 'AC Milan')),
    ('Cesc Fàbregas', ('Arsenal', 'Barcelona', 'Chelsea')),
    ('Thierry Henry', ('Juventus', 'Arsenal', 'Barcelona')),
    ('Alexis Sánchez', ('Barcelona', 'Arsenal', 'Manchester United', 'Inter')),
    ('Pierre-Emerick Aubameyang', ('Borussia Dortmund', 'Arsenal', 'Barcelona', 'Chelsea')),
    ('İlkay Gündoğan', ('Borussia Dortmund', 'Manchester City', 'Barcelona', 'Galatasaray')),
    ('Kevin De Bruyne', ('Chelsea', 'Manchester City', 'Napoli')),
    ('Eden Hazard', ('Chelsea', 'Real Madrid')),
    ('Thibaut Courtois', ('Chelsea', 'Real Madrid', 'Atletico Madrid')),
    ('Romelu Lukaku', ('Chelsea', 'Manchester United', 'Inter', 'Roma', 'Napoli')),
    ('Antonio Rüdiger', ('Roma', 'Chelsea', 'Real Madrid')),
    ('Olivier Giroud', ('Arsenal', 'Chelsea', 'AC Milan')),
    ('Christian Pulisic', ('Borussia Dortmund', 'Chelsea', 'AC Milan')),
    ('Jadon Sancho', ('Borussia Dortmund', 'Manchester United', 'Chelsea')),
    ('Shinji Kagawa', ('Borussia Dortmund', 'Manchester United', 'Beşiktaş')),
    ('Robert Lewandowski', ('Borussia Dortmund', 'Bayern Münih', 'Barcelona')),
    ('Mats Hummels', ('Bayern Münih', 'Borussia Dortmund', 'Roma')),
    ('Mario Götze', ('Borussia Dortmund', 'Bayern Münih')),
    ('Ivan Perišić', ('Borussia Dortmund', 'Inter', 'Bayern Münih', 'Tottenham')),
    ('Harry Kane', ('Tottenham', 'Bayern Münih')),
    ('Eric Dier', ('Tottenham', 'Bayern Münih')),
    ('João Cancelo', ('Juventus', 'Manchester City', 'Bayern Münih', 'Barcelona', 'Inter')),
    ('Arturo Vidal', ('Juventus', 'Bayern Münih', 'Barcelona', 'Inter')),
    ('Kingsley Coman', ('PSG', 'Juventus', 'Bayern Münih')),
    ('Douglas Costa', ('Bayern Münih', 'Juventus')),
    ('Paul Pogba', ('Juventus', 'Manchester United')),
    ('Federico Chiesa', ('Juventus', 'Liverpool')),
    ('Emre Can', ('Bayern Münih', 'Liverpool', 'Juventus', 'Borussia Dortmund')),
    ('Hakan Çalhanoğlu', ('AC Milan', 'Inter')),
    ('Andrea Pirlo', ('Inter', 'AC Milan', 'Juventus')),
    ('Mohamed Salah', ('Chelsea', 'Roma', 'Liverpool')),
    ('Alisson Becker', ('Roma', 'Liverpool')),
    ('Xherdan Shaqiri', ('Bayern Münih', 'Inter', 'Liverpool')),
    ('Georginio Wijnaldum', ('PSG', 'Liverpool', 'Roma')),
    ('Raphinha', ('Barcelona', 'Leeds United')),
    ('Rúben Dias', ('Benfica', 'Manchester City')),
    ('Julián Álvarez', ('Manchester City', 'Atletico Madrid')),
    ('Antoine Griezmann', ('Barcelona', 'Atletico Madrid')),
    ('Memphis Depay', ('Manchester United', 'Barcelona', 'Atletico Madrid')),
    ('Frenkie de Jong', ('Ajax', 'Barcelona')),
    ('Matthijs de Ligt', ('Ajax', 'Juventus', 'Bayern Münih', 'Manchester United')),
    ('Donny van de Beek', ('Ajax', 'Manchester United')),
    ('Lisandro Martínez', ('Ajax', 'Manchester United')),
    ('André Onana', ('Ajax', 'Inter', 'Manchester United')),
    ('Christian Eriksen', ('Ajax', 'Tottenham', 'Inter', 'Manchester United')),
    ('Dušan Tadić', ('Ajax', 'Fenerbahçe')),
    ('Sébastien Haller', ('Ajax', 'Borussia Dortmund')),
    ('Daley Blind', ('Ajax', 'Manchester United', 'Bayern Münih')),
    ('Henrikh Mkhitaryan', ('Borussia Dortmund', 'Manchester United', 'Arsenal', 'Roma', 'Inter')),
    ('Leroy Sané', ('Manchester City', 'Bayern Münih', 'Galatasaray')),
    ('Serge Gnabry', ('Arsenal', 'Bayern Münih')),
    ('David Alaba', ('Bayern Münih', 'Real Madrid')),
    ('Luka Modrić', ('Tottenham', 'Real Madrid', 'AC Milan')),
    ('Iker Casillas', ('Real Madrid', 'Porto')),
    ('Marcos Llorente', ('Real Madrid', 'Atletico Madrid')),
    ('Sandro Tonali', ('AC Milan', 'Newcastle United')),
    ('Kyle Walker', ('Tottenham', 'Manchester City', 'AC Milan')),
    ('Raheem Sterling', ('Liverpool', 'Manchester City', 'Chelsea', 'Arsenal')),
    ('Cole Palmer', ('Manchester City', 'Chelsea')),
    ('Gabriel Jesus', ('Manchester City', 'Arsenal')),
    ('Oleksandr Zinchenko', ('Manchester City', 'Arsenal')),
    ('Declan Rice', ('Arsenal', 'West Ham United')),
    ('Jorginho', ('Napoli', 'Chelsea', 'Arsenal')),
    ('Mateo Kovačić', ('Real Madrid', 'Inter', 'Chelsea', 'Manchester City')),
    ('Kai Havertz', ('Chelsea', 'Arsenal')),
    ('Timo Werner', ('Chelsea', 'Tottenham', 'RB Leipzig')),
    ('Bruno Fernandes', ('Sporting CP', 'Manchester United')),
    ('Erling Haaland', ('Borussia Dortmund', 'Manchester City')),
    ('Virgil van Dijk', ('Liverpool', 'Southampton')),
    ('Martin Ødegaard', ('Real Madrid', 'Arsenal')),
    ('Alexander Isak', ('Borussia Dortmund', 'Newcastle United', 'Liverpool')),
]

CLUBS = sorted(set(c for _, cs in PLAYER_HISTORIES for c in cs), key=normalize)
PLAYER_NAMES = [n for n, _ in PLAYER_HISTORIES]
PAIR_PLAYERS: dict[frozenset[str], list[str]] = {}
for name, clubs in PLAYER_HISTORIES:
    for i, a in enumerate(clubs):
        for b in clubs[i + 1:]:
            PAIR_PLAYERS.setdefault(frozenset((a, b)), []).append(name)

# Short forms that still unambiguously denote a senior professional.
PLAYER_ALIASES = {
    'cr7': 'Cristiano Ronaldo', 'ronaldo': 'Cristiano Ronaldo',
    'r9': 'Ronaldo Nazário', 'ronaldo nazario': 'Ronaldo Nazário',
    'ozil': 'Mesut Özil', 'dzeko': 'Edin Džeko', 'sneijder': 'Wesley Sneijder',
    'van persie': 'Robin van Persie', 'ibra': 'Zlatan Ibrahimović',
    'messi': 'Lionel Messi', 'kdb': 'Kevin De Bruyne',
    'auba': 'Pierre-Emerick Aubameyang', 'hakimi': 'Achraf Hakimi',
    'mbappe': 'Kylian Mbappé', 'ramos': 'Sergio Ramos',
}


def valid_player_for_pair(answer: str, club_a: str, club_b: str) -> str | None:
    candidates = PAIR_PLAYERS.get(frozenset((club_a, club_b)), ())
    key = normalize(answer)
    if not key:
        return None
    # Alias lookup applies only if its canonical player belongs to both clubs.
    canonical = PLAYER_ALIASES.get(key)
    if canonical in candidates:
        return canonical
    for name in candidates:
        if key == normalize(name):
            return name
    # Unique last name among ALL players avoids ambiguous 'Ronaldo'.
    surname_hits = [name for name in PLAYER_NAMES if normalize(name).split(' ')[-1] == key and len(key) >= 4]
    if len(surname_hits) == 1 and surname_hits[0] in candidates:
        return surname_hits[0]
    return None


@dataclass
class Match:
    phase: str = 'choose'
    round_number: int = 1
    scores: list[int] = field(default_factory=lambda: [0, 0])
    used_clubs: set[str] = field(default_factory=set)
    picks: dict[int, str] = field(default_factory=dict)
    pair: tuple[str, str] | None = None
    winner: int | None = None
    event: dict = field(default_factory=dict)
    overtime: bool = False
    timeout_at: float | None = None
    attempted: set[int] = field(default_factory=set)

    def choose(self, player: int, club: str) -> str:
        if self.phase != 'choose':
            raise ValueError('Şu anda takım seçilemez.')
        if player in self.picks:
            raise ValueError('Bu tur için takımını zaten seçtin.')
        if club not in CLUBS or club in self.used_clubs:
            raise ValueError('Geçersiz veya elenmiş takım.')
        self.picks[player] = club
        if len(self.picks) < 2:
            return 'waiting'
        a, b = self.picks[0], self.picks[1]
        if a == b:
            self.used_clubs.add(a)
            self.event = {'kind': 'same', 'headline': 'Aynı takım seçildi!', 'detail': f'{a} elendi. Bu tur puan yok.', 'clubs': [a, b]}
            self.phase = 'result'
            return 'same'
        if not PAIR_PLAYERS.get(frozenset((a, b))):
            self.picks = {}
            self.event = {'kind': 'invalid', 'headline': 'Ortak futbolcu bulunamadı.', 'detail': 'Takımlar elenmedi, tur sayılmadı. Yeniden seçim yapın.'}
            return 'invalid'
        self.attempted.clear()
        self.pair = (a, b)
        self.used_clubs.update((a, b))
        self.phase = 'answer'
        self.event = {}
        return 'answer'

    def answer(self, player: int, name: str) -> str:
        if self.phase != 'answer' or not self.pair:
            raise ValueError('Şu anda cevap verilemez.')
        if player in self.attempted:
            raise ValueError('Bu turdaki tek cevap hakkını kullandın.')
        if not isinstance(name, str) or not name.strip() or len(name) > 100:
            raise ValueError('Geçerli bir futbolcu adı yaz.')
        self.attempted.add(player)
        found = valid_player_for_pair(name, *self.pair)
        if not found:
            raise ValueError('Yanlış cevap! Bu tur için hakkın bitti.')
        self.scores[player] += 1
        self.event = {'kind': 'point', 'headline': 'Doğru cevap!', 'detail': f'{found} • Oyuncu {player + 1} +1 puan', 'scorer': player, 'player': found, 'clubs': list(self.pair)}
        self.phase = 'result'
        self.timeout_at = None
        return found

    def timeout(self) -> None:
        if self.phase != 'answer':
            raise ValueError('Süre zaten dolmamış veya tur aktif değil.')
        all_answered = len(self.attempted) == 2
        self.event = {'kind': 'timeout', 'headline': 'İki cevap da yanlış!' if all_answered else 'Süre doldu!', 'detail': 'Bu turda puan kazanılmadı.', 'clubs': list(self.pair or ())}
        self.phase = 'result'
        self.timeout_at = None

    def advance(self) -> bool:
        """Return True when match ended; advance after displaying round result."""
        if self.phase != 'result':
            raise ValueError('Sonuç gösterilmeden tur ilerlemez.')
        a, b = self.scores
        win = None
        # '3' victory is only available before completing the seventh normal round.
        if self.round_number < 7 and max(a, b) >= 3:
            win = 0 if a > b else 1
        elif self.round_number >= 7 and a != b:
            win = 0 if a > b else 1
        if win is not None:
            self.winner = win
            self.phase = 'finished'
            return True
        self.round_number += 1
        self.overtime = self.round_number > 7
        self.phase = 'choose'
        self.picks = {}
        self.attempted.clear()
        self.pair = None
        self.event = {}
        self.timeout_at = None
        return False
