# RAN-NEETI — AI Prediction Lab

A deployable Streamlit research prototype for multi-sport matchup exploration, tactical win routes/counters, and anime character metadata lookup.

## What is included
- Responsive dark dashboard with five workspaces.
- Best-effort public ESPN scoreboard retrieval for selected leagues.
- Exploratory Elo-style matchup estimate **only when** returned records contain completed head-to-head results for both named sides.
- Sport-specific general major-moves playbooks with counters.
- Jikan API character metadata search.
- Evidence-input workspace for conditional fictional battle analysis.
- Explicit data/model status and beginner deployment guide.

## Important limitations
This is **not** a validated production all-sports AI prediction engine. The ESPN public endpoints may not support every listed sport/league consistently. No sport-specific trained model, historical backtest, calibrated probability model, automated event-level tactics detector, or canonical anime battle reasoner is claimed as complete. Missing evidence results in no numeric prediction. Do not use the prototype for betting decisions.

## Run locally (optional)
```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Deploy without installing Python on your computer
1. Extract this ZIP.
2. Create a GitHub repository called `ran-neeti`.
3. Upload `app.py`, `requirements.txt`, and `README.md` to the repository root.
4. Open https://share.streamlit.io and sign in with GitHub.
5. Create app → select the repository, branch `main`, and file `app.py`.
6. Deploy and wait for the public URL.

## Data sources
- ESPN public scoreboard endpoints (best effort; availability varies): `https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/scoreboard`
- Jikan API for public anime character metadata: `https://api.jikan.moe/v4/characters`

Check each source's terms, rate limits and permitted use before public or commercial deployment.
