import csv
from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class Song:
    """A song and its attributes; the last five fields are optional extras."""
    id: int
    title: str
    artist: str
    genre: str
    mood: str
    energy: float
    tempo_bpm: float
    valence: float
    danceability: float
    acousticness: float
    popularity: int = 50
    release_decade: int = 2020
    mood_tags: List[str] = field(default_factory=list)
    language: str = "english"
    explicit: bool = False


@dataclass
class UserProfile:
    """A user's taste preferences; everything after likes_acoustic is optional."""
    favorite_genre: str
    favorite_mood: str
    target_energy: float
    likes_acoustic: bool
    target_valence: Optional[float] = None
    preferred_tags: List[str] = field(default_factory=list)
    target_decade: Optional[int] = None
    target_popularity: Optional[int] = None
    preferred_language: Optional[str] = None
    allow_explicit: bool = True

    def to_prefs(self) -> Dict:
        """Convert the profile into the plain dict that score_song expects."""
        prefs = {
            "genre": self.favorite_genre,
            "mood": self.favorite_mood,
            "energy": self.target_energy,
            "likes_acoustic": self.likes_acoustic,
            "allow_explicit": self.allow_explicit,
        }
        optional = {
            "valence": self.target_valence,
            "tags": self.preferred_tags or None,
            "decade": self.target_decade,
            "popularity": self.target_popularity,
            "language": self.preferred_language,
        }
        prefs.update({key: value for key, value in optional.items() if value is not None})
        return prefs


# ---------------------------------------------------------------------------
# Scoring modes (Strategy pattern: each mode is a swappable set of weights)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ScoringMode:
    """One ranking strategy: how many points each kind of match is worth."""
    name: str
    description: str
    genre: float = 2.0
    mood: float = 1.0
    energy: float = 1.0
    acousticness: float = 0.5
    valence: float = 0.5
    tags: float = 0.75
    decade: float = 0.5
    popularity: float = 0.5
    language: float = 0.5
    explicit_penalty: float = 1.0


SCORING_MODES: Dict[str, ScoringMode] = {
    "genre_first": ScoringMode(
        name="genre_first",
        description="Default recipe: genre 2.0, mood 1.0, energy up to 1.0.",
    ),
    "mood_first": ScoringMode(
        name="mood_first",
        description="Mood is worth twice as much as genre.",
        genre=1.0,
        mood=2.0,
    ),
    "energy_focused": ScoringMode(
        name="energy_focused",
        description="Energy doubled, genre halved: the 'vibe' matters most.",
        genre=1.0,
        energy=2.0,
    ),
}

DEFAULT_MODE = "genre_first"

# Penalty applied to a candidate for each song already picked that shares its
# artist or genre (Diversity Penalty, Challenge 3).
ARTIST_REPEAT_PENALTY = 1.0
GENRE_REPEAT_PENALTY = 0.5


def get_mode(mode) -> ScoringMode:
    """Resolve a mode name (or an existing ScoringMode) into a ScoringMode."""
    if isinstance(mode, ScoringMode):
        return mode
    try:
        return SCORING_MODES[mode]
    except KeyError:
        valid = ", ".join(sorted(SCORING_MODES))
        raise ValueError(f"Unknown scoring mode '{mode}'. Choose from: {valid}") from None


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

def _to_bool(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def _parse_song_row(row: Dict[str, str]) -> Dict:
    """Convert one CSV row of strings into typed values; extra columns are optional."""
    song: Dict = {
        "id": int(row["id"]),
        "title": row["title"],
        "artist": row["artist"],
        "genre": row["genre"].strip().lower(),
        "mood": row["mood"].strip().lower(),
        "energy": float(row["energy"]),
        "tempo_bpm": float(row["tempo_bpm"]),
        "valence": float(row["valence"]),
        "danceability": float(row["danceability"]),
        "acousticness": float(row["acousticness"]),
    }
    if row.get("popularity"):
        song["popularity"] = int(row["popularity"])
    if row.get("release_decade"):
        song["release_decade"] = int(row["release_decade"])
    if row.get("mood_tags"):
        song["mood_tags"] = [tag.strip().lower() for tag in row["mood_tags"].split("|") if tag.strip()]
    if row.get("language"):
        song["language"] = row["language"].strip().lower()
    if row.get("explicit"):
        song["explicit"] = _to_bool(row["explicit"])
    return song


def load_songs(csv_path: str) -> List[Dict]:
    """Read songs.csv into a list of dicts with numeric fields converted to int/float."""
    with open(csv_path, newline="", encoding="utf-8") as handle:
        return [_parse_song_row(row) for row in csv.DictReader(handle)]


# ---------------------------------------------------------------------------
# Scoring and ranking
# ---------------------------------------------------------------------------

def _closeness(value: float, target: float, scale: float = 1.0) -> float:
    """Return 1.0 for an exact match, falling linearly to 0.0 at `scale` away."""
    return max(0.0, 1.0 - abs(value - target) / scale)


def score_song(user_prefs: Dict, song: Dict, mode=DEFAULT_MODE) -> Tuple[float, List[str]]:
    """Score one song against a user's preferences and explain every point awarded."""
    weights = get_mode(mode)
    score = 0.0
    reasons: List[str] = []

    def award(points: float, text: str) -> None:
        nonlocal score
        score += points
        reasons.append(f"{text} ({points:+.2f})")

    genre = user_prefs.get("genre")
    if genre and song["genre"] == str(genre).lower():
        award(weights.genre, "genre match")

    mood = user_prefs.get("mood")
    if mood and song["mood"] == str(mood).lower():
        award(weights.mood, "mood match")

    if "energy" in user_prefs:
        target = float(user_prefs["energy"])
        award(
            weights.energy * _closeness(song["energy"], target),
            f"energy {song['energy']:.2f} vs target {target:.2f}",
        )

    if "likes_acoustic" in user_prefs:
        wants_acoustic = bool(user_prefs["likes_acoustic"])
        fit = song["acousticness"] if wants_acoustic else 1.0 - song["acousticness"]
        label = "acoustic" if wants_acoustic else "non-acoustic"
        award(weights.acousticness * fit, f"{label} fit ({song['acousticness']:.2f} acousticness)")

    if "valence" in user_prefs:
        target = float(user_prefs["valence"])
        award(
            weights.valence * _closeness(song["valence"], target),
            f"valence {song['valence']:.2f} vs target {target:.2f}",
        )

    wanted_tags = [str(tag).lower() for tag in user_prefs.get("tags", [])]
    if wanted_tags:
        shared = [tag for tag in wanted_tags if tag in song.get("mood_tags", [])]
        if shared:
            award(weights.tags * len(shared) / len(wanted_tags), f"mood tags {'/'.join(shared)}")

    if "decade" in user_prefs and "release_decade" in song:
        gap = abs(song["release_decade"] - int(user_prefs["decade"]))
        fit = _closeness(gap, 0, scale=50.0)
        if fit > 0:
            award(weights.decade * fit, f"{song['release_decade']}s release vs {user_prefs['decade']}s")

    if "popularity" in user_prefs and "popularity" in song:
        fit = _closeness(song["popularity"], float(user_prefs["popularity"]), scale=100.0)
        award(weights.popularity * fit, f"popularity {song['popularity']} vs target {user_prefs['popularity']}")

    language = user_prefs.get("language")
    if language and song.get("language") == str(language).lower():
        award(weights.language, f"language match ({language})")

    if not user_prefs.get("allow_explicit", True) and song.get("explicit"):
        award(-weights.explicit_penalty, "explicit content")

    return score, reasons


def _rank_plain(scored: List[Tuple[Dict, float, List[str]]], k: int) -> List[Tuple[Dict, float, List[str]]]:
    """Rank by score, highest first; ties go to the lower song id so output is stable."""
    return sorted(scored, key=lambda item: (-item[1], item[0].get("id", 0)))[:k]


def _rank_diverse(scored: List[Tuple[Dict, float, List[str]]], k: int) -> List[Tuple[Dict, float, List[str]]]:
    """Greedy re-rank: each pick lowers the score of later songs by the same artist or genre."""
    remaining = list(scored)
    picked: List[Tuple[Dict, float, List[str]]] = []
    while remaining and len(picked) < k:
        best = None
        for song, score, reasons in remaining:
            repeat_artist = sum(1 for chosen, _, _ in picked if chosen["artist"] == song["artist"])
            repeat_genre = sum(1 for chosen, _, _ in picked if chosen["genre"] == song["genre"])
            penalty = repeat_artist * ARTIST_REPEAT_PENALTY + repeat_genre * GENRE_REPEAT_PENALTY
            adjusted = score - penalty
            extra = list(reasons)
            if repeat_artist:
                extra.append(f"diversity: artist already picked ({-repeat_artist * ARTIST_REPEAT_PENALTY:+.2f})")
            if repeat_genre:
                extra.append(f"diversity: genre already picked ({-repeat_genre * GENRE_REPEAT_PENALTY:+.2f})")
            candidate = (song, adjusted, extra)
            if best is None or (-adjusted, song.get("id", 0)) < (-best[1], best[0].get("id", 0)):
                best = candidate
        picked.append(best)
        remaining = [item for item in remaining if item[0] is not best[0]]
    return picked


def recommend_songs(
    user_prefs: Dict,
    songs: List[Dict],
    k: int = 5,
    mode=DEFAULT_MODE,
    diversity: bool = False,
) -> List[Tuple[Dict, float, str]]:
    """Score every song, rank them, and return the top k as (song, score, explanation)."""
    scored = []
    for song in songs:
        score, reasons = score_song(user_prefs, song, mode)
        scored.append((song, score, reasons))
    ranked = _rank_diverse(scored, k) if diversity else _rank_plain(scored, k)
    return [(song, score, "; ".join(reasons)) for song, score, reasons in ranked]


# ---------------------------------------------------------------------------
# Object-oriented wrapper (used by the tests)
# ---------------------------------------------------------------------------

class Recommender:
    """OOP wrapper that ranks Song objects for a UserProfile using the same scoring."""

    def __init__(self, songs: List[Song], mode=DEFAULT_MODE, diversity: bool = False):
        self.songs = songs
        self.mode = mode
        self.diversity = diversity

    def recommend(self, user: UserProfile, k: int = 5) -> List[Song]:
        """Return the top k Song objects for this user, best first."""
        by_id = {song.id: song for song in self.songs}
        ranked = recommend_songs(
            user.to_prefs(),
            [asdict(song) for song in self.songs],
            k=k,
            mode=self.mode,
            diversity=self.diversity,
        )
        return [by_id[item[0]["id"]] for item in ranked]

    def explain_recommendation(self, user: UserProfile, song: Song) -> str:
        """Return a plain-language explanation of why this song scored the way it did."""
        score, reasons = score_song(user.to_prefs(), asdict(song), self.mode)
        if not reasons:
            return f"{song.title} earned no points for this profile (score {score:.2f})."
        return f"{song.title} scored {score:.2f}: " + "; ".join(reasons)
