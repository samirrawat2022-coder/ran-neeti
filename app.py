import io, json, zipfile, re, difflib, html
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict, deque
from datetime import datetime, timezone
import requests
import numpy as np
import pandas as pd
import streamlit as st
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, log_loss, f1_score, brier_score_loss

st.set_page_config(page_title='RAN-NEETI | AI Prediction Lab', page_icon='◈', layout='wide')
st.markdown('''<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;600;700;800&family=Inter:wght@300;400;500;600;700&display=swap');
:root{--bg:#070b14;--panel:#0e1626;--line:#24344d;--cyan:#53e5ff;--violet:#a78bfa;--muted:#91a2bd;}
.stApp{background:radial-gradient(ellipse at 12% 0%,#15233c 0%,#070b14 45%,#080b16 100%);color:#edf4ff;font-family:Inter,sans-serif}
.block-container{padding-top:1.4rem;max-width:1250px}.brand{font-family:Orbitron,sans-serif;font-size:2.35rem;letter-spacing:.14em;font-weight:800;color:#f4f8ff;text-shadow:0 0 22px #53e5ff45}
.brand span{color:var(--cyan)}.sub{color:#91a2bd;letter-spacing:.18em;text-transform:uppercase;font-size:.72rem}
.panel{background:linear-gradient(145deg,#101b2d,#0b1220);border:1px solid #263954;border-radius:16px;padding:20px 22px;margin:8px 0;box-shadow:0 8px 35px #0002}
.kicker{font-family:Orbitron,sans-serif;color:#53e5ff;font-size:.72rem;letter-spacing:.15em;text-transform:uppercase}.muted{color:#91a2bd;font-size:.88rem}
h1,h2,h3{font-family:Orbitron,sans-serif!important}.stButton>button{background:linear-gradient(90deg,#23c9e8,#8b7cff);color:#06101a;border:0;border-radius:10px;font-weight:800;min-height:2.8rem}
[data-testid="stMetric"]{background:#0d1727;border:1px solid #263954;padding:14px;border-radius:12px}[data-testid="stSidebar"]{background:#080e19;border-right:1px solid #263954}
</style>''', unsafe_allow_html=True)

SEASONS = ['2526','2425','2324','2223','2122','2021','1920','1819']
LEAGUES = {
    'English Premier League':'E0', 'Spanish La Liga':'SP1', 'Italian Serie A':'I1',
    'German Bundesliga':'D1', 'French Ligue 1':'F1', 'Dutch Eredivisie':'N1',
    'Portuguese Primeira Liga':'P1'
}
BASE_FOOTBALL_URL='https://www.football-data.co.uk/mmz4281/{season}/{league}.csv'
CRICKET_URL='https://cricsheet.org/downloads/t20s_json.zip'
WIKI_API='https://en.wikipedia.org/w/api.php'
HEADERS={'User-Agent':'RAN-NEETI educational data science project contact: academic prototype'}

@st.cache_data(ttl=3600, show_spinner=False)
def load_football(league_code):
    frames=[]; failures=[]
    def fetch(season):
        url=BASE_FOOTBALL_URL.format(season=season,league=league_code)
        r=requests.get(url,timeout=(4,9),headers=HEADERS); r.raise_for_status()
        df=pd.read_csv(io.BytesIO(r.content),encoding='latin1',on_bad_lines='skip')
        required={'HomeTeam','AwayTeam','FTHG','FTAG','FTR'}
        if not required.issubset(df.columns): raise ValueError('CSV missing match-result columns')
        cols=['HomeTeam','AwayTeam','FTHG','FTAG','FTR']+(['Date'] if 'Date' in df.columns else [])
        df=df[cols].copy(); df['Season']=season; return df
    with ThreadPoolExecutor(max_workers=6) as pool:
        jobs={pool.submit(fetch,s):s for s in SEASONS}
        for f in as_completed(jobs):
            s=jobs[f]
            try: frames.append(f.result())
            except Exception as e: failures.append(f'{s}: {type(e).__name__}')
    if not frames: return pd.DataFrame(),failures
    df=pd.concat(frames,ignore_index=True)
    df['FTHG']=pd.to_numeric(df['FTHG'],errors='coerce'); df['FTAG']=pd.to_numeric(df['FTAG'],errors='coerce')
    df['ParsedDate']=pd.to_datetime(df.get('Date',pd.Series(index=df.index,dtype='object')),dayfirst=True,errors='coerce')
    df=df.dropna(subset=['HomeTeam','AwayTeam','FTHG','FTAG','FTR'])
    df=df[df.FTR.isin(['H','D','A'])].sort_values('ParsedDate',na_position='last').reset_index(drop=True)
    return df,failures

@st.cache_data(ttl=86400,show_spinner=False)
def load_cricket():
    r=requests.get(CRICKET_URL,timeout=(8,60),headers=HEADERS); r.raise_for_status()
    rows=[]
    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
        names=[n for n in z.namelist() if n.endswith('.json')]
        for name in names:
            try:
                obj=json.loads(z.read(name)); info=obj.get('info',{}); teams=info.get('teams',[]); outcome=info.get('outcome',{}); winner=outcome.get('winner'); dates=info.get('dates',[])
                if len(teams)==2 and winner in teams and dates:
                    rows.append({'date':str(dates[0]),'team1':teams[0],'team2':teams[1],'winner':winner,'venue':info.get('venue','Unknown')})
            except Exception: continue
    df=pd.DataFrame(rows)
    if not df.empty: df['date']=pd.to_datetime(df.date,errors='coerce'); df=df.dropna(subset=['date']).sort_values('date').reset_index(drop=True)
    return df

@st.cache_data(ttl=3600,show_spinner=False)
def wiki_search(query):
    r=requests.get(WIKI_API,params={'action':'query','list':'search','srsearch':query,'format':'json','srlimit':5},timeout=(4,12),headers=HEADERS); r.raise_for_status()
    return r.json().get('query',{}).get('search',[])

@st.cache_data(ttl=3600,show_spinner=False)
def wiki_summary(title):
    r=requests.get(WIKI_API,params={'action':'query','prop':'extracts|info','exintro':1,'explaintext':1,'inprop':'url','redirects':1,'titles':title,'format':'json'},timeout=(4,12),headers=HEADERS); r.raise_for_status()
    pages=r.json().get('query',{}).get('pages',{})
    if not pages:return None
    p=next(iter(pages.values()))
    if 'missing' in p:return None
    return {'title':p.get('title',title),'extract':p.get('extract',''),'url':p.get('fullurl','https://en.wikipedia.org/wiki/'+title.replace(' ','_'))}

def resolve_name(name, teams):
    cleaned=name.strip().casefold()
    exact={str(t).casefold():str(t) for t in teams}
    if cleaned in exact:return exact[cleaned],None
    # Allow common shorthand, e.g. Barca for Barcelona, but tell user what matched.
    aliases={'barca':'Barcelona','fc barcelona':'Barcelona','real madrid cf':'Real Madrid','man utd':'Manchester United','man city':'Manchester City','spurs':'Tottenham Hotspur','atleti':'Atletico Madrid','atletico madrid':'Atlético Madrid'}
    candidate=aliases.get(cleaned)
    if candidate and candidate.casefold() in exact:return exact[candidate.casefold()],None
    matches=difflib.get_close_matches(cleaned,list(exact.keys()),n=1,cutoff=.78)
    if matches:return exact[matches[0]],f'Interpreted “{name}” as “{exact[matches[0]]}”.'
    return None,None

def football_features(df):
    form=defaultdict(lambda:deque(maxlen=5)); gd=defaultdict(lambda:deque(maxlen=5)); rows=[]
    for r in df.itertuples(index=False):
        h,a=r.HomeTeam,r.AwayTeam
        rows.append({'HomeTeam':h,'AwayTeam':a,'home_form':float(np.mean(form[h])) if form[h] else .5,'away_form':float(np.mean(form[a])) if form[a] else .5,'home_gd':float(np.mean(gd[h])) if gd[h] else 0.,'away_gd':float(np.mean(gd[a])) if gd[a] else 0.})
        hg,ag=float(r.FTHG),float(r.FTAG)
        form[h].append(1 if hg>ag else .5 if hg==ag else 0); form[a].append(1 if ag>hg else .5 if hg==ag else 0)
        gd[h].append(hg-ag); gd[a].append(ag-hg)
    return pd.DataFrame(rows)

def latest_football_features(df,home,away):
    # Build recent form from all downloaded matches; no future score is used as a model feature.
    hist=defaultdict(lambda:deque(maxlen=5)); gd=defaultdict(lambda:deque(maxlen=5))
    for r in df.itertuples(index=False):
        h,a=r.HomeTeam,r.AwayTeam; hg,ag=float(r.FTHG),float(r.FTAG)
        hist[h].append(1 if hg>ag else .5 if hg==ag else 0); hist[a].append(1 if ag>hg else .5 if hg==ag else 0)
        gd[h].append(hg-ag); gd[a].append(ag-hg)
    return pd.DataFrame([{'HomeTeam':home,'AwayTeam':away,'home_form':float(np.mean(hist[home])) if hist[home] else .5,'away_form':float(np.mean(hist[away])) if hist[away] else .5,'home_gd':float(np.mean(gd[home])) if gd[home] else 0.,'away_gd':float(np.mean(gd[away])) if gd[away] else 0.}])

def cricket_features(df):
    history=defaultdict(lambda:deque(maxlen=5)); rows=[]
    for r in df.itertuples(index=False):
        a,b=r.team1,r.team2; fa=float(np.mean(history[a])) if history[a] else .5; fb=float(np.mean(history[b])) if history[b] else .5
        rows.append({'team1':a,'team2':b,'form_diff':fa-fb,'form_team1':fa,'form_team2':fb})
        history[a].append(1 if r.winner==a else 0); history[b].append(1 if r.winner==b else 0)
    return pd.DataFrame(rows)

def pipeline(cat,num):
    prep=ColumnTransformer([('cat',OneHotEncoder(handle_unknown='ignore'),cat),('num',Pipeline([('impute',SimpleImputer(strategy='median')),('scale',StandardScaler())]),num)])
    return Pipeline([('prep',prep),('model',LogisticRegression(max_iter=600,class_weight='balanced'))])

@st.cache_data(ttl=3600,show_spinner=False)
def train_football(df):
    X=football_features(df); y=df.FTR.to_numpy(); cut=int(len(X)*.8)
    if cut<30 or len(set(y[:cut]))<2: raise ValueError('Not enough match history to train. Select another league or try again later.')
    model=pipeline(['HomeTeam','AwayTeam'],['home_form','away_form','home_gd','away_gd']); model.fit(X.iloc[:cut],y[:cut])
    metrics={}
    if cut<len(X):
        xt=X.iloc[cut:]; yt=y[cut:]; pred=model.predict(xt); probs=model.predict_proba(xt)
        metrics={'Accuracy':float(accuracy_score(yt,pred)),'Macro F1':float(f1_score(yt,pred,average='macro',zero_division=0)),'Log loss':float(log_loss(yt,probs,labels=model.named_steps['model'].classes_)),'Test matches':int(len(yt))}
    model.fit(X,y)
    return model,metrics

@st.cache_data(ttl=3600,show_spinner=False)
def train_cricket(df):
    X=cricket_features(df); y=np.array([1 if w==a else 0 for w,a in zip(df.winner,df.team1)]); cut=int(len(X)*.8)
    if cut<30 or len(set(y[:cut]))<2: raise ValueError('Not enough cricket records to train a stable baseline.')
    model=pipeline(['team1','team2'],['form_diff','form_team1','form_team2']); model.fit(X.iloc[:cut],y[:cut]); metrics={}
    if cut<len(X):
        xt=X.iloc[cut:]; yt=y[cut:]; pred=model.predict(xt); prob=model.predict_proba(xt)[:,1]
        metrics={'Accuracy':float(accuracy_score(yt,pred)),'Macro F1':float(f1_score(yt,pred,average='macro',zero_division=0)),'Brier score':float(brier_score_loss(yt,prob)),'Test matches':int(len(yt))}
    model.fit(X,y); return model,metrics

def gemini_key():
    try:return st.secrets.get('GEMINI_API_KEY','')
    except Exception:return ''

def ai_fiction_analysis(name_a,name_b,summary_a,summary_b,settings):
    key=gemini_key()
    if not key:return None,'No Gemini API key configured. Add GEMINI_API_KEY in Streamlit app Secrets to enable generative AI analysis.'
    prompt=f'''You are the evidence analyst for RAN-NEETI, a fictional matchup estimation tool. Compare these fictional characters using ONLY the source excerpts below. Do not invent feats, powers, forms, scaling, or citations. If the excerpts do not contain comparable combat evidence, say that clearly and give a cautious qualitative estimate only if the evidence supports it. If you give a percentage, label it subjective and assumption-dependent, never scientifically calibrated. Explain the main evidence, missing evidence, assumptions and uncertainty. Cite only the supplied URLs. Keep the response concise with headings.
Character A: {name_a}\nSource title: {summary_a['title']}\nURL: {summary_a['url']}\nExcerpt: {summary_a['extract'][:4500]}\n\nCharacter B: {name_b}\nSource title: {summary_b['title']}\nURL: {summary_b['url']}\nExcerpt: {summary_b['extract'][:4500]}\n\nScenario settings: {settings}'''
    url='https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent'
    try:
        r=requests.post(url,params={'key':key},json={'contents':[{'parts':[{'text':prompt}]}],'generationConfig':{'temperature':0.2,'maxOutputTokens':900}},timeout=(8,45))
        if r.status_code==429:return None,'Gemini free-tier rate limit reached. Wait and retry, or use the source summaries below.'
        r.raise_for_status(); data=r.json(); text=data['candidates'][0]['content']['parts'][0]['text']
        return text,None
    except Exception as e:return None,f'AI request failed ({type(e).__name__}). Check that your API key/model is valid and retry.'

st.markdown('<div class="brand">RAN<span>·</span>NEETI</div><div class="sub">Unified AI Prediction Lab · Research prototype</div>',unsafe_allow_html=True)
st.write('')
with st.sidebar:
    st.markdown('### ◈ CONTROL DECK')
    domain=st.radio('Prediction domain',['Real Sports','Anime / Fiction'])
    mode=st.radio('Input mode',['Automatic','Advanced controls'])
    st.divider(); st.caption('Sports: historical results + trained ML baseline. Fiction: sourced lookup + optional Gemini analysis.')

if domain=='Real Sports':
    sport=st.selectbox('SPORT ENGINE',['Football / Soccer','Cricket · T20'])
    if sport=='Football / Soccer':
        st.markdown('<div class="panel"><div class="kicker">01 / Match intelligence</div><h2>Football outcome prediction</h2><div class="muted">Choose the competition, enter two teams, and run a historical ML baseline. This is not live-score or betting-odds prediction.</div></div>',unsafe_allow_html=True)
        league_name=st.selectbox('COMPETITION',list(LEAGUES.keys()),index=0)
        c1,c2=st.columns(2)
        with c1: home=st.text_input('HOME TEAM','Arsenal')
        with c2: away=st.text_input('AWAY TEAM','Liverpool')
        if mode=='Advanced controls':
            seasons=st.multiselect('Historical seasons',SEASONS,default=SEASONS[:6]); st.caption('The model trains on the selected league and seasons only.')
        else: seasons=SEASONS
        if st.button('⚡ RUN FOOTBALL PREDICTION',use_container_width=True):
            with st.spinner(f'Downloading {league_name} history and training the model…'):
                try:
                    df,failures=load_football(LEAGUES[league_name])
                    if mode=='Advanced controls' and seasons: df=df[df.Season.isin(seasons)].reset_index(drop=True)
                    if df.empty:
                        st.error('No football CSVs could be loaded. This can be a temporary source/network issue. Try again later.'); st.caption('Download status: '+('; '.join(failures) if failures else 'No records returned.'))
                    elif not home.strip() or not away.strip() or home.strip().casefold()==away.strip().casefold():st.warning('Enter two different team names.')
                    else:
                        teams=sorted(set(df.HomeTeam)|set(df.AwayTeam)); h,ha=resolve_name(home,teams); a,aa=resolve_name(away,teams)
                        if not h or not a:
                            st.error(f'Team not found in {league_name}. Select the correct competition and use a team name from its historical records.')
                            st.caption('Available teams: '+', '.join(teams))
                        else:
                            if ha:st.info(ha)
                            if aa:st.info(aa)
                            if h==a:st.warning('Both entries resolved to the same team. Enter two different teams.')
                            else:
                                model,metrics=train_football(df); feat=latest_football_features(df,h,a); pred=model.predict_proba(feat)[0]; cls=list(model.named_steps['model'].classes_); probs={str(k):float(v) for k,v in zip(cls,pred)}
                                labels={'H':f'{h} win','D':'Draw','A':f'{a} win'}; best=max(probs,key=probs.get)
                                st.markdown(f'<div class="panel"><div class="kicker">Historical ML prediction</div><h2>{html.escape(labels[best])}</h2><div class="muted">Probabilities from a Logistic Regression baseline trained on {html.escape(league_name)} historical results. Not a guarantee.</div></div>',unsafe_allow_html=True)
                                cols=st.columns(3)
                                for col,k in zip(cols,['H','D','A']):col.metric(labels[k],f'{probs.get(k,0)*100:.1f}%')
                                f=feat.iloc[0]; st.write(f'Recent-form proxy: {h} {f.home_form:.2f}, goal-difference average {f.home_gd:.2f}; {a} {f.away_form:.2f}, goal-difference average {f.away_gd:.2f}.')
                                st.markdown('#### Chronological holdout evaluation (separate from this prediction)')
                                if metrics:
                                    cols=st.columns(len(metrics))
                                    for col,(k,v) in zip(cols,metrics.items()):col.metric(k,f'{v:.3f}' if isinstance(v,float) else str(v))
                                st.caption(f'Source: Football-Data.co.uk · {len(df)} historical matches loaded · data retrieval time (UTC): {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")}')
                                st.markdown('[Inspect Football-Data sources](https://www.football-data.co.uk/data.php)')
                except Exception as e:st.error(f'Football prediction error: {type(e).__name__}: {e}. Open Manage app → Logs for details.')
    else:
        st.markdown('<div class="panel"><div class="kicker">02 / Match intelligence</div><h2>Cricket T20 outcome prediction</h2><div class="muted">Historical Cricsheet T20 outcomes → recent form → Logistic Regression baseline.</div></div>',unsafe_allow_html=True)
        c1,c2=st.columns(2)
        with c1:t1=st.text_input('TEAM A','India',key='cr_a')
        with c2:t2=st.text_input('TEAM B','Australia',key='cr_b')
        if st.button('⚡ RUN CRICKET PREDICTION',use_container_width=True):
            with st.spinner('Loading and parsing the historical Cricsheet archive. First run may take a few minutes…'):
                try:
                    df=load_cricket()
                    if df.empty:st.error('No usable completed T20 results were loaded. Check the app logs or retry later.')
                    else:
                        teams=sorted(set(df.team1)|set(df.team2)); a,_=resolve_name(t1,teams); b,_=resolve_name(t2,teams)
                        if not a or not b:
                            st.error('One or both team names were not found in the Cricsheet archive. Try a name from this list:');st.write(', '.join(teams))
                        elif a==b:st.warning('Enter two different teams.')
                        else:
                            model,metrics=train_cricket(df); allx=cricket_features(df); latest=defaultdict(lambda:deque(maxlen=5))
                            for r in df.itertuples(index=False):
                                latest[r.team1].append(1 if r.winner==r.team1 else 0);latest[r.team2].append(1 if r.winner==r.team2 else 0)
                            fa=float(np.mean(latest[a])) if latest[a] else .5;fb=float(np.mean(latest[b])) if latest[b] else .5
                            feat=pd.DataFrame([{'team1':a,'team2':b,'form_diff':fa-fb,'form_team1':fa,'form_team2':fb}]); p=model.predict_proba(feat)[0]; cls=list(model.named_steps['model'].classes_); probs={int(k):float(v) for k,v in zip(cls,p)}
                            st.markdown(f'<div class="panel"><div class="kicker">Historical ML prediction</div><h2>{html.escape(a if probs.get(1,0)>=probs.get(0,0) else b)} more likely to win</h2><div class="muted">Estimated probabilities from historical T20 outcomes; not a guarantee.</div></div>',unsafe_allow_html=True)
                            cols=st.columns(2);cols[0].metric(a,f'{probs.get(1,0)*100:.1f}%');cols[1].metric(b,f'{probs.get(0,0)*100:.1f}%')
                            st.write(f'Recent win-form proxy: {a} {fa:.2f}; {b} {fb:.2f}. Matches parsed: {len(df)}.')
                            for col,(k,v) in zip(st.columns(len(metrics)),metrics.items()):col.metric(k,f'{v:.3f}' if isinstance(v,float) else str(v))
                            st.caption('Source: Cricsheet downloadable T20 archive. This is historical outcome modelling, not a live in-play predictor.')
                            st.markdown('[Inspect Cricsheet downloads](https://cricsheet.org/downloads/)')
                except Exception as e:st.error(f'Cricket prediction error: {type(e).__name__}: {e}. If this is the first run, wait for the archive download to finish; see app Logs if it repeats.')
else:
    st.markdown('<div class="panel"><div class="kicker">03 / Fiction intelligence</div><h2>Character matchup lab</h2><div class="muted">Source-linked character lookup plus optional generative AI analysis. Fictional win estimates are subjective, not calibrated sports probabilities.</div></div>',unsafe_allow_html=True)
    c1,c2=st.columns(2)
    with c1:char1=st.text_input('CHARACTER A','Naruto Uzumaki')
    with c2:char2=st.text_input('CHARACTER B','Ichigo Kurosaki')
    if mode=='Advanced controls':
        version=st.selectbox('Character version',['Peak / strongest shown','Anime-only feats','Manga / canon feats','Early-series versions']); equal=st.checkbox('Equalize physical stats',False); prep=st.selectbox('Preparation',['No prep','1 hour prep','1 day prep']); arena=st.selectbox('Battle conditions',['Neutral arena','Home universe','Random encounter'])
    else:version='Peak / strongest shown';equal=False;prep='No prep';arena='Neutral arena'
    if st.button('⚡ ANALYSE FICTION MATCHUP',use_container_width=True):
        if not char1.strip() or not char2.strip() or char1.strip().casefold()==char2.strip().casefold():st.warning('Enter two different character names.')
        else:
            with st.spinner('Searching sources and preparing the comparison…'):
                try:
                    summaries=[]
                    for name in [char1.strip(),char2.strip()]:
                        hits=wiki_search(name+' fictional character')
                        chosen=next((x for x in hits if name.casefold() in x.get('title','').casefold()),hits[0] if hits else None)
                        summaries.append(wiki_summary(chosen['title']) if chosen else None)
                    if not all(summaries):st.error('Could not find both characters. Try full name plus series name.')
                    else:
                        for s in summaries:
                            st.markdown(f'<div class="panel"><div class="kicker">Retrieved source</div><h3>{html.escape(s["title"])}</h3><div class="muted">{html.escape((s["extract"] or "No summary available.")[:1000])}</div><a href="{html.escape(s["url"],quote=True)}" target="_blank">Open source ↗</a></div>',unsafe_allow_html=True)
                        settings=f'version={version}; equal physical stats={equal}; prep={prep}; arena={arena}'
                        answer,error=ai_fiction_analysis(char1,char2,summaries[0],summaries[1],settings)
                        if answer:
                            st.markdown('<div class="panel"><div class="kicker">AI scenario analysis</div></div>',unsafe_allow_html=True);st.markdown(answer)
                        else:
                            st.warning(error)
                            st.info('Without a configured AI API key, this module can retrieve source biographies but cannot responsibly infer a winner from them. Add the key under Streamlit app Secrets to enable AI analysis.')
                        st.caption('The AI is instructed to use only retrieved excerpts. Its judgement remains subjective and source coverage may be incomplete.')
                except Exception as e:st.error(f'Fiction lookup failed: {type(e).__name__}: {e}. Check Manage app → Logs.')

st.divider()
t1,t2,t3=st.tabs(['RESEARCH EVIDENCE','DATA & SOURCES','SYSTEM LIMITS'])
with t1:
    st.markdown('''### Reproducible evaluation design
- Models: Logistic Regression baseline with team identities and rolling recent-form features.
- Evaluation: chronological 80/20 holdout; metrics are calculated at runtime.
- Football metrics: accuracy, macro-F1 and log loss. Cricket metrics: accuracy, macro-F1 and Brier score.
- Historical records only; these are not live scores, odds, injuries or betting predictions.
- Save dated data snapshots and logs before reporting thesis results.''')
with t2:
    st.markdown('''- Football: [Football-Data.co.uk](https://www.football-data.co.uk/data.php) (multiple competitions).
- Cricket: [Cricsheet](https://cricsheet.org/downloads/).
- Fiction character summaries: [Wikipedia API](https://en.wikipedia.org/w/api.php).
- Optional generative AI: Google Gemini API; requires a key in Streamlit Secrets.''')
with t3:
    st.markdown('''- Football competition must match the teams; the model is trained on that competition's historical results.
- Cricket uses the available Cricsheet T20 archive; first download can take time.
- Fiction analysis needs a Gemini API key. Biography text may not contain comparable combat feats, so uncertainty must be reported.
- All model metrics are computed at runtime and may change with data versions. This is a research prototype, not a validated universal prediction system.''')
st.markdown('<div style="text-align:center;color:#637894;font-size:.75rem;padding:18px 0">RAN-NEETI · Research prototype · Transparent by design</div>',unsafe_allow_html=True)
