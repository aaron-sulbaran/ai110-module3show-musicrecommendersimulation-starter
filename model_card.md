# 🎧 Model Card: Music Recommender Simulation

## 1. Model Name

**VibeFinder 1.0**

---

## 2. Intended Use

VibeFinder suggests the top few songs from a small catalog for one user "taste profile". Each suggestion comes with the exact reasons it scored well.

- It assumes the user can describe their taste with a favorite genre, a favorite mood, and a target energy level (plus a few optional extras).
- It is built for classroom exploration, not for real listeners.

**Not intended for:** real music apps, real user data, or any decision that affects people. The catalog is far too small and the matching is too rigid. It should not be used to claim that some music is "better" or to judge a person's taste.

---

## 3. How the Model Works

Think of a judge holding a scorecard. For each song, the judge awards points:

- **Genre:** 2 points if the song's genre is exactly what the user likes.
- **Mood:** 1 point if the mood is exactly what the user likes.
- **Energy:** up to 1 point. A song gets full points when its energy equals the user's target, and fewer points the further away it is, in either direction. A very high-energy song does not win just for being high energy.
- **Small extras:** up to half a point each for acoustic fit, matching a target valence, release decade, popularity, and language, and up to three quarters of a point for shared mood tags. A song that is explicit loses 1 point if the user says no explicit songs.

Extras only count when the user actually set that preference. After every song has a score, the songs are sorted from highest to lowest and the top few are shown with their reasons.

There are three scoring "modes" that change the point values. `genre_first` is the default. `mood_first` makes mood worth 2 and genre worth 1. `energy_focused` makes energy worth 2 and genre worth 1. A "diversity" switch lowers the score of a song if the same artist (-1.0) or genre (-0.5) is already in the list.

**Changes from the starter:** the starter returned placeholders. I added CSV loading with real numbers, the scoring rules above, ranking, explanations, modes, the diversity penalty, a table display, and tests.

---

## 4. Data

- **Size:** 30 songs. The starter had 10; I added 20 more.
- **Genres:** 25 different genres. Only pop (3), lofi (3), and ambient (2) appear more than once.
- **Moods:** 15 different moods. Happy (5) and relaxed (4) are the most common.
- **Features:** genre, mood, energy, tempo, valence, danceability, acousticness, plus five I added: popularity, release decade, mood tags, language, explicit flag.
- **Limits:** 17 songs are in English and 10 are instrumental, with one each in Spanish, Korean, and Portuguese. 19 of 30 songs are from the 2010s or 2020s. Moods use single words, so `sad` and `melancholic` are treated as different things.
- **Missing from the data:** lyrics, artist popularity over time, how people actually listen (skips, replays, playlists), and cultural context. All values were written by hand, not measured from real audio.

---

## 5. Strengths

- **Clear profiles work well.** Chill Lofi returns the three lofi songs first, then ambient and jazz with matching energy. Deep Intense Rock puts Storm Runner first with 5.69 points, and the next two songs are also intense with very high energy.
- **Every result is explainable.** Each point is listed, so I can see exactly why a song ranked where it did. This made debugging the weights easy.
- **Energy closeness behaves the way I wanted.** A 0.35-energy song is not rewarded for a 0.9-energy target just for being "different", and a very high-energy song does not win a low-energy profile.
- **The Clean Spanish Party profile** shows the extras working: the only Spanish latin song wins by a wide margin (4.99 vs 2.22) because every signal agrees.

---

## 6. Limitations and Bias

The strongest bias I found is that **genre overpowers everything else**. In the default "happy pop" test, Gym Hero (pop, intense) and Glass Heart Confessions (pop, sad) take spots #2 and #3 even though neither is happy, because the 2.0 genre bonus is bigger than the mood bonus and the energy miss combined. A person who wants upbeat pop would be surprised to see a quiet heartbreak ballad third. When I doubled energy and halved genre, those two songs left the top 5 and were replaced by happy songs from funk, indie pop, k-pop, and soul.

Related weaknesses:

- **Exact word matching.** `pop` does not match `indie pop` or `k-pop`, and `sad` does not match `melancholic`, so near neighbors get no credit. The "Genre Missing From Catalog" test (opera) fell back to energy only.
- **Conflicting tastes get flattened.** A profile with high energy (0.9) and a sad mood returns a 0.35-energy ballad first. No song in the catalog is both, and the system has no way to say "nothing fits".
- **Tiny catalog, hidden filter bubble.** Most genres have one song, so a genre match often means "the only song of that genre". With genre weighted so heavily, users never see anything outside their stated genre unless it is a mood or energy near-match.
- **Underrepresented listeners.** English and recent music dominate, so someone who loves older or non-English music gets fewer meaningful matches.

---

## 7. Evaluation

**Profiles tested (7):** High-Energy Pop, Chill Lofi, Deep Intense Rock, and four more designed to trick the scoring: Conflicting (high energy + sad), Genre Missing From Catalog (opera), Middle Of The Road (only an energy preference), and Clean Spanish Party (language, popularity, no explicit). The full top-5 tables are in `README.md`. I also ran 30 automated tests.

**What I looked for:** whether the top results matched my own sense of the vibe, whether the same song kept appearing everywhere, and whether the scores added up to the reasons shown.

**Profile-versus-profile comparisons:**

- **High-Energy Pop vs Chill Lofi:** The pop list is led by loud, danceable songs (energy 0.8 or higher) and the lofi list by quiet, acoustic ones (energy around 0.35 to 0.42). The two lists share no songs. That makes sense, because the profiles sit at opposite ends of the energy and acousticness scales.
- **Chill Lofi vs Deep Intense Rock:** Lofi rewards high acousticness and cozy tags; rock rewards low acousticness and aggressive tags. Spacewalk Thoughts (ambient) cracks the lofi top 4 mostly on its chill mood match, while Gym Hero (pop) takes #2 for rock on mood and energy even though it is pop, which shows how much mood and energy matter when the genre is a single song.
- **High-Energy Pop vs Deep Intense Rock:** Both want high energy, so Gym Hero appears in both lists. In the pop list it ranks second because of its genre; in the rock list it ranks second because of its intense mood and near-perfect energy. This is why "Gym Hero" keeps showing up for people who only wanted happy pop: it is pop *and* loud.
- **High-Energy Pop vs Conflicting (pop, sad, energy 0.9):** Same genre, but now the sad ballad Glass Heart Confessions jumps from #3 to #1 because it matches both genre and mood. The high-energy part of the profile is largely ignored, which is the intended weakness this test was built to expose.
- **Genre Missing From Catalog vs Middle Of The Road:** With no genre match available, the first list is led by the one romantic song (Velvet Hours) and the rest are chosen by energy alone. Middle Of The Road is energy only, so it returns very similar scores (0.92 to 0.98) with almost no spread. When the only signal is one number, the ranking is nearly arbitrary.

**Experiments:** (1) Weight shift, genre 2.0 to 1.0 and energy 1.0 to 2.0: the results got better for a happy-pop listener. (2) Feature removal, mood off: the results got worse, since wrong-mood songs were no longer separated from right-mood ones. (3) Mode switching on the conflicting profile: three modes gave three different top lists. (4) Diversity penalty on Chill Lofi: the second LoRoom song dropped from #3 to #5.

**What surprised me:** how much a single weight changes everything, and that the "wrong" song (a sad ballad) could look correct on paper because the explanation list was all true.

---

## 8. Future Work

- **Soft genre and mood matching.** Group related genres (pop, indie pop, k-pop) and moods (sad, melancholic) and give partial credit instead of exact-match only.
- **Handle conflicts honestly.** Warn the user when the best match is weak ("no song fits all of your preferences") instead of showing it as a confident answer.
- **A bigger, more balanced catalog and real listening data,** so collaborative filtering can sit next to content-based scoring and cold-start songs can still be recommended.
- **Learn the weights** from skips and replays instead of choosing 2.0 / 1.0 / 1.0 by hand.

---

## 9. Personal Reflection

<!-- TODO (Aaron): write this in your own words. Prompts from the assignment:
  - What was your biggest learning moment during this project?
  - How did using AI tools help you, and when did you need to double-check them?
  - What surprised you about how simple algorithms can still "feel" like recommendations?
  - What would you try next if you extended this project?
Facts to draw on are in "Projects/Project 3/Reflection fact sheet (Claude, 2026-11-04).md". -->
