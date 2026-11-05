# 🎵 Music Recommender Simulation

## Project Summary

VibeFinder 1.0 is a small, CLI-first music recommender. It reads a 30-song catalog from `data/songs.csv`, compares every song to a "taste profile" (favorite genre, mood, target energy, and a few optional extras), and prints the top matches in a table with the exact reasons each song earned its points.

It is a content-based system: it only looks at song attributes, never at what other listeners did. That makes it easy to explain, and it is also why it has the biases described below.

Beyond the core project it includes all four optional extensions: five extra song attributes, switchable scoring modes, a diversity penalty, and a formatted summary table.

---

## How The System Works

### How real recommenders work (short version)

Big platforms like Spotify and YouTube blend two ideas. **Collaborative filtering** says "people whose listening history looks like yours also loved this song", so it uses other users' behavior (likes, skips, replays, playlist adds, watch time) and needs no knowledge of the music itself. **Content-based filtering** says "this song has attributes similar to songs you already like", so it uses the song's own features (genre, tempo, energy, mood, acousticness, lyrics, audio embeddings). Collaborative filtering finds surprising matches but struggles with brand-new songs and users (the cold-start problem); content-based filtering works on day one but tends to keep you in a bubble of more-of-the-same. This project simulates only the content-based half.

### What my version prioritizes

My recommender treats genre as the strongest signal, mood as the next strongest, and then rewards songs whose numbers sit *close* to what the user wants instead of simply being higher or lower. Every point is explained in plain text so a user can see why a song showed up.

### Features

**`Song`** (columns in `data/songs.csv`):

- Starter features: `genre`, `mood`, `energy` (0-1), `tempo_bpm`, `valence` (0-1), `danceability` (0-1), `acousticness` (0-1)
- Extension features: `popularity` (0-100), `release_decade`, `mood_tags` (detailed tags such as `nostalgic|cozy`), `language`, `explicit`

**`UserProfile`** (or the equivalent preferences dict used by `score_song`):

- Required: `favorite_genre`, `favorite_mood`, `target_energy`, `likes_acoustic`
- Optional: `target_valence`, `preferred_tags`, `target_decade`, `target_popularity`, `preferred_language`, `allow_explicit`

An optional preference that is not set is simply skipped, so a short profile never gets penalized for what it did not ask for.

### Algorithm Recipe (default `genre_first` mode)

Scoring rule, applied to one song:

| Signal | Points |
|---|---|
| Genre matches exactly | +2.0 |
| Mood matches exactly | +1.0 |
| Energy closeness | up to +1.0, computed as `1 - abs(song_energy - target_energy)` |
| Acousticness fit | up to +0.5 (matches the song's acousticness if the user likes acoustic, otherwise `1 - acousticness`) |
| Valence closeness (if set) | up to +0.5 |
| Shared mood tags (if set) | up to +0.75, scaled by the share of requested tags found |
| Release decade closeness (if set) | up to +0.5, fading to zero 50 years away |
| Popularity closeness (if set) | up to +0.5 |
| Language match (if set) | +0.5 |
| Explicit song when user disallows it | -1.0 |

Ranking rule: score every song in the catalog, sort from highest to lowest (ties go to the lower song id so results are stable), and return the top k. Why both rules? The scoring rule judges one song in isolation; the ranking rule compares all of those judgments to decide what the user actually sees.

```
Input (user prefs) --> Process (loop over all 30 songs, score_song on each) --> Output (sorted, top k with reasons)
```

### Scoring modes (Strategy pattern)

A `ScoringMode` is a frozen set of weights, and `score_song(..., mode=...)` accepts any of them, so strategies swap without touching the scoring code.

| Mode | Genre | Mood | Energy | Idea |
|---|---|---|---|---|
| `genre_first` (default) | 2.0 | 1.0 | 1.0 | The recipe above |
| `mood_first` | 1.0 | 2.0 | 1.0 | Feeling beats label |
| `energy_focused` | 1.0 | 1.0 | 2.0 | Energy doubled, genre halved |

### Diversity penalty

With `--diversity`, results are chosen one at a time. After each pick, remaining songs lose 1.0 point for every already-picked song by the same artist and 0.5 for every already-picked song in the same genre, and the penalty is listed in the reasons.

### Expected biases

- Genre is worth more than mood and energy combined for most profiles, so a mediocre song in the right genre can outrank a better-feeling song in a neighboring genre.
- Genre and mood are exact string matches, so `pop` earns nothing for `indie pop` or `k-pop`, and `sad` earns nothing for `melancholic`.
- A 30-song catalog means most genres have exactly one song, so a "genre match" often means "the only song of that genre".

---

## Getting Started

### Setup

1. Create a virtual environment (optional but recommended):

   ```bash
   python -m venv .venv
   source .venv/bin/activate      # Mac or Linux
   .venv\Scripts\activate         # Windows
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Run the app from the repo root:

   ```bash
   python -m src.main
   ```

### Command line options

```bash
python -m src.main                                   # default pop/happy profile
python -m src.main --profile all                     # every profile, including adversarial ones
python -m src.main --profile "Chill Lofi" --mode mood_first
python -m src.main --profile "Chill Lofi" --diversity
python -m src.main --experiment                      # weight-shift and feature-removal experiment
python -m src.main -k 3                              # change how many songs are shown
```

### Running Tests

```bash
pytest
```

The suite has 30 tests covering CSV loading, the scoring rules, ranking order, edge cases (empty catalog, `k` larger than the catalog, empty preferences, ties), the three modes, the diversity penalty, and the object-oriented `Recommender`.

---

## Sample Recommendation Output

Default profile (`genre=pop, mood=happy, energy=0.8`), produced by `python -m src.main`:

```
Profile: High-Energy Pop | mode: genre_first
Prefs: genre=pop, mood=happy, energy=0.8
+-----+-------------------------+---------------+-------------------+---------+------------------------------------+
|   # | Title                   | Artist        | Genre / Mood      |   Score | Reasons                            |
+=====+=========================+===============+===================+=========+====================================+
|   1 | Sunrise City            | Neon Echo     | pop / happy       |    3.98 | genre match (+2.00)                |
|     |                         |               |                   |         | mood match (+1.00)                 |
|     |                         |               |                   |         | energy 0.82 vs target 0.80 (+0.98) |
+-----+-------------------------+---------------+-------------------+---------+------------------------------------+
|   2 | Gym Hero                | Max Pulse     | pop / intense     |    2.87 | genre match (+2.00)                |
|     |                         |               |                   |         | energy 0.93 vs target 0.80 (+0.87) |
+-----+-------------------------+---------------+-------------------+---------+------------------------------------+
|   3 | Glass Heart Confessions | Liv Harlow    | pop / sad         |    2.55 | genre match (+2.00)                |
|     |                         |               |                   |         | energy 0.35 vs target 0.80 (+0.55) |
+-----+-------------------------+---------------+-------------------+---------+------------------------------------+
|   4 | Slap Bass Sunday        | Funktronic    | funk / happy      |    2.00 | mood match (+1.00)                 |
|     |                         |               |                   |         | energy 0.80 vs target 0.80 (+1.00) |
+-----+-------------------------+---------------+-------------------+---------+------------------------------------+
|   5 | Rooftop Lights          | Indigo Parade | indie pop / happy |    1.96 | mood match (+1.00)                 |
|     |                         |               |                   |         | energy 0.76 vs target 0.80 (+0.96) |
+-----+-------------------------+---------------+-------------------+---------+------------------------------------+
```

**Screenshot or video** *(optional)*: <!-- Insert a screenshot or demo video link here -->

### Stress test outputs (top 5 per profile)

**Chill Lofi**

```
Profile: Chill Lofi | mode: genre_first
Prefs: genre=lofi, mood=chill, energy=0.35, likes_acoustic=True, tags=['cozy', 'dreamy']
+-----+---------------------+----------------+-----------------+---------+------------------------------------------+
|   # | Title               | Artist         | Genre / Mood    |   Score | Reasons                                  |
+=====+=====================+================+=================+=========+==========================================+
|   1 | Library Rain        | Paper Lanterns | lofi / chill    |    5.18 | genre match (+2.00)                      |
|     |                     |                |                 |         | mood match (+1.00)                       |
|     |                     |                |                 |         | energy 0.35 vs target 0.35 (+1.00)       |
|     |                     |                |                 |         | acoustic fit (0.86 acousticness) (+0.43) |
|     |                     |                |                 |         | mood tags cozy/dreamy (+0.75)            |
+-----+---------------------+----------------+-----------------+---------+------------------------------------------+
|   2 | Midnight Coding     | LoRoom         | lofi / chill    |    4.66 | genre match (+2.00)                      |
|     |                     |                |                 |         | mood match (+1.00)                       |
|     |                     |                |                 |         | energy 0.42 vs target 0.35 (+0.93)       |
|     |                     |                |                 |         | acoustic fit (0.71 acousticness) (+0.35) |
|     |                     |                |                 |         | mood tags cozy (+0.38)                   |
+-----+---------------------+----------------+-----------------+---------+------------------------------------------+
|   3 | Focus Flow          | LoRoom         | lofi / focused  |    3.72 | genre match (+2.00)                      |
|     |                     |                |                 |         | energy 0.40 vs target 0.35 (+0.95)       |
|     |                     |                |                 |         | acoustic fit (0.78 acousticness) (+0.39) |
|     |                     |                |                 |         | mood tags cozy (+0.38)                   |
+-----+---------------------+----------------+-----------------+---------+------------------------------------------+
|   4 | Spacewalk Thoughts  | Orbit Bloom    | ambient / chill |    2.77 | mood match (+1.00)                       |
|     |                     |                |                 |         | energy 0.28 vs target 0.35 (+0.93)       |
|     |                     |                |                 |         | acoustic fit (0.92 acousticness) (+0.46) |
|     |                     |                |                 |         | mood tags dreamy (+0.38)                 |
+-----+---------------------+----------------+-----------------+---------+------------------------------------------+
|   5 | Coffee Shop Stories | Slow Stereo    | jazz / relaxed  |    1.80 | energy 0.37 vs target 0.35 (+0.98)       |
|     |                     |                |                 |         | acoustic fit (0.89 acousticness) (+0.45) |
|     |                     |                |                 |         | mood tags cozy (+0.38)                   |
+-----+---------------------+----------------+-----------------+---------+------------------------------------------+
```

**Deep Intense Rock**

```
Profile: Deep Intense Rock | mode: genre_first
Prefs: genre=rock, mood=intense, energy=0.92, likes_acoustic=False, tags=['aggressive'], decade=2010
+-----+-----------------+-----------+------------------+---------+----------------------------------------------+
|   # | Title           | Artist    | Genre / Mood     |   Score | Reasons                                      |
+=====+=================+===========+==================+=========+==============================================+
|   1 | Storm Runner    | Voltline  | rock / intense   |    5.69 | genre match (+2.00)                          |
|     |                 |           |                  |         | mood match (+1.00)                           |
|     |                 |           |                  |         | energy 0.91 vs target 0.92 (+0.99)           |
|     |                 |           |                  |         | non-acoustic fit (0.10 acousticness) (+0.45) |
|     |                 |           |                  |         | mood tags aggressive (+0.75)                 |
|     |                 |           |                  |         | 2010s release vs 2010s (+0.50)               |
+-----+-----------------+-----------+------------------+---------+----------------------------------------------+
|   2 | Gym Hero        | Max Pulse | pop / intense    |    3.61 | mood match (+1.00)                           |
|     |                 |           |                  |         | energy 0.93 vs target 0.92 (+0.99)           |
|     |                 |           |                  |         | non-acoustic fit (0.05 acousticness) (+0.47) |
|     |                 |           |                  |         | mood tags aggressive (+0.75)                 |
|     |                 |           |                  |         | 2020s release vs 2010s (+0.40)               |
+-----+-----------------+-----------+------------------+---------+----------------------------------------------+
|   3 | Warehouse 303   | Kessler   | techno / intense |    2.98 | mood match (+1.00)                           |
|     |                 |           |                  |         | energy 0.91 vs target 0.92 (+0.99)           |
|     |                 |           |                  |         | non-acoustic fit (0.02 acousticness) (+0.49) |
|     |                 |           |                  |         | 2010s release vs 2010s (+0.50)               |
+-----+-----------------+-----------+------------------+---------+----------------------------------------------+
|   4 | Teenage Static  | Rust Kids | punk / angry     |    1.85 | energy 0.93 vs target 0.92 (+0.99)           |
|     |                 |           |                  |         | non-acoustic fit (0.08 acousticness) (+0.46) |
|     |                 |           |                  |         | 2000s release vs 2010s (+0.40)               |
+-----+-----------------+-----------+------------------+---------+----------------------------------------------+
|   5 | Pulse Cathedral | Arc Zero  | edm / euphoric   |    1.85 | energy 0.96 vs target 0.92 (+0.96)           |
|     |                 |           |                  |         | non-acoustic fit (0.03 acousticness) (+0.48) |
|     |                 |           |                  |         | 2020s release vs 2010s (+0.40)               |
+-----+-----------------+-----------+------------------+---------+----------------------------------------------+
```

**Adversarial: conflicting preferences (high energy but sad)**

```
Profile: Conflicting (high energy + sad) | mode: genre_first
Prefs: genre=pop, mood=sad, energy=0.9
+-----+-------------------------+-----------------+----------------+---------+------------------------------------+
|   # | Title                   | Artist          | Genre / Mood   |   Score | Reasons                            |
+=====+=========================+=================+================+=========+====================================+
|   1 | Glass Heart Confessions | Liv Harlow      | pop / sad      |    3.45 | genre match (+2.00)                |
|     |                         |                 |                |         | mood match (+1.00)                 |
|     |                         |                 |                |         | energy 0.35 vs target 0.90 (+0.45) |
+-----+-------------------------+-----------------+----------------+---------+------------------------------------+
|   2 | Gym Hero                | Max Pulse       | pop / intense  |    2.97 | genre match (+2.00)                |
|     |                         |                 |                |         | energy 0.93 vs target 0.90 (+0.97) |
+-----+-------------------------+-----------------+----------------+---------+------------------------------------+
|   3 | Sunrise City            | Neon Echo       | pop / happy    |    2.92 | genre match (+2.00)                |
|     |                         |                 |                |         | energy 0.82 vs target 0.90 (+0.92) |
+-----+-------------------------+-----------------+----------------+---------+------------------------------------+
|   4 | Smoke and Whiskey       | Delta Moon      | blues / sad    |    1.54 | mood match (+1.00)                 |
|     |                         |                 |                |         | energy 0.44 vs target 0.90 (+0.54) |
+-----+-------------------------+-----------------+----------------+---------+------------------------------------+
|   5 | Hollow Pines            | Wren and Willow | folk / sad     |    1.40 | mood match (+1.00)                 |
|     |                         |                 |                |         | energy 0.30 vs target 0.90 (+0.40) |
+-----+-------------------------+-----------------+----------------+---------+------------------------------------+
```

**Adversarial: genre missing from the catalog**

```
Profile: Genre Missing From Catalog | mode: genre_first
Prefs: genre=opera, mood=romantic, energy=0.4
+-----+---------------------+---------------+------------------------+---------+------------------------------------+
|   # | Title               | Artist        | Genre / Mood           |   Score | Reasons                            |
+=====+=====================+===============+========================+=========+====================================+
|   1 | Velvet Hours        | Mara Sol      | r&b / romantic         |    1.88 | mood match (+1.00)                 |
|     |                     |               |                        |         | energy 0.52 vs target 0.40 (+0.88) |
+-----+---------------------+---------------+------------------------+---------+------------------------------------+
|   2 | Focus Flow          | LoRoom        | lofi / focused         |    1.00 | energy 0.40 vs target 0.40 (+1.00) |
+-----+---------------------+---------------+------------------------+---------+------------------------------------+
|   3 | Midnight Coding     | LoRoom        | lofi / chill           |    0.98 | energy 0.42 vs target 0.40 (+0.98) |
+-----+---------------------+---------------+------------------------+---------+------------------------------------+
|   4 | Paper Boats         | June Calloway | indie folk / nostalgic |    0.98 | energy 0.38 vs target 0.40 (+0.98) |
+-----+---------------------+---------------+------------------------+---------+------------------------------------+
|   5 | Coffee Shop Stories | Slow Stereo   | jazz / relaxed         |    0.97 | energy 0.37 vs target 0.40 (+0.97) |
+-----+---------------------+---------------+------------------------+---------+------------------------------------+
```

**Adversarial: only an energy preference**

```
Profile: Middle Of The Road | mode: genre_first
Prefs: energy=0.5
+-----+-------------------+--------------+---------------------+---------+------------------------------------+
|   # | Title             | Artist       | Genre / Mood        |   Score | Reasons                            |
+=====+===================+==============+=====================+=========+====================================+
|   1 | Velvet Hours      | Mara Sol     | r&b / romantic      |    0.98 | energy 0.52 vs target 0.50 (+0.98) |
+-----+-------------------+--------------+---------------------+---------+------------------------------------+
|   2 | Island Slow Burn  | Jah Meridian | reggae / relaxed    |    0.98 | energy 0.48 vs target 0.50 (+0.98) |
+-----+-------------------+--------------+---------------------+---------+------------------------------------+
|   3 | Dust Road Home    | Waylon Pike  | country / nostalgic |    0.95 | energy 0.55 vs target 0.50 (+0.95) |
+-----+-------------------+--------------+---------------------+---------+------------------------------------+
|   4 | Smoke and Whiskey | Delta Moon   | blues / sad         |    0.94 | energy 0.44 vs target 0.50 (+0.94) |
+-----+-------------------+--------------+---------------------+---------+------------------------------------+
|   5 | Midnight Coding   | LoRoom       | lofi / chill        |    0.92 | energy 0.42 vs target 0.50 (+0.92) |
+-----+-------------------+--------------+---------------------+---------+------------------------------------+
```

**Clean Spanish party (language, popularity, and explicit filter)**

```
Profile: Clean Spanish Party | mode: genre_first
Prefs: genre=latin, mood=energetic, energy=0.85, language=spanish, allow_explicit=False, popularity=90
+-----+-------------------+-------------+----------------------+---------+------------------------------------+
|   # | Title             | Artist      | Genre / Mood         |   Score | Reasons                            |
+=====+===================+=============+======================+=========+====================================+
|   1 | Fuego en la Calle | Luz Navarro | latin / energetic    |    4.99 | genre match (+2.00)                |
|     |                   |             |                      |         | mood match (+1.00)                 |
|     |                   |             |                      |         | energy 0.86 vs target 0.85 (+0.99) |
|     |                   |             |                      |         | popularity 90 vs target 90 (+0.50) |
|     |                   |             |                      |         | language match (spanish) (+0.50)   |
+-----+-------------------+-------------+----------------------+---------+------------------------------------+
|   2 | Pixel Dreams      | Chiptone    | chiptune / energetic |    2.22 | mood match (+1.00)                 |
|     |                   |             |                      |         | energy 0.84 vs target 0.85 (+0.99) |
|     |                   |             |                      |         | popularity 36 vs target 90 (+0.23) |
+-----+-------------------+-------------+----------------------+---------+------------------------------------+
|   3 | Starlight Hotline | Mochi Pop   | k-pop / happy        |    1.45 | energy 0.88 vs target 0.85 (+0.97) |
|     |                   |             |                      |         | popularity 86 vs target 90 (+0.48) |
+-----+-------------------+-------------+----------------------+---------+------------------------------------+
|   4 | Sunrise City      | Neon Echo   | pop / happy          |    1.41 | energy 0.82 vs target 0.85 (+0.97) |
|     |                   |             |                      |         | popularity 78 vs target 90 (+0.44) |
+-----+-------------------+-------------+----------------------+---------+------------------------------------+
|   5 | Gym Hero          | Max Pulse   | pop / intense        |    1.41 | energy 0.93 vs target 0.85 (+0.92) |
|     |                   |             |                      |         | popularity 88 vs target 90 (+0.49) |
+-----+-------------------+-------------+----------------------+---------+------------------------------------+
```

### Diversity penalty on Chill Lofi (`--diversity`)

Compare with the Chill Lofi table above: Focus Flow (the second LoRoom song, also lofi) drops from #3 to #5 and Spacewalk Thoughts and Coffee Shop Stories move up.

```
Profile: Chill Lofi | mode: genre_first + diversity
Prefs: genre=lofi, mood=chill, energy=0.35, likes_acoustic=True, tags=['cozy', 'dreamy']
+-----+---------------------+----------------+-----------------+---------+------------------------------------------+
|   # | Title               | Artist         | Genre / Mood    |   Score | Reasons                                  |
+=====+=====================+================+=================+=========+==========================================+
|   1 | Library Rain        | Paper Lanterns | lofi / chill    |    5.18 | genre match (+2.00)                      |
|     |                     |                |                 |         | mood match (+1.00)                       |
|     |                     |                |                 |         | energy 0.35 vs target 0.35 (+1.00)       |
|     |                     |                |                 |         | acoustic fit (0.86 acousticness) (+0.43) |
|     |                     |                |                 |         | mood tags cozy/dreamy (+0.75)            |
+-----+---------------------+----------------+-----------------+---------+------------------------------------------+
|   2 | Midnight Coding     | LoRoom         | lofi / chill    |    4.16 | genre match (+2.00)                      |
|     |                     |                |                 |         | mood match (+1.00)                       |
|     |                     |                |                 |         | energy 0.42 vs target 0.35 (+0.93)       |
|     |                     |                |                 |         | acoustic fit (0.71 acousticness) (+0.35) |
|     |                     |                |                 |         | mood tags cozy (+0.38)                   |
|     |                     |                |                 |         | diversity: genre already picked (-0.50)  |
+-----+---------------------+----------------+-----------------+---------+------------------------------------------+
|   3 | Spacewalk Thoughts  | Orbit Bloom    | ambient / chill |    2.77 | mood match (+1.00)                       |
|     |                     |                |                 |         | energy 0.28 vs target 0.35 (+0.93)       |
|     |                     |                |                 |         | acoustic fit (0.92 acousticness) (+0.46) |
|     |                     |                |                 |         | mood tags dreamy (+0.38)                 |
+-----+---------------------+----------------+-----------------+---------+------------------------------------------+
|   4 | Coffee Shop Stories | Slow Stereo    | jazz / relaxed  |    1.80 | energy 0.37 vs target 0.35 (+0.98)       |
|     |                     |                |                 |         | acoustic fit (0.89 acousticness) (+0.45) |
|     |                     |                |                 |         | mood tags cozy (+0.38)                   |
+-----+---------------------+----------------+-----------------+---------+------------------------------------------+
|   5 | Focus Flow          | LoRoom         | lofi / focused  |    1.72 | genre match (+2.00)                      |
|     |                     |                |                 |         | energy 0.40 vs target 0.35 (+0.95)       |
|     |                     |                |                 |         | acoustic fit (0.78 acousticness) (+0.39) |
|     |                     |                |                 |         | mood tags cozy (+0.38)                   |
|     |                     |                |                 |         | diversity: artist already picked (-1.00) |
|     |                     |                |                 |         | diversity: genre already picked (-1.00)  |
+-----+---------------------+----------------+-----------------+---------+------------------------------------------+
```

---

## Experiments You Tried

**Weight shift (genre 2.0 to 1.0, energy 1.0 to 2.0) and feature removal (mood check off)**, run on the default pop/happy profile with `python -m src.main --experiment`:

```
EXPERIMENT on profile 'High-Energy Pop': {'genre': 'pop', 'mood': 'happy', 'energy': 0.8}

baseline (genre 2.0, mood 1.0, energy 1.0)
#    Title                    Genre / Mood       Score
---  -----------------------  -----------------  -------
1    Sunrise City             pop / happy        3.98
2    Gym Hero                 pop / intense      2.87
3    Glass Heart Confessions  pop / sad          2.55
4    Slap Bass Sunday         funk / happy       2.00
5    Rooftop Lights           indie pop / happy  1.96

weight shift (genre 1.0, energy 2.0)
#    Title                 Genre / Mood       Score
---  --------------------  -----------------  -------
1    Sunrise City          pop / happy        3.96
2    Slap Bass Sunday      funk / happy       3.00
3    Rooftop Lights        indie pop / happy  2.92
4    Starlight Hotline     k-pop / happy      2.84
5    Sunday Morning Choir  soul / happy       2.76

feature removal (mood check off)
#    Title                    Genre / Mood         Score
---  -----------------------  -------------------  -------
1    Sunrise City             pop / happy          2.98
2    Gym Hero                 pop / intense        2.87
3    Glass Heart Confessions  pop / sad            2.55
4    Slap Bass Sunday         funk / happy         1.00
5    Concrete Crown           hip hop / confident  0.98
```

- **Weight shift:** Gym Hero (pop, intense) and Glass Heart Confessions (pop, sad) fell out of the top 5, replaced by happy songs from funk, indie pop, k-pop, and soul. For a "happy pop" listener this feels *more* accurate, so the original genre weight was overpowering.
- **Feature removal:** Without the mood check, Sunrise City falls from 3.98 to 2.98 and the sad pop ballad stays at #3 because nothing penalizes the wrong mood. Songs with the wrong mood are now almost indistinguishable from songs with the right one. The change made results less accurate.
- **Mode switch on a conflicting profile (`pop`, `sad`, energy 0.9):** In `genre_first` the top 3 are all pop. In `mood_first` the top 3 are all sad songs (pop, blues, folk), and in `energy_focused` the three pop songs lead, followed by a blues song and a rock song. The same profile gives three different lists, which shows the weights *are* the recommender.

---

## Limitations and Risks

- The catalog is tiny: 30 songs, 25 genres, 15 moods, so most genres have only one song and a genre match is close to a lookup.
- Genre and mood are exact strings, so near-neighbors (`pop` vs `indie pop` vs `k-pop`, `sad` vs `melancholic`) get no credit at all.
- It cannot represent conflicting taste. A profile wanting high energy *and* a sad mood gets a quiet pop ballad first, because the genre and mood points outweigh the energy miss.
- Content-only scoring creates a filter bubble: the system never suggests anything outside the user's stated genre and mood unless the weights are changed.
- English dominates the catalog (17 of 30 songs, plus 10 instrumentals), and 2010s/2020s songs make up 19 of 30, so non-English and older music is underrepresented.
- There is no listening history, so nothing can learn from skips, replays, or other users.

See `model_card.md` for the full analysis.

---

## Optional Extensions Completed

- **Challenge 1, advanced song features:** `popularity`, `release_decade`, `mood_tags`, `language`, and `explicit` added to `data/songs.csv` and used in `score_song`.
- **Challenge 2, multiple scoring modes:** `genre_first`, `mood_first`, `energy_focused`, switchable with `--mode`; Strategy pattern documented in `ai_interactions.md`.
- **Challenge 3, diversity and fairness logic:** artist and genre repeat penalties via `--diversity`.
- **Challenge 4, visual summary table:** `tabulate` grid with a reasons column.

---

## Reflection

Read and complete `model_card.md`:

[**Model Card**](model_card.md)

<!-- TODO (Aaron): write 1 to 2 paragraphs in your own words:
  - what you learned about how recommenders turn data into predictions
  - where bias or unfairness could show up in systems like this
-->
