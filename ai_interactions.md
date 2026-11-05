# AI Interactions Log

This log covers the optional extensions (Challenges 1 to 4). The work was done with Claude Code (Sonnet 5.5) running in the repo as an agent that could read files, edit them, and run the CLI and tests.

---

## Agentic Workflow (Challenge 1: Advanced Song Features)

**What task did you give the agent?**

Implement the whole project, including every optional extension, starting from the forked starter. For Challenge 1 specifically: add five or more attributes the baseline data did not have, update `data/songs.csv`, and make the scoring logic use them.

**Prompts used:**

> I'm working on Project 3 from codepath ... Can you help me start with the fork ... Just help me implement everything, including extra credit since that will be important for me since I'll be losing some points now as well

The agent turned that into a plan: read the spec, clone the fork, inspect the starter, implement the required features, implement the extensions, then run and verify.

**What did the agent generate or change?**

- `data/songs.csv`: 20 new songs (30 total) across 25 genres, plus five new columns: `popularity` (0-100), `release_decade`, `mood_tags` (pipe-separated, e.g. `nostalgic|cozy`), `language`, `explicit`.
- `src/recommender.py`: `load_songs` parses the new columns (and still accepts a CSV with only the starter columns); `score_song` awards points for tag overlap, decade closeness, popularity closeness, language match, and subtracts points for explicit songs when the user disallows them; `Song` and `UserProfile` gained optional fields with defaults so the starter tests still pass.
- `src/main.py`: a "Clean Spanish Party" profile that exercises language, popularity, and the explicit filter.
- `tests/test_scoring.py`: tests for CSV parsing, the new scoring terms, and backward compatibility.

**What did you verify or fix manually?**

- Ran `python -m src.main --profile all` and read the reasons for each profile, checking that every shown point value adds up to the printed score (for example 4.99 for Fuego en la Calle = 2.0 + 1.0 + 0.99 + 0.50 + 0.50).
- Checked that unset optional preferences are skipped, so the original pop/happy profile still scores exactly 3.98 for Sunrise City.
- Caught and fixed three problems the agent's first draft had: `main.py` imported `from recommender import ...`, which fails under `python -m src.main`; `pytest` could not import `src` until a `pytest.ini` with `pythonpath = .` was added; and `tabulate` was turning `2.00` into `2` in the score column until `disable_numparse=True` was set.
- Dataset values were written by hand to be plausible, not measured, which is called out in the model card.
- My own note: the summary of the first draft looked fine every time, and it was only running it (`python -m src.main`, then `pytest`) that exposed the import, path, and formatting problems. I would rather run the thing early than trust a clean-sounding description of it.

---

## Design Pattern (Challenge 2: Multiple Scoring Modes)

**Which design pattern did you use?**

Strategy pattern, implemented as data: each ranking strategy is a frozen `ScoringMode` dataclass of weights (`genre_first`, `mood_first`, `energy_focused`) stored in a `SCORING_MODES` registry.

**How did AI help you brainstorm or implement it?**

The agent proposed two options: (a) a separate scoring function or class per mode, or (b) one scoring function that reads its weights from a swappable mode object. Option (b) was chosen because the three modes only differ in how many points each signal is worth, so writing three scoring functions would duplicate the same logic and let them drift apart. It also makes experiments cheap: the feature-removal experiment is just `dataclasses.replace(mode, mood=0.0)`.

**How does the pattern appear in your final code?**

- `ScoringMode` and `SCORING_MODES` in `src/recommender.py`.
- `score_song(user_prefs, song, mode=...)` and `recommend_songs(..., mode=...)` accept a mode name or a `ScoringMode` object; `get_mode` resolves it and raises a helpful `ValueError` for unknown names.
- `--mode` in `src/main.py` switches strategies from the command line.
- Tests in `tests/test_scoring.py` confirm that the same pair of songs ranks in opposite orders under `genre_first` and `mood_first`.

---

## Diversity and Fairness Logic (Challenge 3)

**Prompt idea given to the agent:** penalize a song's score if its artist is already in the top recommendations list.

**What was generated:** `_rank_diverse` in `src/recommender.py`, a greedy re-ranker. It picks the best song, then lowers every remaining song's score by 1.0 per already-picked song by the same artist and 0.5 per already-picked song of the same genre, and adds the penalty to that song's reasons so it is visible in the output.

**Verification:** with Chill Lofi, the second LoRoom song (Focus Flow) dropped from #3 to #5 and shows both penalties in the table. `--diversity` off leaves scores identical (tested). The genre penalty was added on top of the artist penalty because the prompt only covered artists, and genre was the bigger problem in this catalog.

---

## Visual Summary Table (Challenge 4)

`tabulate` (added to `requirements.txt`) renders a grid with rank, title, artist, genre/mood, score, and a multi-line reasons column. Verified by reading the output for all seven profiles.
