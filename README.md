# ShadowIntelX IQ

ShadowIntelX IQ is a local-first student practice platform for interview skills, reasoning, mental maths, memory, verbal ability, and focus. It keeps the original practice arenas and question banks, and adds saved performance insights, missions, adaptive difficulty, and combined boss battles.

## Run locally

Use Python 3.10 or newer.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
streamlit run app.py
```

The app opens in your browser. SQLite stores data in `shadowintelx.sqlite3` beside the app. Existing `high_scores.json` entries are imported once and the JSON file is kept unchanged. To choose a different database location, set `SHADOWINTELX_DB_PATH` before launching Streamlit.

Profiles are local display names, not login accounts. Attempts, XP, mission claims, badges, and progress remain on this device. The app does not send performance data anywhere unless a student explicitly requests optional model feedback.

## What the platform includes

- **Existing practice arenas:** role-based interviews, the 10-question logic arena, timed mental maths, four memory games, verbal practice, four focus games, the high-score board, and the progress page.
- **Skill DNA:** a six-area profile for logic, maths, memory, focus, verbal ability, and interview practice. The radar uses saved completed rounds; unmeasured skills stay unmeasured. The chart and trends update as rounds are completed.
- **Shadow Coach and Shadow Mirror:** a deterministic offline coach explains its recommendation using the student's saved results. The 7-day Mirror plan puts the weakest measured area first and gives unmeasured areas a baseline exercise.
- **Adaptive Challenge Engine:** recent saved accuracy sets the suggested difficulty for each arena. Students can still choose another level.
- **Mind Boss Battles:** a four-stage logic, maths, verbal, and interview challenge. The completed run stores its stage breakdown, total result, and XP once.
- **Shadow Missions:** daily and weekly practice goals, saved-day streaks, claim-once XP rewards, and badges. Ranks come from persisted XP.
- **Performance Intelligence:** history, accuracy, completion time, strongest and weakest practiced areas, next-step guidance, and a downloadable PDF (including an honest empty-data report).
- **Interview Simulator Pro:** HR, technical, and role-based question rounds with the existing offline keyword rubric.

## Optional model feedback

Offline coaching and all non-model features work without an API key. To enable model feedback, provide both `OPENAI_API_KEY` and `OPENAI_MODEL` in the environment that launches Streamlit. For a temporary PowerShell session:

```powershell
$env:OPENAI_API_KEY = "your-key"
$env:OPENAI_MODEL = "your-enabled-model"
streamlit run app.py
```

Never put the key in Python source, this README, or a committed file. Model feedback is only requested by a button. The interview answer is sent only after the student requests feedback; the coach sends only aggregate saved metrics. The integration uses the OpenAI Responses API with `store: false`. Without both environment variables, the app clearly uses its offline rubric and makes no model request.

## Checks

Run the built-in tests with:

```powershell
python -m unittest discover -s tests -v
```

## College presentation walkthrough

1. Introduce the problem: students need a practical way to build job-readiness and thinking skills and understand what to practice next.
2. Show the original arenas, then complete a short round to create a real saved result.
3. Open **Skill DNA & Shadow Coach** to show the measured skill profile and the coach's explanation. Point out that it reports missing data as unmeasured.
4. Show **Adaptive Challenge Engine** by returning to an arena: saved accuracy changes the suggested level, while the student remains in control.
5. Complete a **Mind Boss Battle**, then show its saved stage breakdown in Skill DNA and the performance report.
6. Open **Shadow Missions** to explain how completed rounds feed streaks, goals, one-time XP claims, badges, and ranks.
7. Export the **Performance Intelligence** PDF. Explain that it summarizes saved practice and does not claim to estimate IQ, diagnose ability, or predict hiring outcomes.
8. Explain the architecture: Streamlit presents the app, SQLite persists local profiles and results, pure Python rules calculate offline insights, and an optional Responses API call is isolated behind explicit user action and environment configuration.

The strongest demo is to practice first, then show the resulting data. A new profile starts empty by design; do not present sample values as a student's real performance.
