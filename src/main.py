"""
Command line runner for the Music Recommender Simulation.

Examples:
    python -m src.main                          # default pop/happy profile
    python -m src.main --profile all            # every profile, incl. adversarial ones
    python -m src.main --mode mood_first        # switch scoring strategy
    python -m src.main --diversity              # penalize repeated artists/genres
    python -m src.main --experiment             # weight-shift and feature-removal runs
"""

import argparse
from dataclasses import replace
from pathlib import Path
from typing import Dict, List

from tabulate import tabulate

from src.recommender import (
    DEFAULT_MODE,
    SCORING_MODES,
    get_mode,
    load_songs,
    recommend_songs,
)

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "songs.csv"

# The default profile from the assignment: a happy pop listener.
DEFAULT_PROFILE = "High-Energy Pop"

PROFILES: Dict[str, Dict] = {
    "High-Energy Pop": {"genre": "pop", "mood": "happy", "energy": 0.8},
    "Chill Lofi": {
        "genre": "lofi", "mood": "chill", "energy": 0.35,
        "likes_acoustic": True, "tags": ["cozy", "dreamy"],
    },
    "Deep Intense Rock": {
        "genre": "rock", "mood": "intense", "energy": 0.92,
        "likes_acoustic": False, "tags": ["aggressive"], "decade": 2010,
    },
    # Adversarial profiles, designed to confuse the scoring logic.
    "Conflicting (high energy + sad)": {"genre": "pop", "mood": "sad", "energy": 0.9},
    "Genre Missing From Catalog": {"genre": "opera", "mood": "romantic", "energy": 0.4},
    "Middle Of The Road": {"energy": 0.5},
    "Clean Spanish Party": {
        "genre": "latin", "mood": "energetic", "energy": 0.85,
        "language": "spanish", "allow_explicit": False, "popularity": 90,
    },
}


def format_results(profile_name: str, prefs: Dict, recommendations, mode: str, diversity: bool) -> str:
    """Build a readable table: rank, title, artist, genre/mood, score and reasons."""
    shown = ", ".join(f"{key}={value}" for key, value in prefs.items())
    header = f"Profile: {profile_name} | mode: {mode}{' + diversity' if diversity else ''}\nPrefs: {shown}"
    rows = []
    for rank, (song, score, explanation) in enumerate(recommendations, start=1):
        reasons = "\n".join(explanation.split("; ")) if explanation else "no matching features"
        rows.append([rank, song["title"], song["artist"], f"{song['genre']} / {song['mood']}", f"{score:.2f}", reasons])
    table = tabulate(
        rows,
        headers=["#", "Title", "Artist", "Genre / Mood", "Score", "Reasons"],
        tablefmt="grid",
        disable_numparse=True,
        colalign=("right", "left", "left", "left", "right", "left"),
    )
    return f"{header}\n{table}\n"


def run_profile(name: str, songs: List[Dict], k: int, mode: str, diversity: bool) -> None:
    """Recommend for one named profile and print the table."""
    prefs = PROFILES[name]
    recommendations = recommend_songs(prefs, songs, k=k, mode=mode, diversity=diversity)
    print(format_results(name, prefs, recommendations, mode, diversity))


def run_experiment(songs: List[Dict], k: int) -> None:
    """Compare the baseline against a weight shift and a feature removal for one profile."""
    name = DEFAULT_PROFILE
    prefs = PROFILES[name]
    variants = {
        "baseline (genre 2.0, mood 1.0, energy 1.0)": get_mode(DEFAULT_MODE),
        "weight shift (genre 1.0, energy 2.0)": SCORING_MODES["energy_focused"],
        "feature removal (mood check off)": replace(get_mode(DEFAULT_MODE), name="no_mood", mood=0.0),
    }
    print(f"EXPERIMENT on profile '{name}': {prefs}\n")
    for label, mode in variants.items():
        recommendations = recommend_songs(prefs, songs, k=k, mode=mode)
        rows = [[rank, song["title"], f"{song['genre']} / {song['mood']}", f"{score:.2f}"]
                for rank, (song, score, _) in enumerate(recommendations, start=1)]
        print(label)
        print(tabulate(rows, headers=["#", "Title", "Genre / Mood", "Score"], tablefmt="simple"))
        print()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Music Recommender Simulation")
    parser.add_argument("--profile", default=DEFAULT_PROFILE,
                        help=f"profile name or 'all'. Choices: {', '.join(PROFILES)}")
    parser.add_argument("--mode", default=DEFAULT_MODE, choices=sorted(SCORING_MODES),
                        help="scoring strategy to use")
    parser.add_argument("-k", type=int, default=5, help="how many songs to recommend")
    parser.add_argument("--diversity", action="store_true",
                        help="penalize songs whose artist or genre is already in the list")
    parser.add_argument("--experiment", action="store_true",
                        help="run the weight-shift and feature-removal experiment")
    return parser


def main(argv=None) -> None:
    args = build_parser().parse_args(argv)
    songs = load_songs(str(DATA_PATH))
    print(f"\nLoaded songs: {len(songs)}\n")

    if args.experiment:
        run_experiment(songs, args.k)
        return

    names = list(PROFILES) if args.profile == "all" else [args.profile]
    unknown = [name for name in names if name not in PROFILES]
    if unknown:
        raise SystemExit(f"Unknown profile '{unknown[0]}'. Choose from: {', '.join(PROFILES)}")
    for name in names:
        run_profile(name, songs, args.k, args.mode, args.diversity)


if __name__ == "__main__":
    main()
