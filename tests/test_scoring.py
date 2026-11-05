from pathlib import Path

import pytest

from src.main import PROFILES
from src.recommender import (
    SCORING_MODES,
    Recommender,
    Song,
    UserProfile,
    get_mode,
    load_songs,
    recommend_songs,
    score_song,
)

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "songs.csv"


@pytest.fixture(scope="module")
def songs():
    return load_songs(str(DATA_PATH))


def make_song(**overrides):
    base = {
        "id": 1, "title": "T", "artist": "A", "genre": "pop", "mood": "happy",
        "energy": 0.8, "tempo_bpm": 120.0, "valence": 0.8, "danceability": 0.8,
        "acousticness": 0.2,
    }
    base.update(overrides)
    return base


# --- load_songs -----------------------------------------------------------

def test_load_songs_reads_whole_catalog(songs):
    assert len(songs) == 30


def test_load_songs_converts_numbers(songs):
    first = songs[0]
    assert isinstance(first["id"], int)
    assert isinstance(first["energy"], float)
    assert isinstance(first["tempo_bpm"], float)
    assert isinstance(first["popularity"], int)
    assert first["mood_tags"] == ["euphoric", "uplifting"]
    assert first["explicit"] is False


def test_load_songs_accepts_starter_columns_only(tmp_path):
    csv_file = tmp_path / "old.csv"
    csv_file.write_text(
        "id,title,artist,genre,mood,energy,tempo_bpm,valence,danceability,acousticness\n"
        "1,A,B,pop,happy,0.5,100,0.5,0.5,0.5\n"
    )
    loaded = load_songs(str(csv_file))
    assert loaded[0]["energy"] == 0.5
    assert "popularity" not in loaded[0]


def test_every_catalog_song_is_valid(songs):
    for song in songs:
        for key in ("energy", "valence", "danceability", "acousticness"):
            assert 0.0 <= song[key] <= 1.0
        assert 0 <= song["popularity"] <= 100


# --- score_song -----------------------------------------------------------

def test_score_follows_the_recipe():
    prefs = {"genre": "pop", "mood": "happy", "energy": 0.8}
    score, reasons = score_song(prefs, make_song())
    assert score == pytest.approx(4.0)
    assert reasons[0].startswith("genre match (+2.00)")
    assert reasons[1].startswith("mood match (+1.00)")


def test_energy_rewards_closeness_not_height():
    prefs = {"energy": 0.3}
    close, _ = score_song(prefs, make_song(energy=0.35))
    far, _ = score_song(prefs, make_song(energy=0.95))
    assert close > far


def test_energy_is_symmetric_around_target():
    prefs = {"energy": 0.5}
    below, _ = score_song(prefs, make_song(energy=0.3))
    above, _ = score_song(prefs, make_song(energy=0.7))
    assert below == pytest.approx(above)


def test_every_reason_shows_its_points():
    prefs = {"genre": "pop", "mood": "happy", "energy": 0.8, "likes_acoustic": False}
    score, reasons = score_song(prefs, make_song())
    assert reasons and all("(" in reason and reason.endswith(")") for reason in reasons)
    assert score > 0


def test_empty_prefs_score_zero_with_no_reasons():
    assert score_song({}, make_song()) == (0.0, [])


def test_genre_and_mood_are_case_insensitive():
    score, _ = score_song({"genre": "POP", "mood": "Happy"}, make_song())
    assert score == pytest.approx(3.0)


def test_explicit_penalty_applies_only_when_disallowed():
    explicit = make_song(explicit=True)
    allowed, _ = score_song({"energy": 0.8, "allow_explicit": True}, explicit)
    blocked, reasons = score_song({"energy": 0.8, "allow_explicit": False}, explicit)
    assert blocked == pytest.approx(allowed - 1.0)
    assert any("explicit" in reason for reason in reasons)


def test_extra_attributes_add_points():
    prefs = {"tags": ["cozy", "dreamy"], "decade": 2020, "popularity": 60, "language": "english"}
    song = make_song(mood_tags=["cozy"], release_decade=2020, popularity=60, language="english")
    score, reasons = score_song(prefs, song)
    assert score == pytest.approx(0.75 * 0.5 + 0.5 + 0.5 + 0.5)
    assert len(reasons) == 4


# --- scoring modes --------------------------------------------------------

def test_modes_change_the_weights():
    prefs = {"genre": "pop", "mood": "sad"}
    pop_happy = make_song()
    rock_sad = make_song(genre="rock", mood="sad")
    genre_first = (score_song(prefs, pop_happy, "genre_first")[0], score_song(prefs, rock_sad, "genre_first")[0])
    mood_first = (score_song(prefs, pop_happy, "mood_first")[0], score_song(prefs, rock_sad, "mood_first")[0])
    assert genre_first[0] > genre_first[1]
    assert mood_first[1] > mood_first[0]


def test_unknown_mode_raises_helpful_error():
    with pytest.raises(ValueError, match="Choose from"):
        get_mode("vibes_only")


def test_all_modes_are_registered():
    assert {"genre_first", "mood_first", "energy_focused"} <= set(SCORING_MODES)


# --- recommend_songs ------------------------------------------------------

def test_default_profile_puts_pop_happy_first(songs):
    results = recommend_songs(PROFILES["High-Energy Pop"], songs, k=5)
    assert results[0][0]["title"] == "Sunrise City"


def test_results_are_sorted_high_to_low(songs):
    results = recommend_songs(PROFILES["Chill Lofi"], songs, k=10)
    scores = [score for _, score, _ in results]
    assert scores == sorted(scores, reverse=True)


def test_k_limits_results_and_handles_oversize(songs):
    assert len(recommend_songs(PROFILES["Chill Lofi"], songs, k=3)) == 3
    assert len(recommend_songs(PROFILES["Chill Lofi"], songs, k=500)) == len(songs)


def test_empty_catalog_returns_empty_list():
    assert recommend_songs({"genre": "pop"}, [], k=5) == []


def test_recommend_does_not_mutate_input(songs):
    snapshot = [dict(song) for song in songs]
    recommend_songs(PROFILES["High-Energy Pop"], songs, k=5)
    assert songs == snapshot


def test_ties_break_by_song_id():
    twins = [make_song(id=2, title="B"), make_song(id=1, title="A")]
    results = recommend_songs({"genre": "pop"}, twins, k=2)
    assert [song["id"] for song, _, _ in results] == [1, 2]


def test_every_profile_returns_k_results(songs):
    for prefs in PROFILES.values():
        assert len(recommend_songs(prefs, songs, k=5)) == 5


# --- diversity penalty ----------------------------------------------------

def test_diversity_breaks_up_repeated_artists(songs):
    prefs = {"genre": "synthwave", "mood": "moody", "energy": 0.75}
    plain = recommend_songs(prefs, songs, k=5)
    diverse = recommend_songs(prefs, songs, k=5, diversity=True)
    plain_artists = [song["artist"] for song, _, _ in plain]
    diverse_artists = [song["artist"] for song, _, _ in diverse]
    assert len(set(diverse_artists)) >= len(set(plain_artists))


def test_diversity_penalty_is_explained():
    songs_ = [
        make_song(id=1, title="One", artist="Same"),
        make_song(id=2, title="Two", artist="Same", genre="rock"),
        make_song(id=3, title="Three", artist="Other", genre="rock", energy=0.7),
    ]
    results = recommend_songs({"genre": "pop", "energy": 0.8}, songs_, k=3, diversity=True)
    explanations = " ".join(explanation for _, _, explanation in results)
    assert "diversity: artist already picked" in explanations


def test_diversity_off_leaves_scores_untouched(songs):
    plain = recommend_songs(PROFILES["High-Energy Pop"], songs, k=5)
    again = recommend_songs(PROFILES["High-Energy Pop"], songs, k=5, diversity=False)
    assert plain == again


# --- OOP wrapper ----------------------------------------------------------

def test_user_profile_to_prefs_skips_unset_options():
    user = UserProfile("pop", "happy", 0.8, False)
    prefs = user.to_prefs()
    assert prefs["genre"] == "pop"
    assert "decade" not in prefs and "tags" not in prefs


def test_recommender_ranks_with_shared_scoring():
    songs_ = [
        Song(1, "Calm", "A", "lofi", "chill", 0.3, 70, 0.5, 0.5, 0.9),
        Song(2, "Hype", "B", "pop", "happy", 0.85, 120, 0.9, 0.9, 0.1),
    ]
    user = UserProfile("pop", "happy", 0.8, False)
    assert Recommender(songs_).recommend(user, k=1)[0].title == "Hype"


def test_explanation_mentions_the_score():
    song = Song(1, "Hype", "B", "pop", "happy", 0.85, 120, 0.9, 0.9, 0.1)
    text = Recommender([song]).explain_recommendation(UserProfile("pop", "happy", 0.8, False), song)
    assert "Hype" in text and "genre match" in text
