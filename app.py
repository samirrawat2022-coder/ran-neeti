import math
import requests
import streamlit as st
from datetime import datetime, timezone

st.set_page_config(page_title="RAN-NEETI | AI Prediction Lab", page_icon="⚔️", layout="wide", initial_sidebar_state="expanded")

SPORTS = {
    "Football": {"sport":"soccer", "league":"eng.1", "label":"English Premier League", "moves":[("High pressing", "Force rushed passes and recover the ball high up the pitch.", "Bypass the first press with quick switches and runs into space."), ("Counter-attack", "Attack quickly after winning possession while the defence is unbalanced.", "Keep defensive cover and avoid losing the ball centrally."), ("Set pieces", "Corners and free kicks can create high-value chances.", "Use organised marking and goalkeeper communication.")]},
    "Basketball": {"sport":"basketball", "league":"nba", "label":"NBA", "moves":[("Pick-and-roll", "Create a two-on-two decision and attack a mismatch.", "Switch, hedge or drop depending on personnel."), ("Three-point volume", "Stretch the defence and create high-value perimeter shots.", "Close out under control and protect the paint."), ("Transition offence", "Score before the defence sets.", "Prioritise floor balance and sprint back.")]},
    "Baseball": {"sport":"baseball", "league":"mlb", "label":"MLB", "moves":[("Pitch sequencing", "Change pitch type and location to disrupt timing.", "Identify patterns and avoid predictable counts."), ("Bullpen matchup", "Use a reliever whose handedness and pitch profile suit the batter.", "Counter with platoon-aware batting decisions."), ("Baserunning pressure", "Force defensive decisions and create extra-base chances.", "Quick releases, pickoff awareness and smart positioning.")]},
    "American Football": {"sport":"football", "league":"nfl", "label":"NFL", "moves":[("Play-action", "Sell the run to create passing windows.", "Disciplined linebackers and coverage rotations reduce the effect."), ("Blitz pressure", "Disrupt the quarterback before routes develop.", "Hot routes, protection shifts and quick releases."), ("Red-zone execution", "Convert limited-field possessions into touchdowns.", "Tight coverage and disciplined gap responsibility.")]},
    "Ice Hockey": {"sport":"hockey", "league":"nhl", "label":"NHL", "moves":[("Forecheck", "Pressure the puck carrier and force turnovers.", "Quick support passes and controlled exits."), ("Power play", "Create passing lanes and overload a defensive box.", "Keep lanes clear and pressure the puck, not just the shooter."), ("Goaltender pull", "Add an extra attacker late when trailing.", "Clear the zone and target the empty net when safe.")]},
    "Tennis": {"sport":"tennis", "league":"atp", "label":"ATP", "moves":[("Serve + first ball", "Use the serve to dictate the next shot.", "Return deep and make the server play an extra ball."), ("Cross-court pressure", "Move the opponent laterally and open the court.", "Recover to a balanced position and change direction selectively."), ("Drop shot variation", "Punish deep positioning and disrupt rhythm.", "Read contact early and move forward decisively.")]},
    "Cricket": {"sport":"cricket", "league":"icc", "label":"Cricket", "moves":[("Powerplay intent", "Use fielding restrictions to score quickly while managing risk.", "Vary pace/line and target the stumps with field-aware plans."), ("Middle-over squeeze", "Control scoring through matchups and dot-ball pressure.", "Rotate strike, target weaker matchups and avoid predictable shots."), ("Death-over execution", "Yorkers, slower balls and boundary options decide late overs.", "Pre-plan scoring zones and adapt to length changes.")]},
    "Rugby": {"sport":"rugby", "league":"all.rugby.union", "label":"Rugby Union", "moves":[("Territorial kicking", "Gain field position and pressure the opponent's exit.", "Secure the catch and return with a planned chase."), ("Set-piece platform", "Create stable possession from scrums and lineouts.", "Contest timing and defend the next phase."), ("Wide phase attack", "Stretch the defensive line and create overlap.", "Slide together and communicate edge assignments.")]},
    "Volleyball": {"sport":"volleyball", "league":"fivb", "label":"Volleyball", "moves":[("Serve targeting", "Stress a weak passer and disrupt the setter's options.", "Use clear passing lanes and adjust serve-receive shape."), ("Quick middle attack", "Exploit the block before it closes.", "Read the setter and commit block with disciplined timing."), ("Block-defence system", "Turn attacker tendencies into controlled digs and blocks.", "Vary approach, shots and attack tempo.")]},
    "Badminton": {"sport":"badminton", "league":"bwf", "label":"Badminton", "moves":[("Length and height control", "Push the opponent deep, then open the front court.", "Recover centrally and read the racket early."), ("Smash follow-up", "Use a smash to force a weak reply and finish the rally.", "Defend compactly and vary block/lift choices."), ("Serve-return pressure", "Win the first three shots and seize initiative.", "Keep the return low and vary placement.")]},
    "Table Tennis": {"sport":"table-tennis", "league":"ittf", "label":"Table Tennis", "moves":[("Spin variation", "Change rotation to force errors and weak returns.", "Read racket angle and contact point."), ("Short game", "Keep the ball short to limit attacking options.", "Use a controlled flick or push to create depth."), ("Wide placement", "Move the opponent away from recovery position.", "Anticipate patterns and recover quickly.")]},
    "Field Hockey": {"sport":"hockey", "league":"fih", "label":"Field Hockey", "moves":[("Pressing trap", "Steer build-up into a sideline or predictable lane.", "Switch play quickly and use a supporting outlet."), ("Circle entries", "Create controlled entries into the scoring circle.", "Protect central lanes and force low-angle attempts."), ("Penalty corners", "Use rehearsed routines for high-value shots.", "Disrupt injection timing and set defensive roles.")]},
    "Motorsport": {"sport":"racing", "league":"f1", "label":"Formula 1", "moves":[("Undercut", "Pit earlier to use fresh tyres and gain time on track.", "Extend the stint when tyre life and traffic allow."), ("DRS / overtaking setup", "Use a speed advantage on suitable straights.", "Defend legally and prioritise exit speed before the straight."), ("Tyre strategy", "Balance pace, degradation and track position.", "Force a strategic response through pace and pit windows.")]},
    "Combat Sports": {"sport":"mma", "league":"ufc", "label":"MMA / UFC", "moves":[("Distance management", "Control range to land safely and limit counters.", "Feints, angle changes and pressure entries."), ("Wrestling chain", "Link takedown attempts until a defensive reaction opens another.", "Underhooks, hips back and disciplined cage work."), ("Cardio and pace", "Sustain output and make later rounds decisive.", "Manage exchanges and force inefficient movement.")]},
}

SPORTS["Esports"] = {"sport":"esports", "league":"lol", "label":"League of Legends (sample feed varies)", "moves":[("Objective control", "Set vision and position before major neutral objectives.", "Contest vision early and trade objectives when unfavourable."), ("Draft synergy", "Pick a composition whose win condition is clear.", "Deny comfort picks and draft tools that disrupt combos."), ("Tempo rotation", "Convert lane priority into map pressure.", "Track rotations and avoid isolated fights.")]}

API_BASE = "https://site.api.espn.com/apis/site/v2/sports"

@st.cache_data(ttl=300, show_spinner=False)
def fetch_scoreboard(sport_key, league_key):
    url = f"{API_BASE}/{sport_key}/{league_key}/scoreboard"
    r = requests.get(url, timeout=12, headers={"User-Agent":"RAN-NEETI educational prototype"})
    r.raise_for_status()
    payload = r.json()
    events = []
    for event in payload.get("events", [])[:30]:
        comps = event.get("competitions", [{}])[0].get("competitors", [])
        teams = []
        for c in comps:
            team = c.get("team", {})
            teams.append({"name": team.get("displayName", "Unknown team"), "score": c.get("score"), "winner": c.get("winner"), "homeAway": c.get("homeAway"), "record": (c.get("records") or [{}])[0].get("summary", "")})
        status = event.get("status", {}).get("type", {}).get("description", "Unknown status")
        events.append({"name": event.get("name", "Event"), "date": event.get("date", ""), "status": status, "teams": teams, "id": event.get("id")})
    return {"events": events, "source": url, "league": payload.get("leagues", [{}])[0].get("name", league_key), "fetched_at": datetime.now(timezone.utc).isoformat()}

def elo_probability(rating_a, rating_b):
    return 1 / (1 + 10 ** ((rating_b - rating_a) / 400))

def estimate_from_recent_events(events, name_a, name_b):
    """Only estimate from observed results if both names appear in returned events; otherwise return None."""
    scores = {name_a.lower(): 1500.0, name_b.lower(): 1500.0}
    counts = {name_a.lower(): 0, name_b.lower(): 0}
    target = {name_a.lower(), name_b.lower()}
    for ev in events:
        teams = ev.get("teams", [])
        if len(teams) != 2 or not all(t.get("score") is not None for t in teams):
            continue
        n0, n1 = teams[0]["name"].lower(), teams[1]["name"].lower()
        if n0 not in target or n1 not in target:
            continue
        try:
            s0, s1 = float(teams[0]["score"]), float(teams[1]["score"])
        except (TypeError, ValueError):
            continue
        exp0 = elo_probability(scores[n0], scores[n1])
        actual0 = 1 if s0 > s1 else (0.5 if s0 == s1 else 0)
        scores[n0] += 24 * (actual0 - exp0)
        scores[n1] += 24 * ((1 - actual0) - (1 - exp0))
        counts[n0] += 1; counts[n1] += 1
    if not counts[name_a.lower()] or not counts[name_b.lower()]:
        return None
    return elo_probability(scores[name_a.lower()], scores[name_b.lower()]), scores, counts

def fetch_anime(query):
    url = "https://api.jikan.moe/v4/characters"
    r = requests.get(url, params={"q": query, "limit": 5}, timeout=12, headers={"User-Agent":"RAN-NEETI educational prototype"})
    r.raise_for_status()
    return r.json().get("data", [])

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Manrope:wght@400;500;600;700;800&display=swap');
:root { color-scheme: dark; }
html, body, [class*="css"] { font-family: 'Manrope', sans-serif; }
.stApp { background: radial-gradient(ellipse at 82% 0%, #142b40 0%, #0a111b 42%, #070b12 100%); color: #ecf3ff; }
.block-container { padding-top: 1.8rem; max-width: 1400px; }
.hero { border: 1px solid #26384d; border-radius: 24px; padding: 30px; background: linear-gradient(120deg, rgba(17,31,47,.96), rgba(10,17,27,.9)); position: relative; overflow: hidden; }
.hero:after { content:'⚔'; position:absolute; right:5%; top:-36px; font-size:180px; color:rgba(67,220,183,.06); transform:rotate(-18deg); }
.eyebrow { color:#55e4c1; font: 500 11px 'DM Mono',monospace; letter-spacing:2px; text-transform:uppercase; }
.hero h1 { font-size:clamp(32px,5vw,54px); line-height:1.03; letter-spacing:-2px; margin:12px 0; color:#f4f8ff; }
.hero p { max-width:720px; color:#a9b9cb; font-size:15px; line-height:1.7; }
.pill { display:inline-block; border:1px solid #31536a; border-radius:999px; color:#a6f4e4; padding:6px 10px; font-size:11px; margin:4px 5px 0 0; background:#112b33; }
.metric { border:1px solid #25364a; background:rgba(15,27,41,.85); border-radius:16px; padding:18px; min-height:112px; }
.metric .num { color:#56e4c2; font-size:27px; font-weight:800; letter-spacing:-1px; }
.metric .cap { color:#8fa4ba; font-size:11px; text-transform:uppercase; letter-spacing:1px; }
.panel { border:1px solid #25364a; border-radius:18px; background:rgba(12,21,32,.78); padding:20px; margin:12px 0; }
.panel h3 { margin-top:0; color:#edf5ff; }
.smallmuted { color:#8fa4ba; font-size:12px; }
.move { border-left:3px solid #56e4c2; background:#101f2d; padding:12px 14px; border-radius:0 10px 10px 0; margin:9px 0; }
.move b { color:#eaf5ff; }
.move p { margin:5px 0; color:#a8bacd; font-size:13px; }
[data-testid="stSidebar"] { background:#080e17; border-right:1px solid #1c2a3b; }
.stButton>button { border-radius:10px; border:1px solid #2d5a60; background:#45d8b6; color:#06120f; font-weight:800; min-height:44px; }
.stButton>button:hover { border-color:#72ffe1; background:#65f0d0; color:#06120f; }
.stTextInput input, .stSelectbox div[data-baseweb="select"], .stTextArea textarea { background:#0d1825; }
hr { border-color:#243449; }
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### ⚔️ RAN-NEETI")
    st.caption("AI PREDICTION LAB · PROTOTYPE")
    page = st.radio("WORKSPACE", ["Matchup Lab", "Major Moves Intelligence", "Anime / Fiction Lab", "Data & Model Status", "Deployment Guide"], label_visibility="visible")
    st.divider()
    st.markdown("**Data policy**")
    st.caption("Public sources only. Missing data stays missing; no invented scores or accuracy claims.")
    st.caption("Prototype v1.0 · Educational use")

st.markdown("""
<div class="hero">
  <div class="eyebrow">Unified AI Prediction Lab / 001</div>
  <h1>RAN-NEETI<span style="color:#55e4c1">.</span></h1>
  <p>Predict the outcome. Understand the win condition. Explore the decisive moves, counters and turning points — across real-world sports and fictional battles.</p>
  <span class="pill">MULTI-SPORT</span><span class="pill">SOURCE-AWARE</span><span class="pill">MAJOR MOVES</span><span class="pill">ANIME / FICTION</span>
</div>
""", unsafe_allow_html=True)

m1, m2, m3, m4 = st.columns(4)
for col, num, cap in [(m1,"14+","SPORT CATEGORIES"),(m2,"LIVE*","PUBLIC DATA FETCH"),(m3,"WHY","WIN-CONDITION ANALYSIS"),(m4,"NO FAKE","EVIDENCE-FIRST OUTPUT")]:
    with col: st.markdown(f'<div class="metric"><div class="num">{num}</div><div class="cap">{cap}</div></div>', unsafe_allow_html=True)
st.caption("*Live data depends on the selected league endpoint being reachable and returning usable records. Available feeds vary by sport and region.")

if page == "Matchup Lab":
    st.markdown("## Matchup Lab")
    st.markdown('<p class="smallmuted">Choose a sport and matchup. Fetch public scoreboard data where supported, then review the data before trusting any estimate.</p>', unsafe_allow_html=True)
    left, right = st.columns([1,1])
    with left:
        sport_name = st.selectbox("SPORT", list(SPORTS.keys()), index=0)
        a = st.text_input("SIDE / TEAM A", "Arsenal")
        b = st.text_input("SIDE / TEAM B", "Liverpool")
        advanced = st.checkbox("Show data-source and model details", value=True)
    with right:
        cfg = SPORTS[sport_name]
        st.markdown(f'<div class="panel"><div class="eyebrow">SELECTED DOMAIN</div><h3>{sport_name}</h3><p>{cfg["label"]}</p><p class="smallmuted">The data connector is a best-effort public feed. A selectable sport does not mean a validated production model exists for that sport.</p></div>', unsafe_allow_html=True)
        run = st.button("⚡ FETCH DATA & ANALYSE", use_container_width=True)
    if run:
        if not a.strip() or not b.strip() or a.strip().lower() == b.strip().lower():
            st.error("Enter two different team/player names.")
        else:
            with st.spinner("Contacting public data endpoint…"):
                try:
                    result = fetch_scoreboard(cfg["sport"], cfg["league"])
                    st.success(f"Source responded: {result['league']} · {len(result['events'])} event(s) returned")
                    if advanced:
                        st.code(result["source"], language="text")
                        st.caption(f"Fetched at: {result['fetched_at']} · Cached for 5 minutes")
                    estimate = estimate_from_recent_events(result["events"], a.strip(), b.strip())
                    if estimate:
                        p, ratings, counts = estimate
                        st.markdown("### Exploratory outcome estimate")
                        c1,c2 = st.columns(2)
                        with c1: st.markdown(f'<div class="metric"><div class="num">{p*100:.1f}%</div><div class="cap">{a} estimated win probability</div></div>', unsafe_allow_html=True)
                        with c2: st.markdown(f'<div class="metric"><div class="num">{(1-p)*100:.1f}%</div><div class="cap">{b} estimated win probability</div></div>', unsafe_allow_html=True)
                        st.warning("Exploratory Elo-style estimate only. It uses a tiny sample of matching events returned by this feed, not a validated sport-specific production model. Do not interpret it as betting advice.")
                        st.write(f"Observed matching games: {a} = {counts[a.lower()]}, {b} = {counts[b.lower()]}. Starting ratings are equal; rating updates use K=24.")
                    else:
                        st.info("The feed responded, but it did not include completed head-to-head results for both names. A reliable probability cannot be calculated from the retrieved data. Try exact official team names or inspect the event list below.")
                    st.markdown("### Returned events / data preview")
                    if result["events"]:
                        rows=[]
                        for ev in result["events"]:
                            teams = ev["teams"]
                            desc = " vs ".join([f"{t['name']} ({t.get('score') if t.get('score') is not None else '—'})" for t in teams]) or ev["name"]
                            rows.append({"Event":ev["name"],"Date":ev["date"],"Status":ev["status"],"Score / sides":desc})
                        st.dataframe(rows, use_container_width=True, hide_index=True)
                    else:
                        st.info("No events returned by this endpoint right now.")
                except Exception as e:
                    st.error("This public feed could not be fetched or parsed right now.")
                    st.caption(f"Technical detail: {type(e).__name__}: {e}")
                    st.info("No prediction was generated. Check internet access, endpoint support, or try another sport. Some feeds may not support this competition.")
    else:
        st.markdown('<div class="panel"><h3>How the analysis works</h3><p>01 · Identify the sport and matchup</p><p>02 · Fetch public scoreboard records when available</p><p>03 · Check whether actual comparable results exist</p><p>04 · Estimate only when there is enough relevant data</p><p>05 · Explain major win routes, counters and uncertainty</p></div>', unsafe_allow_html=True)

elif page == "Major Moves Intelligence":
    st.markdown("## Major Moves Intelligence")
    st.markdown("Understand what could decide the contest — and what the opponent can do about it.")
    chosen = st.selectbox("Choose sport for tactical playbook", list(SPORTS.keys()))
    for i,(name,desc,counter) in enumerate(SPORTS[chosen]["moves"],1):
        st.markdown(f'<div class="move"><b>{i:02d} · {name}</b><p><b>Why it matters:</b> {desc}</p><p><b>Possible counter:</b> {counter}</p></div>', unsafe_allow_html=True)
    st.markdown('<div class="panel"><h3>Turning-point checklist</h3><p>• Matchup / player availability and recent form</p><p>• Tactical or stylistic mismatch</p><p>• Key phases: start, middle, late-game / clutch phase</p><p>• Resource management: stamina, substitutions, bullpen, tyres or cooldowns as relevant</p><p>• What-if scenario: what changes if the primary win route is neutralised?</p><p class="smallmuted">This playbook is a general tactical reference, not a claim that these moves were detected in a specific live match. Match-specific analysis needs event-level data.</p></div>', unsafe_allow_html=True)

elif page == "Anime / Fiction Lab":
    st.markdown("## Anime / Fiction Lab")
    st.markdown("Search public character metadata, then structure a source-aware battle analysis. Metadata lookup alone does not verify combat feats or determine a canon winner.")
    q = st.text_input("CHARACTER SEARCH", "Naruto")
    if st.button("🔎 LOOK UP CHARACTER", use_container_width=True):
        try:
            chars = fetch_anime(q.strip())
            if not chars: st.info("No matching characters returned. Try a shorter or alternate name.")
            for ch in chars:
                with st.expander(f"{ch.get('name','Unknown')} · {ch.get('name_kanji') or 'Japanese name not listed'}"):
                    image = (ch.get("images") or {}).get("jpg", {}).get("image_url")
                    if image: st.image(image, width=140)
                    st.write(ch.get("about") or "No biography returned by the source.")
                    st.link_button("Open source profile", ch.get("url", "https://jikan.moe/"))
            st.caption("Metadata source: Jikan API, which indexes MyAnimeList data. Results can be incomplete and are not an official canon authority.")
        except Exception as e:
            st.error("Character metadata could not be fetched at the moment.")
            st.caption(f"Technical detail: {type(e).__name__}: {e}")
    st.markdown("### Battle analysis workspace")
    ca, cb = st.columns(2)
    with ca: char_a = st.text_input("FIGHTER A", "Naruto Uzumaki")
    with cb: char_b = st.text_input("FIGHTER B", "Ichigo Kurosaki")
    feats_a = st.text_area("A — source-backed feats / abilities", placeholder="Paste feats with episode/chapter/source links; include conditions and limitations.")
    feats_b = st.text_area("B — source-backed feats / abilities", placeholder="Paste feats with episode/chapter/source links; include conditions and limitations.")
    if st.button("BUILD CONDITIONAL BATTLE REPORT", use_container_width=True):
        if not feats_a.strip() or not feats_b.strip():
            st.warning("Add source-backed feats for both fighters first. The app will not invent signature moves or a winner from names alone.")
        else:
            st.markdown("### Evidence comparison")
            st.write(f"**Fighter A:** {char_a} — supplied evidence has {len(feats_a.split())} words.")
            st.write(f"**Fighter B:** {char_b} — supplied evidence has {len(feats_b.split())} words.")
            st.info("This prototype organises user-supplied evidence only; it does not yet run a validated fictional-battle reasoning model. Compare demonstrated speed, range, durability, stamina, resistance, activation limits and proven counters, then report conditional win routes rather than an unsupported numeric probability.")
            st.markdown("**Report template:** likely win condition · top 3 decisive moves · counters · turning points · weaknesses · evidence gaps · what-if outcome")

elif page == "Data & Model Status":
    st.markdown("## Data & Model Status")
    st.markdown("A transparent inventory of what this version actually does.")
    status = [
        ("Responsive Streamlit dashboard", "Implemented", "Navigation, matchup input, tactical playbooks and report areas."),
        ("Public scoreboard retrieval", "Best effort", "ESPN public endpoints for selected leagues; endpoint support and returned events vary."),
        ("Outcome probability", "Limited baseline", "Only an exploratory Elo-style estimate when matching completed results are found for both sides."),
        ("Sport-specific trained models", "Not yet", "Separate curated datasets, training, backtesting and calibration are still required."),
        ("Major moves and counters", "General playbooks", "Sport-specific examples are available; automatic event-level detection is pending."),
        ("Anime metadata lookup", "Implemented", "Jikan character search; source metadata is not the same as verified combat evidence."),
        ("Anime battle reasoning model", "Not yet", "Requires canonical source collection, evidence extraction and systematic evaluation."),
        ("Production reliability", "Not yet", "Needs monitoring, API policy review, caching, tests and deployment validation."),
    ]
    st.dataframe([{"Feature":x,"Status":y,"Details":z} for x,y,z in status], use_container_width=True, hide_index=True)
    st.markdown("### Minimum validation plan")
    st.markdown("1. Collect licensed/permitted historical data per league.\n2. Split by time: train on older seasons, test on later matches.\n3. Compare against a simple baseline (home advantage / Elo / bookmaker-free baseline).\n4. Report accuracy plus log loss or Brier score and calibration; include sample size.\n5. Test across seasons and competitions; record missing data and API failures.\n6. Publish only measured metrics, never placeholder accuracy.")

else:
    st.markdown("## Deploy RAN-NEETI online")
    st.markdown("### Beginner-friendly steps — no local Python install needed")
    steps = [
        ("Download and extract", "Download the project ZIP from this chat and choose Extract All."),
        ("Create a GitHub repository", "Sign in at github.com, create a public repository named ran-neeti, and upload app.py, requirements.txt and README.md from the extracted folder."),
        ("Open Streamlit Community Cloud", "Visit share.streamlit.io and sign in using GitHub."),
        ("Create app", "Choose repository ran-neeti, branch main, and main file path app.py."),
        ("Deploy", "Click Deploy. Wait for the build to finish; then copy the URL Streamlit gives you."),
        ("Check it", "Test the matchup lab, data source status and anime lookup. A live endpoint may be unavailable temporarily."),
    ]
    for i,(title,desc) in enumerate(steps,1):
        st.markdown(f'<div class="move"><b>{i}. {title}</b><p>{desc}</p></div>', unsafe_allow_html=True)
    st.warning("This package is a deployable research prototype, not a finished all-sports AI system. The public feed is best-effort, and each sport still needs its own validated dataset/model before presenting reliable probabilities.")

st.divider()
st.markdown('<div class="smallmuted">RAN-NEETI · Research prototype · Public data can be delayed, incomplete, rate-limited or unavailable. Predictions are exploratory, not betting advice.</div>', unsafe_allow_html=True)
