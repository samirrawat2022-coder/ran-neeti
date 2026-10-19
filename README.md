# RAN-NEETI — Unified AI Prediction Lab

A cloud-deployable Streamlit research prototype for historical football and T20 cricket predictions, plus source-linked fictional-character lookup.

## Included files

- `app.py` — complete Streamlit application
- `requirements.txt` — Python packages installed by Streamlit Cloud
- `.streamlit/config.toml` — dark futuristic theme and cloud-safe settings
- `.gitignore` — excludes secrets and local Python cache
- `README.md` — deployment instructions

## Deploy online (no local Python installation)

### A. Create a GitHub repository

1. Sign in at https://github.com/ and choose **New repository**.
2. Name it `ran-neeti`.
3. Check **Add a README file** before clicking **Create repository**. This creates the first commit and branch (usually `main`).

### B. Upload every project file

1. Open the repository's main **Code** page.
2. Choose **Add file → Upload files** (or the `uploading an existing file` link if the repository is empty).
3. Extract this ZIP on your computer.
4. Upload the files *inside* the extracted folder to the repository root. Upload `app.py`, `requirements.txt`, `README.md`, `.gitignore`, and the `.streamlit` folder containing `config.toml`.
5. Make sure `app.py` is visible on the repository's main page, not inside another `RAN_NEETI` folder.
6. Click **Commit changes**.

### C. Deploy on Streamlit Community Cloud

1. Open https://share.streamlit.io/ and sign in with GitHub.
2. Choose **Create app**.
3. Select your repository and the exact branch shown in GitHub (usually `main`; use `master` if that is what your repository shows).
4. Set **Main file path** to `app.py`.
5. Click **Deploy** and wait for dependency installation and startup.

## If the branch does not exist

- First ensure the files were committed. An uncommitted upload does not create a branch.
- On GitHub, open the repository and look at the branch dropdown above the file list.
- Select the exact branch name shown there in Streamlit. Do not type `main` if GitHub shows a different name.
- If the repository is empty, create a README or upload files and commit them first.

## Current capabilities and honest limitations

- **Football:** fetches historical English Premier League results from Football-Data.co.uk, builds pre-match rolling-form features, trains a Logistic Regression baseline and calculates a chronological holdout evaluation at runtime.
- **Cricket:** fetches historical T20 results from Cricsheet, builds rolling team-form features, trains a Logistic Regression baseline and calculates evaluation metrics at runtime.
- **Anime/fiction:** searches Wikipedia and displays source-linked summaries. This version does **not** include a fully generative LLM battle-judging engine and does not claim fictional win probabilities are scientifically calibrated.
- **No API key is required** for the included functions. A generative AI provider integration must be implemented separately before adding an API key; adding a key alone cannot activate code that is not present.

## Research integrity

- Metrics are computed at runtime and are not hard-coded.
- Save dated dataset snapshots and retrieval dates for reproducible thesis experiments because public datasets can change.
- The temporal holdout is a baseline research prototype and should be critically reviewed before thesis reporting.
- Predictions are not betting advice. The app does not fetch live odds, live scores, or injury updates.
