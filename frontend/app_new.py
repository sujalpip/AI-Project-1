import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import base64, math

st.set_page_config(
    page_title="StockSense AI",
    layout="wide",
    page_icon="⚡",
    initial_sidebar_state="expanded"
)
API = "https://ai-project-1-ooli.onrender.com"

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;600&display=swap');
:root{
  --bg0:#05080f;--bg1:#080c16;--bg2:#0b0f1c;--bg3:#0e1322;
  --card:rgba(255,255,255,0.03);--card2:rgba(255,255,255,0.055);
  --b1:rgba(255,255,255,0.06);--b2:rgba(255,255,255,0.1);
  --blue:#60a5fa;--purple:#a78bfa;--cyan:#34d399;
  --green:#4ade80;--red:#f87171;--yellow:#fbbf24;--orange:#fb923c;
  --t1:#f1f5f9;--t2:#94a3b8;--t3:#64748b;--t4:#334155;
}
html,body,[class*="css"]{font-family:'Inter',sans-serif!important;background:var(--bg0)!important;color:var(--t1)!important;}
.stApp{
  background:
    radial-gradient(ellipse 90% 50% at 10% -10%,rgba(96,165,250,0.08) 0%,transparent 55%),
    radial-gradient(ellipse 70% 60% at 90% 110%,rgba(167,139,250,0.08) 0%,transparent 55%),
    radial-gradient(ellipse 50% 40% at 50% 50%,rgba(52,211,153,0.03) 0%,transparent 60%),
    linear-gradient(180deg,var(--bg0) 0%,var(--bg1) 100%)!important;
  min-height:100vh;
}
#MainMenu,footer,header,.stDeployButton{visibility:hidden!important;display:none!important;}
/* Sidebar */
[data-testid="stSidebar"]{background:linear-gradient(180deg,var(--bg2) 0%,var(--bg0) 100%)!important;border-right:1px solid var(--b1)!important;box-shadow:6px 0 30px rgba(0,0,0,0.4)!important;}
[data-testid="stSidebar"] *{color:var(--t2)!important;}
[data-testid="stSidebar"] strong{color:var(--t1)!important;}
[data-testid="stSidebar"] input{background:#000!important;border:1px solid rgba(251,191,36,0.5)!important;border-radius:10px!important;color:#fbbf24!important;font-family:'JetBrains Mono',monospace!important;font-weight:700!important;font-size:0.9rem!important;letter-spacing:0.06em!important;}
[data-testid="stSidebar"] input:focus{border-color:#fbbf24!important;box-shadow:0 0 0 3px rgba(251,191,36,0.15)!important;outline:none!important;}
[data-testid="stSidebar"] .stSelectbox>div>div{background:rgba(255,255,255,0.04)!important;border:1px solid var(--b2)!important;border-radius:10px!important;color:var(--t1)!important;}
/* Tabs */
.stTabs [data-baseweb="tab-list"]{background:rgba(255,255,255,0.02)!important;border-radius:14px!important;padding:5px!important;border:1px solid var(--b1)!important;gap:3px!important;}
.stTabs [data-baseweb="tab"]{background:transparent!important;border-radius:10px!important;color:var(--t3)!important;font-weight:600!important;font-size:0.82rem!important;padding:8px 16px!important;transition:all 0.2s!important;border:none!important;letter-spacing:0.01em!important;}
.stTabs [aria-selected="true"]{background:linear-gradient(135deg,rgba(96,165,250,0.18),rgba(167,139,250,0.18))!important;color:var(--t1)!important;box-shadow:0 2px 16px rgba(96,165,250,0.2),inset 0 1px 0 rgba(255,255,255,0.07)!important;}
.stTabs [data-baseweb="tab"]:hover{color:var(--t1)!important;background:rgba(255,255,255,0.05)!important;}
.stTabs [data-baseweb="tab-panel"]{padding-top:1.5rem!important;}
/* Buttons */
.stButton>button[kind="primary"]{background:linear-gradient(135deg,#1d4ed8 0%,#7c3aed 100%)!important;border:none!important;border-radius:10px!important;color:#fff!important;font-weight:700!important;font-size:0.85rem!important;letter-spacing:0.05em!important;padding:0.58rem 1.4rem!important;transition:all 0.22s!important;box-shadow:0 4px 18px rgba(29,78,216,0.4)!important;text-transform:uppercase!important;}
.stButton>button[kind="primary"]:hover{transform:translateY(-2px)!important;box-shadow:0 8px 30px rgba(29,78,216,0.6)!important;filter:brightness(1.1)!important;}
.stButton>button[kind="primary"]:active{transform:translateY(0)!important;}
.stButton>button:not([kind="primary"]){background:rgba(255,255,255,0.04)!important;border:1px solid var(--b2)!important;border-radius:10px!important;color:var(--t1)!important;font-weight:600!important;font-size:0.84rem!important;transition:all 0.18s!important;}
.stButton>button:not([kind="primary"]):hover{background:rgba(255,255,255,0.08)!important;border-color:var(--blue)!important;color:var(--blue)!important;}
/* Inputs */
.stTextInput input,.stNumberInput input{background:var(--bg2)!important;border:1px solid var(--b2)!important;border-radius:10px!important;color:var(--t1)!important;font-size:0.9rem!important;transition:all 0.18s!important;}
.stTextInput input:focus,.stNumberInput input:focus{border-color:var(--blue)!important;box-shadow:0 0 0 3px rgba(96,165,250,0.14)!important;outline:none!important;}
.stTextInput label,.stNumberInput label{color:var(--t3)!important;font-size:0.72rem!important;font-weight:700!important;text-transform:uppercase!important;letter-spacing:0.1em!important;}
.stSelectbox>div>div,.stMultiSelect>div>div{background:var(--bg2)!important;border:1px solid var(--b2)!important;border-radius:10px!important;color:var(--t1)!important;}
.stSelectbox label{color:var(--t3)!important;font-size:0.72rem!important;font-weight:700!important;text-transform:uppercase!important;letter-spacing:0.1em!important;}
/* Slider */
.stSlider [data-baseweb="slider"] div[role="slider"]{background:var(--blue)!important;border-color:var(--blue)!important;box-shadow:0 0 10px rgba(96,165,250,0.6)!important;}
/* Chat */
[data-testid="stChatMessage"]{background:rgba(255,255,255,0.03)!important;border:1px solid var(--b2)!important;border-radius:14px!important;margin-bottom:8px!important;}
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]){background:rgba(96,165,250,0.05)!important;border-color:rgba(96,165,250,0.18)!important;}
[data-testid="stChatMessage"] p,[data-testid="stChatMessage"] li,[data-testid="stChatMessage"] span,[data-testid="stChatMessage"] div{color:var(--t1)!important;font-size:0.9rem!important;line-height:1.72!important;}
[data-testid="stChatMessage"] strong{color:#fff!important;font-weight:700!important;}
[data-testid="stChatInput"]>div,[data-testid="stChatInputContainer"]{background:var(--bg2)!important;border:1px solid rgba(96,165,250,0.3)!important;border-radius:14px!important;}
[data-testid="stChatInput"]>div:focus-within{border-color:var(--blue)!important;box-shadow:0 0 0 3px rgba(96,165,250,0.12)!important;}
[data-testid="stChatInput"] textarea{background:var(--bg2)!important;color:var(--t1)!important;caret-color:var(--blue)!important;-webkit-text-fill-color:var(--t1)!important;}
[data-testid="stChatInput"] textarea::placeholder{color:var(--t4)!important;}
/* File uploader */
[data-testid="stFileUploader"]{background:rgba(255,255,255,0.018)!important;border:2px dashed var(--b2)!important;border-radius:14px!important;transition:border-color 0.2s!important;}
[data-testid="stFileUploader"]:hover{border-color:var(--blue)!important;}
/* Dataframe */
.stDataFrame{border-radius:12px!important;overflow:hidden!important;}
.stDataFrame thead th{background:rgba(255,255,255,0.05)!important;color:var(--t3)!important;font-size:0.7rem!important;text-transform:uppercase!important;letter-spacing:0.1em!important;font-weight:700!important;border-bottom:1px solid var(--b1)!important;}
.stDataFrame tbody td{color:var(--t2)!important;font-size:0.83rem!important;border-color:var(--b1)!important;}
.stDataFrame tbody tr:hover td{background:rgba(255,255,255,0.025)!important;}
/* Misc */
.stAlert{border-radius:10px!important;}
.stSpinner>div{border-top-color:var(--blue)!important;}
.stCheckbox label,.stToggle label{color:var(--t2)!important;font-size:0.85rem!important;}
::-webkit-scrollbar{width:5px;height:5px;}
::-webkit-scrollbar-track{background:transparent;}
::-webkit-scrollbar-thumb{background:rgba(255,255,255,0.1);border-radius:3px;}
::-webkit-scrollbar-thumb:hover{background:rgba(255,255,255,0.2);}
</style>""", unsafe_allow_html=True)

# ── Helpers ───────────────────────────────────────────────────────────────────
def api_get(path, params=None):
    try:
        r = requests.get(f"{API}{path}", params=params, timeout=8)
        return r.json() if r.status_code == 200 else None
    except Exception:
        return None

def api_post(path, data=None):
    try:
        r = requests.post(f"{API}{path}", json=data or {}, timeout=20)
        return r.json() if r.status_code == 200 else None
    except Exception:
        return None

def ac(a):
    return {"Strong Buy":"#4ade80","Buy":"#86efac","Hold":"#fbbf24",
            "Sell":"#f87171","Strong Sell":"#ef4444"}.get(a,"#94a3b8")

def kpi(label, value, color="#60a5fa", sub=""):
    s = f'<div style="font-size:0.68rem;color:#334155;margin-top:5px;font-weight:500;">{sub}</div>' if sub else ""
    return f"""<div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.07);
border-radius:14px;padding:20px 14px;text-align:center;position:relative;overflow:hidden;">
<div style="position:absolute;top:0;left:0;right:0;height:2px;
background:linear-gradient(90deg,transparent,{color},transparent);opacity:0.9;"></div>
<div style="font-size:0.6rem;color:#64748b;font-weight:700;text-transform:uppercase;
letter-spacing:0.14em;margin-bottom:9px;">{label}</div>
<div style="font-size:1.45rem;font-weight:800;color:{color};
font-family:'JetBrains Mono',monospace;line-height:1.1;">{value}</div>{s}</div>"""

def sec(title, badge="", bc="#60a5fa"):
    b = f'<span style="font-size:0.6rem;font-weight:700;padding:3px 9px;border-radius:20px;background:{bc}18;color:{bc};border:1px solid {bc}28;text-transform:uppercase;letter-spacing:0.1em;margin-left:8px;">{badge}</span>' if badge else ""
    return f'<div style="display:flex;align-items:center;margin:24px 0 14px;padding-bottom:10px;border-bottom:1px solid rgba(255,255,255,0.06);"><span style="font-size:0.92rem;font-weight:700;color:#f1f5f9;">{title}</span>{b}</div>'

def logrow(ev, msg, ts, c):
    return f'<div style="background:rgba(255,255,255,0.018);border-left:3px solid {c};border-radius:0 8px 8px 0;padding:8px 14px;margin-bottom:5px;display:flex;gap:14px;align-items:center;"><span style="font-size:0.6rem;font-weight:700;color:{c};min-width:72px;text-transform:uppercase;letter-spacing:0.06em;">{ev}</span><span style="font-size:0.79rem;color:#94a3b8;flex:1;line-height:1.4;">{msg}</span><span style="font-size:0.6rem;color:#334155;font-family:JetBrains Mono,monospace;white-space:nowrap;">{ts[:19].replace("T"," ")}</span></div>'

def newscard(art):
    s=art.get("sentiment","neutral"); c={"positive":"#4ade80","negative":"#f87171","neutral":"#64748b"}.get(s,"#64748b")
    ic={"positive":"🚀","negative":"📉","neutral":"➖"}.get(s,"➖"); conf=int(art.get("confidence",0)*100)
    return f'<div style="background:rgba(255,255,255,0.025);border:1px solid rgba(255,255,255,0.065);border-left:3px solid {c};border-radius:0 10px 10px 0;padding:12px 14px;margin-bottom:8px;"><div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;"><span style="font-size:0.6rem;font-weight:700;color:{c};background:{c}18;border:1px solid {c}28;border-radius:20px;padding:2px 9px;text-transform:uppercase;letter-spacing:0.08em;">{ic} {s}</span><span style="font-size:0.6rem;color:#334155;font-family:JetBrains Mono,monospace;">{conf}%</span></div><div style="font-size:0.83rem;color:#94a3b8;line-height:1.55;">{art.get("headline","")}</div></div>'

def tag(text, color="#60a5fa"):
    return f'<span style="background:{color}18;border:1px solid {color}30;border-radius:20px;padding:4px 12px;font-size:0.72rem;font-weight:700;color:{color};">{text}</span>'

# ── Sidebar ───────────────────────────────────────────────────────────────────
st.sidebar.markdown("""
<div style="text-align:center;padding:24px 8px 22px;border-bottom:1px solid rgba(255,255,255,0.06);margin-bottom:18px;">
<div style="font-size:1.5rem;font-weight:900;letter-spacing:-0.03em;
background:linear-gradient(135deg,#60a5fa 0%,#a78bfa 50%,#34d399 100%);
-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;">
⚡ StockSense AI</div>
<div style="font-size:0.58rem;color:#1e293b;letter-spacing:0.25em;text-transform:uppercase;margin-top:5px;">
Indian Market Intelligence</div>
</div>""", unsafe_allow_html=True)

st.sidebar.markdown('<div style="font-size:0.6rem;color:#1e293b;font-weight:700;text-transform:uppercase;letter-spacing:0.12em;margin-bottom:7px;">Quick Picks</div>', unsafe_allow_html=True)
st.sidebar.markdown("""<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:5px;margin-bottom:14px;">
""" + "".join([f'<div style="background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.07);border-radius:7px;padding:5px 3px;text-align:center;font-size:0.68rem;font-weight:700;color:#64748b;font-family:JetBrains Mono,monospace;">{s}</div>' for s in ["RELIANCE","TCS","INFY","HDFCBANK","SBIN","ITC"]]) + "</div>", unsafe_allow_html=True)

ticker_input  = st.sidebar.text_input("Ticker Symbol", value="RELIANCE", key="ticker")
period_select = st.sidebar.selectbox("Period", ["1mo","3mo","6mo","1y","2y"], index=3,
    format_func=lambda x: {"1mo":"1 Month","3mo":"3 Months","6mo":"6 Months","1y":"1 Year","2y":"2 Years"}[x])
analyze_btn   = st.sidebar.button("🔍  Analyse Stock", type="primary", use_container_width=True)

st.sidebar.markdown("---")
risk = api_get("/api/kotak/risk/status") or {}
pnl  = risk.get("daily_pnl", 0)
pc   = "#4ade80" if pnl >= 0 else "#f87171"
st.sidebar.markdown(f"""<div style="background:rgba(255,255,255,0.025);border:1px solid rgba(255,255,255,0.06);border-radius:10px;padding:12px 14px;">
<div style="font-size:0.6rem;color:#334155;font-weight:700;text-transform:uppercase;letter-spacing:0.12em;margin-bottom:10px;">Risk Dashboard</div>
<div style="display:flex;justify-content:space-between;margin-bottom:5px;"><span style="font-size:0.75rem;color:#64748b;">Daily P&L</span><span style="font-size:0.8rem;font-weight:700;color:{pc};font-family:JetBrains Mono,monospace;">&#8377;{pnl:,.2f}</span></div>
<div style="display:flex;justify-content:space-between;margin-bottom:5px;"><span style="font-size:0.75rem;color:#64748b;">Positions</span><span style="font-size:0.8rem;font-weight:700;color:#60a5fa;">{risk.get('open_positions',0)}/{risk.get('max_positions',5)}</span></div>
<div style="display:flex;justify-content:space-between;"><span style="font-size:0.75rem;color:#64748b;">Trades Today</span><span style="font-size:0.8rem;font-weight:700;color:#a78bfa;">{risk.get('daily_trades',0)}</span></div>
</div>""", unsafe_allow_html=True)
st.sidebar.markdown('<div style="font-size:0.58rem;color:#1e293b;text-align:center;margin-top:14px;line-height:1.9;">FinBERT · YOLOv8 · Random Forest<br>Kotak Neo API v2 · NSE/BSE</div>', unsafe_allow_html=True)

# ── Page Header ───────────────────────────────────────────────────────────────
st.markdown("""<div style="margin-bottom:22px;">
<div style="font-size:1.9rem;font-weight:900;letter-spacing:-0.04em;line-height:1.1;
background:linear-gradient(135deg,#60a5fa 0%,#a78bfa 45%,#34d399 100%);
-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;">
AI-Powered Indian Stock Intelligence</div>
<div style="font-size:0.83rem;color:#334155;margin-top:6px;font-weight:500;">
FinBERT Sentiment &nbsp;·&nbsp; ML Prediction &nbsp;·&nbsp; Live Trading &nbsp;·&nbsp; Options Scalping &nbsp;·&nbsp; Chart Vision
</div></div>""", unsafe_allow_html=True)

# ── Tabs ──────────────────────────────────────────────────────────────────────
t_dash,t_sig,t_trade,t_scalp,t_auto,t_port,t_cv,t_chat = st.tabs([
    "📊  Dashboard","📡  AI Signals","⚡  Live Trade",
    "🎯  Scalping","🤖  Auto Bot","💰  Portfolio",
    "🖼️  Chart Vision","💬  AI Chat"
])

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════════
with t_dash:
    if not analyze_btn:
        st.markdown("""<div style="text-align:center;padding:64px 20px;">
<div style="font-size:3.5rem;margin-bottom:16px;">📈</div>
<div style="font-size:1.2rem;font-weight:700;color:#e2e8f0;margin-bottom:8px;">Ready to Analyse</div>
<div style="font-size:0.87rem;color:#334155;max-width:400px;margin:0 auto;line-height:1.7;">
Enter a ticker in the sidebar and click <strong style="color:#60a5fa;">Analyse Stock</strong>
to get ML predictions, FinBERT sentiment, and technical analysis.</div>
<div style="display:flex;justify-content:center;gap:10px;flex-wrap:wrap;margin-top:24px;">""" +
"".join([tag(t,c) for t,c in [("FinBERT NLP","#60a5fa"),("Random Forest ML","#a78bfa"),("Technical Analysis","#34d399"),("YOLOv8 Vision","#fbbf24")]]) +
"</div></div>", unsafe_allow_html=True)

    if analyze_btn:
        with st.spinner(f"Analysing {ticker_input.upper()} — ML + FinBERT + Technicals..."):
            data = api_get(f"/api/analyze/{ticker_input}", {"period": period_select})
        if not data:
            st.error("Analysis failed. Check backend is running on port 8000.")
        else:
            fund=data.get("fundamentals",{}); dec=data.get("decision",{}); sent=data.get("sentiment",{})
            action=dec.get("action","Hold"); conf=dec.get("confidence",0)
            action_c=ac(action); conf_c="#4ade80" if conf>=70 else "#fbbf24" if conf>=50 else "#f87171"
            sentiment_v=dec.get("sentiment_signal","Neutral")
            sent_c="#4ade80" if sentiment_v=="Positive" else "#f87171" if sentiment_v=="Negative" else "#fbbf24"
            price=fund.get("Current Price","N/A")

            # Ticker badge
            st.markdown(f"""<div style="display:flex;align-items:center;gap:12px;margin-bottom:18px;">
<div style="background:linear-gradient(135deg,rgba(29,78,216,0.2),rgba(124,58,237,0.2));
border:1px solid rgba(96,165,250,0.3);border-radius:12px;padding:8px 18px;
display:inline-flex;align-items:center;gap:10px;">
<span style="font-size:1.3rem;font-weight:900;font-family:'JetBrains Mono',monospace;color:#60a5fa;">{data.get('ticker','')}</span>
<span style="font-size:0.65rem;color:#64748b;background:rgba(255,255,255,0.06);padding:2px 8px;border-radius:20px;font-weight:600;">NSE</span>
</div>
<span style="font-size:0.82rem;color:#334155;">Period: <strong style="color:#94a3b8;">{period_select}</strong></span>
</div>""", unsafe_allow_html=True)

            c1,c2,c3,c4 = st.columns(4)
            c1.markdown(kpi("Current Price",f"&#8377;{price}","#60a5fa","Live Market"), unsafe_allow_html=True)
            c2.markdown(kpi("AI Signal",action,action_c,"ML + Sentiment"), unsafe_allow_html=True)
            c3.markdown(kpi("Confidence",f"{conf}%",conf_c,"Random Forest"), unsafe_allow_html=True)
            c4.markdown(kpi("Sentiment",f"{'🟢' if sentiment_v=='Positive' else '🔴' if sentiment_v=='Negative' else '🟡'} {sentiment_v}",sent_c,"FinBERT NLP"), unsafe_allow_html=True)

            st.markdown(sec("📊 Technical Analysis","Interactive","#60a5fa"), unsafe_allow_html=True)
            chart_data = pd.DataFrame(data.get("chart_data",[]))
            if not chart_data.empty:
                fig = make_subplots(rows=3,cols=1,shared_xaxes=True,vertical_spacing=0.025,
                    subplot_titles=("Price · Bollinger Bands","MACD","RSI"),row_heights=[0.60,0.22,0.18])
                fig.add_trace(go.Candlestick(x=chart_data["Date"],open=chart_data["Open"],
                    high=chart_data["High"],low=chart_data["Low"],close=chart_data["Close"],
                    name="Price",increasing_line_color="#4ade80",decreasing_line_color="#f87171",
                    increasing_fillcolor="rgba(74,222,128,0.8)",decreasing_fillcolor="rgba(248,113,113,0.8)"),row=1,col=1)
                if "SMA_20" in chart_data and chart_data["SMA_20"].iloc[-1]:
                    fig.add_trace(go.Scatter(x=chart_data["Date"],y=chart_data["SMA_20"],line=dict(color="#fbbf24",width=1.5),name="SMA20"),row=1,col=1)
                if "EMA_20" in chart_data and chart_data["EMA_20"].iloc[-1]:
                    fig.add_trace(go.Scatter(x=chart_data["Date"],y=chart_data["EMA_20"],line=dict(color="#a78bfa",width=1.5),name="EMA20"),row=1,col=1)
                if "BB_High" in chart_data and chart_data["BB_High"].iloc[-1]:
                    fig.add_trace(go.Scatter(x=chart_data["Date"],y=chart_data["BB_High"],line=dict(color="rgba(96,165,250,0.4)",width=1,dash="dot"),name="BB High"),row=1,col=1)
                    fig.add_trace(go.Scatter(x=chart_data["Date"],y=chart_data["BB_Low"],line=dict(color="rgba(96,165,250,0.4)",width=1,dash="dot"),name="BB Low",fill="tonexty",fillcolor="rgba(96,165,250,0.04)"),row=1,col=1)
                if "MACD" in chart_data and chart_data["MACD"].iloc[-1]:
                    hist=pd.to_numeric(chart_data["MACD"])-pd.to_numeric(chart_data["MACD_Signal"])
                    fig.add_trace(go.Bar(x=chart_data["Date"],y=hist,marker_color=["rgba(74,222,128,0.7)" if v>=0 else "rgba(248,113,113,0.7)" for v in hist],name="Hist",showlegend=False),row=2,col=1)
                    fig.add_trace(go.Scatter(x=chart_data["Date"],y=chart_data["MACD"],line=dict(color="#60a5fa",width=1.8),name="MACD"),row=2,col=1)
                    fig.add_trace(go.Scatter(x=chart_data["Date"],y=chart_data["MACD_Signal"],line=dict(color="#fb923c",width=1.8),name="Signal"),row=2,col=1)
                if "RSI" in chart_data and chart_data["RSI"].iloc[-1]:
                    rsi=pd.to_numeric(chart_data["RSI"],errors="coerce")
                    fig.add_trace(go.Scatter(x=chart_data["Date"],y=rsi,line=dict(color="#a78bfa",width=1.8),name="RSI",fill="tozeroy",fillcolor="rgba(167,139,250,0.05)"),row=3,col=1)
                    fig.add_hline(y=70,line_dash="dot",line_color="rgba(248,113,113,0.4)",row=3,col=1)
                    fig.add_hline(y=30,line_dash="dot",line_color="rgba(74,222,128,0.4)",row=3,col=1)
                fig.update_layout(height=680,xaxis_rangeslider_visible=False,margin=dict(l=0,r=0,t=28,b=0),
                    template="plotly_dark",plot_bgcolor="rgba(0,0,0,0)",paper_bgcolor="rgba(0,0,0,0)",
                    font=dict(family="Inter",color="#64748b",size=11),
                    legend=dict(orientation="h",yanchor="bottom",y=1.01,xanchor="left",x=0,bgcolor="rgba(0,0,0,0)",font=dict(size=11)),
                    hoverlabel=dict(bgcolor="rgba(5,8,15,0.95)",bordercolor="rgba(96,165,250,0.4)",font=dict(family="JetBrains Mono",size=12,color="#e2e8f0")))
                fig.update_xaxes(gridcolor="rgba(255,255,255,0.04)",zeroline=False)
                fig.update_yaxes(gridcolor="rgba(255,255,255,0.04)",zeroline=False)
                for ann in fig.layout.annotations: ann.font.size=11; ann.font.color="#334155"
                st.plotly_chart(fig,use_container_width=True)

            col_s,col_f = st.columns([3,2],gap="large")
            with col_s:
                score=sent.get("score",0); sp=int((score+1)/2*100)
                sc2="#4ade80" if score>0.33 else "#f87171" if score<-0.33 else "#fbbf24"
                st.markdown(sec("📰 News Sentiment","FinBERT NLP","#34d399"), unsafe_allow_html=True)
                st.markdown(f"""<div style="background:rgba(255,255,255,0.025);border:1px solid rgba(255,255,255,0.065);border-radius:12px;padding:14px 16px;margin-bottom:12px;">
<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
<span style="font-size:0.68rem;color:#64748b;font-weight:700;text-transform:uppercase;letter-spacing:0.1em;">Aggregate Score</span>
<span style="font-family:'JetBrains Mono',monospace;font-size:0.95rem;font-weight:700;color:{sc2};">{score:+.2f}</span>
</div>
<div style="background:rgba(255,255,255,0.05);border-radius:5px;height:6px;overflow:hidden;">
<div style="width:{sp}%;height:100%;border-radius:5px;background:linear-gradient(90deg,{sc2}80,{sc2});box-shadow:0 0 8px {sc2}40;"></div>
</div></div>""", unsafe_allow_html=True)
                for art in sent.get("articles",[]): st.markdown(newscard(art), unsafe_allow_html=True)

            with col_f:
                st.markdown(sec("💼 Fundamentals","Live Data","#a78bfa"), unsafe_allow_html=True)
                def fmt(v,pre="&#8377;"):
                    if v in (None,"N/A"): return "N/A"
                    try:
                        v=float(v)
                        if pre=="&#8377;" and v>=1e7: return f"&#8377;{v/1e7:.2f}Cr"
                        return f"{pre}{v:,.2f}"
                    except: return str(v)
                rows=[("Market Cap",fmt(fund.get("Market Cap"))),("P/E Ratio",fmt(fund.get("P/E Ratio"),"")),
                      ("EPS",fmt(fund.get("EPS"))),("52W High",fmt(fund.get("52 Week High"))),
                      ("52W Low",fmt(fund.get("52 Week Low"))),("Current Price",fmt(fund.get("Current Price")))]
                rh="".join(f'<div style="display:flex;justify-content:space-between;padding:9px 0;border-bottom:1px solid rgba(255,255,255,0.05);"><span style="font-size:0.72rem;color:#64748b;font-weight:600;text-transform:uppercase;letter-spacing:0.07em;">{k}</span><span style="font-size:0.85rem;color:#f1f5f9;font-weight:700;font-family:JetBrains Mono,monospace;">{v}</span></div>' for k,v in rows)
                st.markdown(f'<div style="background:rgba(255,255,255,0.025);border:1px solid rgba(255,255,255,0.065);border-radius:14px;padding:16px;">{rh}</div>', unsafe_allow_html=True)
                ml_sig=dec.get("ml_signal","N/A"); ml_c="#4ade80" if ml_sig=="Buy" else "#f87171" if ml_sig=="Sell" else "#fbbf24"
                st.markdown(f"""<div style="background:rgba(255,255,255,0.025);border:1px solid rgba(255,255,255,0.065);border-radius:14px;padding:16px;margin-top:12px;">
<div style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid rgba(255,255,255,0.05);"><span style="font-size:0.72rem;color:#64748b;text-transform:uppercase;letter-spacing:0.07em;">ML Signal</span><span style="font-size:0.85rem;font-weight:700;color:{ml_c};">{ml_sig}</span></div>
<div style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid rgba(255,255,255,0.05);"><span style="font-size:0.72rem;color:#64748b;text-transform:uppercase;letter-spacing:0.07em;">Sentiment</span><span style="font-size:0.85rem;font-weight:700;color:{sent_c};">{sentiment_v}</span></div>
<div style="display:flex;justify-content:space-between;padding:8px 0;"><span style="font-size:0.72rem;color:#64748b;text-transform:uppercase;letter-spacing:0.07em;">Final Action</span><span style="font-size:1rem;font-weight:800;color:{action_c};">{action}</span></div>
</div>""", unsafe_allow_html=True)
                if logged_in:
                    st.markdown("<br>", unsafe_allow_html=True)
                    dry=st.toggle("Dry Run",value=True,key="dash_dry")
                    if st.button("⚡  Execute Signal",type="primary",use_container_width=True,key="dash_exec"):
                        with st.spinner("Executing..."):
                            res=api_post("/api/kotak/execute",{"symbol":ticker_input.upper(),"action":action,"confidence":conf,"product":"MIS","dry_run":dry})
                        if res:
                            sc3=res.get("status",""); c3="#4ade80" if sc3=="executed" else "#fbbf24" if sc3 in ("dry_run","skipped") else "#f87171"
                            st.markdown(f'<div style="background:{c3}10;border:1px solid {c3}35;border-radius:10px;padding:12px;font-size:0.83rem;color:{c3};margin-top:8px;"><strong>{sc3.upper()}</strong><br><span style="color:#94a3b8;">{res.get("message","")}</span></div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 — AI SIGNALS
# ═══════════════════════════════════════════════════════════════════════════════
with t_sig:
    st.markdown(sec("📡 AI Signal Scanner","Live Watchlist","#60a5fa"), unsafe_allow_html=True)
    cw1,cw2 = st.columns([4,1])
    with cw1:
        wl=st.text_input("Watchlist",placeholder="RELIANCE,TCS,INFY,HDFCBANK,SBIN",key="wl_in",label_visibility="collapsed")
        if wl and st.session_state.get("_wl_prev")!=wl:
            api_post("/api/signals/watchlist",{"symbols":[s.strip().upper() for s in wl.split(",") if s.strip()]})
            st.session_state["_wl_prev"]=wl
    with cw2:
        if st.button("🔄 Refresh",use_container_width=True,key="sig_ref"): st.rerun()

    sigs=(api_get("/api/signals/all") or {}).get("signals",[])
    if not sigs:
        st.markdown('<div style="text-align:center;padding:40px;color:#334155;">Signals loading — backend computing ML predictions...</div>', unsafe_allow_html=True)
    else:
        buys=sum(1 for s in sigs if "Buy" in s.get("action",""))
        sells=sum(1 for s in sigs if "Sell" in s.get("action",""))
        holds=sum(1 for s in sigs if s.get("action","")=="Hold")
        c1,c2,c3,c4=st.columns(4)
        c1.markdown(kpi("Signals",len(sigs),"#60a5fa"), unsafe_allow_html=True)
        c2.markdown(kpi("Buy",buys,"#4ade80","🟢"), unsafe_allow_html=True)
        c3.markdown(kpi("Sell",sells,"#f87171","🔴"), unsafe_allow_html=True)
        c4.markdown(kpi("Hold",holds,"#fbbf24","🟡"), unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        cols=st.columns(3)
        for i,sig in enumerate(sigs):
            a=sig.get("action","Hold"); cc=sig.get("confidence",0); ac2=ac(a)
            chg=sig.get("change_pct",0); chg_c="#4ade80" if chg>=0 else "#f87171"
            rsi=sig.get("rsi",50); rsi_c="#f87171" if rsi>=70 else "#4ade80" if rsi<=30 else "#94a3b8"
            with cols[i%3]:
                st.markdown(f"""<div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.07);
border-radius:14px;padding:16px;margin-bottom:12px;transition:all 0.2s;">
<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
<span style="font-size:0.95rem;font-weight:800;color:#f1f5f9;font-family:'JetBrains Mono',monospace;">{sig['symbol']}</span>
<span style="font-size:0.7rem;font-weight:700;color:{ac2};background:{ac2}18;border:1px solid {ac2}30;border-radius:20px;padding:3px 10px;">{a}</span>
</div>
<div style="display:flex;justify-content:space-between;margin-bottom:6px;"><span style="font-size:0.73rem;color:#64748b;">Price</span><span style="font-size:0.82rem;font-weight:700;color:#e2e8f0;font-family:'JetBrains Mono',monospace;">&#8377;{sig.get('price',0):,.2f}</span></div>
<div style="display:flex;justify-content:space-between;margin-bottom:6px;"><span style="font-size:0.73rem;color:#64748b;">Change</span><span style="font-size:0.8rem;font-weight:700;color:{chg_c};">{'+' if chg>=0 else ''}{chg:.2f}%</span></div>
<div style="display:flex;justify-content:space-between;margin-bottom:10px;"><span style="font-size:0.73rem;color:#64748b;">RSI</span><span style="font-size:0.8rem;font-weight:700;color:{rsi_c};">{rsi:.1f}</span></div>
<div style="background:rgba(255,255,255,0.05);border-radius:4px;height:4px;overflow:hidden;margin-bottom:5px;">
<div style="width:{cc}%;height:100%;background:linear-gradient(90deg,{ac2}80,{ac2});border-radius:4px;"></div></div>
<div style="display:flex;justify-content:space-between;"><span style="font-size:0.62rem;color:#334155;">Confidence</span><span style="font-size:0.68rem;font-weight:700;color:{ac2};font-family:'JetBrains Mono',monospace;">{cc:.1f}%</span></div>
</div>""", unsafe_allow_html=True)
                if logged_in and a in ("Buy","Strong Buy","Sell","Strong Sell"):
                    if st.button(f"⚡ {sig['symbol']}",key=f"se_{sig['symbol']}",use_container_width=True):
                        res=api_post("/api/kotak/execute",{"symbol":sig["symbol"],"action":a,"confidence":cc,"product":"MIS","dry_run":True})
                        if res: st.success(f"{res.get('status','').upper()}: {res.get('message','')}")

    # Live Feed
    st.markdown(sec("📡 Live Market Feed","WebSocket HSM","#34d399"), unsafe_allow_html=True)
    ws=api_get("/api/ws/status") or {}; mf=ws.get("market_feed",{}); of=ws.get("order_feed",{})
    mfc=mf.get("connected",False); ofc=of.get("connected",False)
    wc1,wc2,wc3=st.columns([1,1,2])
    with wc1:
        c2="#4ade80" if mfc else "#f87171"
        st.markdown(f'<div style="background:{c2}08;border:1px solid {c2}25;border-radius:10px;padding:12px;text-align:center;"><div style="font-size:0.62rem;color:#64748b;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:4px;">Market Feed</div><div style="font-size:0.82rem;font-weight:700;color:{c2};">{"🟢 LIVE" if mfc else "🔴 OFFLINE"}</div><div style="font-size:0.65rem;color:#334155;margin-top:3px;">{mf.get("subscribed",0)}/200</div></div>', unsafe_allow_html=True)
    with wc2:
        c3="#4ade80" if ofc else "#f87171"
        st.markdown(f'<div style="background:{c3}08;border:1px solid {c3}25;border-radius:10px;padding:12px;text-align:center;"><div style="font-size:0.62rem;color:#64748b;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:4px;">Order Feed</div><div style="font-size:0.82rem;font-weight:700;color:{c3};">{"🟢 LIVE" if ofc else "🔴 OFFLINE"}</div><div style="font-size:0.65rem;color:#334155;margin-top:3px;">{of.get("update_count",0)} updates</div></div>', unsafe_allow_html=True)
    with wc3:
        ws_sym=st.text_input("Subscribe symbol",placeholder="e.g. RELIANCE",key="ws_sym",label_visibility="collapsed")
        wb1,wb2=st.columns(2)
        with wb1:
            if st.button("📡 Connect",use_container_width=True,key="ws_conn"):
                if not logged_in: st.error("Login first")
                else:
                    r=api_post("/api/ws/connect")
                    if r: st.success(f"Connecting... dc={r.get('data_center','')}")
        with wb2:
            if st.button("➕ Subscribe",use_container_width=True,key="ws_sub"):
                if ws_sym:
                    r=api_get("/api/ws/subscribe/symbol",params={"symbol":ws_sym.upper()})
                    if r and r.get("subscribed"): st.success(f"Subscribed: {r.get('format','')}")
                    else: st.error("Failed")
    ticks=(api_get("/api/ws/ticks") or {}).get("ticks",{})
    if ticks:
        rows=[{"Scrip":sid,"LTP":f"&#8377;{t.get('ltp',0):,.2f}","Open":f"&#8377;{t.get('open',0):,.2f}","High":f"&#8377;{t.get('high',0):,.2f}","Low":f"&#8377;{t.get('low',0):,.2f}","Change%":f"{t.get('change_pct',0):+.2f}%","Vol":f"{t.get('volume',0):,}","Time":t.get("timestamp","")[:19].replace("T"," ")} for sid,t in list(ticks.items())[:20]]
        st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)
    else:
        st.markdown(f'<div style="color:#334155;padding:12px;font-size:0.83rem;">{"Connected — subscribe symbols above to see live ticks." if mfc else "Click Connect to start live market data."}</div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3 — LIVE TRADE
# ═══════════════════════════════════════════════════════════════════════════════
with t_trade:
    st.markdown(sec("⚡ Place Order","Manual","#fbbf24"), unsafe_allow_html=True)
    if not logged_in:
        st.markdown('<div style="background:rgba(248,113,113,0.07);border:1px solid rgba(248,113,113,0.25);border-radius:12px;padding:20px;text-align:center;color:#f87171;">Login to Kotak to place orders</div>', unsafe_allow_html=True)
    else:
        cf,ci=st.columns([3,2],gap="large")
        with cf:
            o_sym=st.text_input("Symbol",value="RELIANCE",key="o_sym").upper()
            oc1,oc2=st.columns(2)
            o_txn=oc1.selectbox("Transaction",["B — Buy","S — Sell"],key="o_txn")
            o_prod=oc2.selectbox("Product",["MIS","CNC","NRML"],key="o_prod")
            oc3,oc4=st.columns(2)
            o_type=oc3.selectbox("Order Type",["MKT","L","SL"],key="o_type")
            o_qty=oc4.number_input("Quantity",min_value=1,value=1,key="o_qty")
            if o_type in ("L","SL"):
                op1,op2=st.columns(2)
                o_price=op1.number_input("Price",min_value=0.0,value=0.0,step=0.05,key="o_price")
                o_trig=op2.number_input("Trigger",min_value=0.0,value=0.0,step=0.05,key="o_trig") if o_type=="SL" else 0.0
            else:
                o_price=o_trig=0.0
            ltp_d=api_get(f"/api/kotak/ltp/{o_sym}") if o_sym else None
            if ltp_d:
                ltp=ltp_d.get("ltp",0)
                st.markdown(f'<div style="background:rgba(96,165,250,0.06);border:1px solid rgba(96,165,250,0.18);border-radius:10px;padding:10px 14px;font-size:0.83rem;color:#94a3b8;margin-bottom:8px;">LTP: <strong style="color:#60a5fa;font-family:JetBrains Mono,monospace;">&#8377;{ltp:,.2f}</strong> &nbsp;·&nbsp; Est. Value: <strong style="color:#f1f5f9;">&#8377;{ltp*o_qty:,.2f}</strong></div>', unsafe_allow_html=True)
            if st.button("🔎  Check Margin",use_container_width=True,key="chk_m"):
                with st.spinner("Checking..."):
                    mg=api_get("/api/kotak/margin/check",params={"symbol":o_sym,"exchange":"nse_cm","price":float(o_price) if o_price else 0,"order_type":o_type,"product":o_prod,"quantity":int(o_qty),"transaction_type":o_txn.split(" — ")[0]})
                if mg:
                    ok=mg.get("rmsVldtd","")=="OK"; oc="#4ade80" if ok else "#f87171"
                    avl=float(str(mg.get("avlMrgn","0")).replace(",","") or 0)
                    req=float(str(mg.get("reqdMrgn","0")).replace(",","") or 0)
                    insuf=float(str(mg.get("insufFund","0")).replace(",","") or 0)
                    ir=f'<div style="display:flex;justify-content:space-between;"><span style="font-size:0.73rem;color:#64748b;">Shortfall</span><span style="font-size:0.8rem;font-weight:700;color:#f87171;font-family:JetBrains Mono,monospace;">&#8377;{insuf:,.2f}</span></div>' if not ok else ""
                    st.markdown(f'<div style="background:{oc}08;border:1px solid {oc}30;border-radius:10px;padding:14px;margin-top:4px;"><div style="font-size:0.78rem;font-weight:800;color:{oc};margin-bottom:10px;">{"✅ SUFFICIENT MARGIN" if ok else "❌ INSUFFICIENT FUNDS"}</div><div style="display:flex;justify-content:space-between;margin-bottom:5px;"><span style="font-size:0.73rem;color:#64748b;">Available</span><span style="font-size:0.8rem;font-weight:700;color:#4ade80;font-family:JetBrains Mono,monospace;">&#8377;{avl:,.2f}</span></div><div style="display:flex;justify-content:space-between;margin-bottom:5px;"><span style="font-size:0.73rem;color:#64748b;">Required</span><span style="font-size:0.8rem;font-weight:700;color:#fbbf24;font-family:JetBrains Mono,monospace;">&#8377;{req:,.2f}</span></div>{ir}</div>', unsafe_allow_html=True)
            if st.button("📋  Place Order",type="primary",use_container_width=True,key="place_btn"):
                with st.spinner("Placing..."):
                    r=api_post("/api/kotak/order/place",{"symbol":o_sym,"transaction_type":o_txn.split(" — ")[0],"quantity":int(o_qty),"order_type":o_type,"price":float(o_price),"trigger_price":float(o_trig),"product":o_prod})
                if r and r.get("status")=="success": st.success(f"✅ Order placed! {r.get('order',{})}")
                else: st.error(f"Failed: {r}" if r else "No response")
        with ci:
            st.markdown("""<div style="background:rgba(255,255,255,0.025);border:1px solid rgba(255,255,255,0.065);border-radius:12px;padding:16px;margin-bottom:12px;">
<div style="font-size:0.62rem;color:#334155;font-weight:700;text-transform:uppercase;letter-spacing:0.12em;margin-bottom:10px;">Order Types</div>
<div style="font-size:0.82rem;color:#94a3b8;line-height:2.0;"><strong style="color:#60a5fa;">MKT</strong> — Execute at market price<br><strong style="color:#a78bfa;">L</strong> — Execute at your price or better<br><strong style="color:#fbbf24;">SL</strong> — Stop-loss trigger order</div></div>
<div style="background:rgba(255,255,255,0.025);border:1px solid rgba(255,255,255,0.065);border-radius:12px;padding:16px;margin-bottom:12px;">
<div style="font-size:0.62rem;color:#334155;font-weight:700;text-transform:uppercase;letter-spacing:0.12em;margin-bottom:10px;">Products</div>
<div style="font-size:0.82rem;color:#94a3b8;line-height:2.0;"><strong style="color:#4ade80;">MIS</strong> — Intraday (sq-off 3:20PM)<br><strong style="color:#60a5fa;">CNC</strong> — Delivery (hold overnight)<br><strong style="color:#a78bfa;">NRML</strong> — Normal F&O</div></div>""", unsafe_allow_html=True)
            cancel_id=st.text_input("Cancel Order ID",placeholder="Paste order ID",key="cid")
            if st.button("❌  Cancel Order",use_container_width=True,key="cancel_btn"):
                if cancel_id:
                    try:
                        r=requests.delete(f"{API}/api/kotak/order/{cancel_id}",timeout=10)
                        st.success("Cancelled") if r.status_code==200 else st.error(r.json().get("detail",""))
                    except Exception as e: st.error(str(e))
                else: st.warning("Enter order ID")


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 4 — SCALPING BOT
# ═══════════════════════════════════════════════════════════════════════════════
with t_scalp:
    scl=api_get("/api/scalping/status") or {}; running=scl.get("running",False)
    st.markdown(sec("🎯 Options Scalping Bot","1-Min · 1:3 R:R","#34d399"), unsafe_allow_html=True)
    if running:
        st.markdown('<div style="background:rgba(74,222,128,0.07);border:1px solid rgba(74,222,128,0.25);border-radius:12px;padding:12px 18px;margin-bottom:16px;display:flex;align-items:center;gap:10px;"><div style="width:9px;height:9px;border-radius:50%;background:#4ade80;box-shadow:0 0 8px #4ade80;"></div><span style="font-weight:700;color:#4ade80;font-size:0.88rem;">BOT ACTIVE</span><span style="color:#94a3b8;font-size:0.8rem;margin-left:6px;">Scanning 1-min candles</span></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div style="background:rgba(255,255,255,0.025);border:1px solid rgba(255,255,255,0.07);border-radius:12px;padding:12px 18px;margin-bottom:16px;"><span style="font-weight:700;color:#64748b;font-size:0.88rem;">⬤ BOT STOPPED</span></div>', unsafe_allow_html=True)
    sc1,sc2=st.columns([2,1],gap="large")
    with sc1:
        s_sym=st.selectbox("Index",["BANKNIFTY","NIFTY","FINNIFTY"],key="scl_sym")
        sa1,sa2=st.columns(2)
        s_opt=sa1.selectbox("Option",["CE (Bullish)","PE (Bearish)"],key="scl_opt")
        s_lots=sa2.number_input("Lots",min_value=1,max_value=10,value=1,key="scl_lots")
        sb1,sb2=st.columns(2)
        s_sl=sb1.number_input("SL (pts)",min_value=5,max_value=200,value=30,key="scl_sl")
        s_rr=sb2.selectbox("R:R",["1:2","1:3","1:4"],index=1,key="scl_rr")
        s_dry=st.toggle("Dry Run",value=True,key="scl_dry")
        rr_val=float(s_rr.split(":")[1]); tgt=int(s_sl*rr_val)
        st.markdown(f'<div style="background:rgba(96,165,250,0.06);border:1px solid rgba(96,165,250,0.18);border-radius:10px;padding:10px 14px;font-size:0.82rem;color:#94a3b8;">SL: <strong style="color:#f87171;">{s_sl}pts</strong> &nbsp;·&nbsp; Target: <strong style="color:#4ade80;">{tgt}pts</strong> &nbsp;·&nbsp; R:R = <strong style="color:#fbbf24;">1:{int(rr_val)}</strong></div>', unsafe_allow_html=True)
        if st.button("💾  Save Config",use_container_width=True,key="scl_save"):
            r=api_post("/api/scalping/configure",{"symbol":s_sym,"option_type":s_opt.split()[0],"lots":s_lots,"sl_points":s_sl,"rr_ratio":rr_val,"dry_run":s_dry})
            if r: st.success("Saved")
    with sc2:
        st.markdown("<br>", unsafe_allow_html=True)
        if not running:
            if st.button("▶  START BOT",type="primary",use_container_width=True,key="scl_start"):
                if not logged_in: st.error("Login first")
                else:
                    r=api_post("/api/scalping/start")
                    if r: st.success(r.get("status","")); st.rerun()
        else:
            if st.button("⏹  STOP BOT",use_container_width=True,key="scl_stop"):
                api_post("/api/scalping/stop"); st.rerun()
        cfg=scl.get("config",{})
        st.markdown(f"""<div style="background:rgba(255,255,255,0.025);border:1px solid rgba(255,255,255,0.065);border-radius:10px;padding:14px;margin-top:12px;font-size:0.79rem;color:#94a3b8;line-height:2.0;">
<strong style="color:#f1f5f9;">Active Config</strong><br>
Symbol: <strong style="color:#60a5fa;">{cfg.get('symbol','—')}</strong><br>
Type: <strong style="color:#a78bfa;">{cfg.get('option_type','—')}</strong><br>
Lots: <strong style="color:#f1f5f9;">{cfg.get('lots','—')}</strong><br>
SL: <strong style="color:#f87171;">{cfg.get('sl_points','—')}pts</strong><br>
Target: <strong style="color:#4ade80;">{cfg.get('target_points','—')}pts</strong><br>
Mode: <strong style="color:{'#fbbf24' if cfg.get('dry_run') else '#f87171'};">{'DRY RUN' if cfg.get('dry_run') else '⚠ LIVE'}</strong>
</div>""", unsafe_allow_html=True)
    st.markdown(sec("Bot Log","","#34d399"), unsafe_allow_html=True)
    lc={"SIGNAL":"#60a5fa","EXECUTED":"#4ade80","DRY_RUN":"#fbbf24","ERROR":"#f87171","SCAN":"#334155","BLOCKED":"#f87171"}
    log_d=(api_get("/api/scalping/log") or {}).get("log",[])
    if log_d:
        for e in log_d[:15]: st.markdown(logrow(e.get("type",""),e.get("message",""),e.get("timestamp",""),lc.get(e.get("type",""),"#64748b")), unsafe_allow_html=True)
    else:
        st.markdown('<div style="color:#334155;padding:14px;font-size:0.83rem;">No activity yet. Start the bot to see logs.</div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 5 — AUTO BOT
# ═══════════════════════════════════════════════════════════════════════════════
with t_auto:
    at=api_get("/api/autotrader/status") or {}; atr=at.get("running",False)
    st.markdown(sec("🤖 Auto Trader","AI Signals → Auto Execution","#a78bfa"), unsafe_allow_html=True)
    if atr:
        st.markdown(f'<div style="background:rgba(74,222,128,0.07);border:1px solid rgba(74,222,128,0.25);border-radius:12px;padding:14px 20px;margin-bottom:16px;display:flex;align-items:center;justify-content:space-between;"><div style="display:flex;align-items:center;gap:10px;"><div style="width:10px;height:10px;border-radius:50%;background:#4ade80;box-shadow:0 0 10px #4ade80;"></div><span style="font-size:0.95rem;font-weight:800;color:#4ade80;">AUTO TRADER RUNNING</span></div><span style="font-size:0.78rem;color:#94a3b8;">Every {at.get("config",{}).get("scan_interval_s",300)}s</span></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div style="background:rgba(255,255,255,0.025);border:1px solid rgba(255,255,255,0.07);border-radius:12px;padding:14px 20px;margin-bottom:16px;"><span style="font-size:0.95rem;font-weight:700;color:#64748b;">⬤ AUTO TRADER STOPPED</span></div>', unsafe_allow_html=True)
    aa1,aa2=st.columns([2,1],gap="large")
    with aa1:
        at_syms=st.text_input("Symbols",value="RELIANCE,TCS,INFY,HDFCBANK,ICICIBANK",key="at_syms")
        ab1,ab2=st.columns(2)
        at_conf=ab1.slider("Min Confidence %",50,95,68,key="at_conf")
        at_max=ab2.number_input("Max Trades/Day",1,50,10,key="at_max")
        ab3,ab4=st.columns(2)
        at_int=ab3.selectbox("Scan Interval",["60s","120s","300s","600s"],index=2,key="at_int")
        at_prod=ab4.selectbox("Product",["MIS","CNC"],key="at_prod")
        at_dry=st.toggle("Dry Run Mode",value=True,key="at_dry")
        if not at_dry:
            st.markdown('<div style="background:rgba(248,113,113,0.08);border:1px solid rgba(248,113,113,0.3);border-radius:8px;padding:10px 14px;font-size:0.8rem;color:#f87171;">⚠️ <strong>LIVE MODE</strong> — Real money will be used.</div>', unsafe_allow_html=True)
        if st.button("💾  Save Config",use_container_width=True,key="at_save"):
            syms=[s.strip().upper() for s in at_syms.split(",") if s.strip()]
            r=api_post("/api/autotrader/configure",{"symbols":syms,"scan_interval_s":int(at_int.replace("s","")),"min_confidence":float(at_conf),"product":at_prod,"dry_run":at_dry,"max_trades_day":int(at_max)})
            if r: st.success("Saved")
    with aa2:
        st.markdown("<br>", unsafe_allow_html=True)
        if not atr:
            if st.button("▶  START AUTO TRADER",type="primary",use_container_width=True,key="at_start"):
                if not logged_in: st.error("Login first")
                else:
                    r=api_post("/api/autotrader/start")
                    if r: st.success(r.get("status","")); st.rerun()
        else:
            if st.button("⏹  STOP",use_container_width=True,key="at_stop"):
                api_post("/api/autotrader/stop"); st.rerun()
        ar=at.get("risk_status",{}); ap=ar.get("daily_pnl",0); apc="#4ade80" if ap>=0 else "#f87171"
        st.markdown(f"""<div style="background:rgba(255,255,255,0.025);border:1px solid rgba(255,255,255,0.065);border-radius:10px;padding:14px;margin-top:12px;font-size:0.79rem;color:#94a3b8;line-height:2.0;">
<strong style="color:#f1f5f9;">Risk Summary</strong><br>
Daily P&L: <strong style="color:{apc};">&#8377;{ap:,.2f}</strong><br>
Positions: <strong style="color:#60a5fa;">{ar.get('open_positions',0)}/{ar.get('max_positions',5)}</strong><br>
Trades: <strong style="color:#a78bfa;">{at.get('trades_today',0)}</strong>
</div>""", unsafe_allow_html=True)
    st.markdown(sec("Execution Log","","#a78bfa"), unsafe_allow_html=True)
    lc2={"EXECUTED":"#4ade80","DRY_RUN":"#fbbf24","SCAN":"#334155","ERROR":"#f87171","BLOCKED":"#f87171","WARN":"#fbbf24"}
    at_log=(api_get("/api/autotrader/log") or {}).get("log",[])
    if at_log:
        for e in at_log[:20]: st.markdown(logrow(e.get("type",""),e.get("message",""),e.get("timestamp",""),lc2.get(e.get("type",""),"#64748b")), unsafe_allow_html=True)
    else:
        st.markdown('<div style="color:#334155;padding:14px;font-size:0.83rem;">No activity yet.</div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 6 — PORTFOLIO
# ═══════════════════════════════════════════════════════════════════════════════
with t_port:
    st.markdown(sec("💰 Portfolio & P&L","Live Data","#4ade80"), unsafe_allow_html=True)
    if not logged_in:
        st.markdown('<div style="background:rgba(248,113,113,0.07);border:1px solid rgba(248,113,113,0.25);border-radius:12px;padding:20px;text-align:center;color:#f87171;">Login to Kotak to view portfolio</div>', unsafe_allow_html=True)
    else:
        limits = api_get("/api/kotak/limits/full") or {}
        net         = float(str(limits.get("Net","0")).replace(",","") or 0)
        collateral  = float(str(limits.get("CollateralValue","0")).replace(",","") or 0)
        margin_used = float(str(limits.get("MarginUsed","0")).replace(",","") or 0)
        unreal      = float(str(limits.get("UnrealizedMtomPrsnt","0")).replace(",","") or 0)
        risk_d      = api_get("/api/kotak/risk/status") or {}
        pnl         = risk_d.get("daily_pnl",0)
        pnl_c       = "#4ade80" if pnl>=0 else "#f87171"
        net_c       = "#4ade80" if net>0 else "#f87171"

        c1,c2,c3,c4 = st.columns(4)
        c1.markdown(kpi("Net Available",f"&#8377;{net:,.2f}",net_c,"Cash + Collateral"), unsafe_allow_html=True)
        c2.markdown(kpi("Collateral",f"&#8377;{collateral:,.2f}","#60a5fa","Pledged"), unsafe_allow_html=True)
        c3.markdown(kpi("Margin Used",f"&#8377;{margin_used:,.2f}","#f87171" if margin_used>0 else "#94a3b8","Active"), unsafe_allow_html=True)
        c4.markdown(kpi("Daily P&L",f"&#8377;{pnl:,.2f}",pnl_c,"Session"), unsafe_allow_html=True)

        if unreal != 0:
            mc1,mc2,mc3 = st.columns(3)
            mc1.markdown(kpi("Unrealised MTM",f"&#8377;{unreal:,.2f}","#4ade80" if unreal>=0 else "#f87171"), unsafe_allow_html=True)
            mc2.markdown(kpi("Open Positions",risk_d.get("open_positions",0),"#a78bfa"), unsafe_allow_html=True)
            mc3.markdown(kpi("Trades Today",risk_d.get("daily_trades",0),"#60a5fa"), unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        
        # ── Kotak Login Section ──────────────────────────────────────────────
        st.markdown("### 🔐 Kotak Neo Authentication")
        
        status = api_get("/api/kotak/status") or {}
        logged_in = status.get("logged_in", False)
        
        col_status, col_action = st.columns([2, 1])
        
        with col_status:
            if logged_in:
                st.success("✅ KOTAK CONNECTED")
            else:
                st.warning("⚠️ NOT LOGGED IN")
        
        with col_action:
            if logged_in:
                if st.button("🔓 Logout", use_container_width=True):
                    api_post("/api/kotak/logout")
                    st.rerun()
            else:
                if st.button("🔐 Login", type="primary", use_container_width=True):
                    st.session_state["show_kotak_login"] = True
        
        # Login form
        if st.session_state.get("show_kotak_login") and not logged_in:
            st.markdown("---")
            st.markdown("#### Enter TOTP Code")
            totp_input = st.text_input("6-digit TOTP from Google Authenticator", max_chars=6, key="kotak_totp")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ Submit", type="primary", use_container_width=True):
                    with st.spinner("Authenticating..."):
                        r = api_post("/api/kotak/login", {"totp": totp_input})
                    if r and r.get("status") == "success":
                        st.success("✅ Logged in successfully!")
                        st.session_state.pop("show_kotak_login", None)
                        st.rerun()
                    else:
                        st.error(r.get("message", "Login failed") if r else "Connection error")
            
            with col2:
                if st.button("❌ Cancel", use_container_width=True):
                    st.session_state.pop("show_kotak_login", None)
                    st.rerun()
        
        st.markdown("---")
        
        pt1,pt2,pt3 = st.tabs(["📍 Positions","🏦 Holdings","🤖 AI Execution Log"])

        with pt1:
            pos = (api_get("/api/kotak/positions") or {}).get("positions",[])
            if pos and isinstance(pos,list) and len(pos)>0:
                try:
                    df=pd.DataFrame(pos)
                    rn={"trdSym":"Symbol","sym":"Name","qty":"Net Qty","prod":"Product","exSeg":"Exchange","buyAmt":"Buy Amt","sellAmt":"Sell Amt","flBuyQty":"Filled Buy","flSellQty":"Filled Sell"}
                    df=df.rename(columns={k:v for k,v in rn.items() if k in df.columns})
                    show=[c for c in ["Symbol","Name","Net Qty","Product","Exchange","Buy Amt","Sell Amt","Filled Buy","Filled Sell"] if c in df.columns]
                    st.dataframe(df[show] if show else df,use_container_width=True,hide_index=True)
                    try:
                        tb=sum(float(p.get("buyAmt",0)) for p in pos)
                        ts=sum(float(p.get("sellAmt",0)) for p in pos)
                        np2=ts-tb; npc="#4ade80" if np2>=0 else "#f87171"
                        st.markdown(f'<div style="display:flex;gap:12px;margin-top:12px;flex-wrap:wrap;">'+
                            "".join([f'<div style="background:rgba(255,255,255,0.025);border:1px solid rgba(255,255,255,0.065);border-radius:10px;padding:12px 18px;flex:1;"><div style="font-size:0.62rem;color:#334155;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:4px;">{l}</div><div style="font-size:1rem;font-weight:700;color:{c};font-family:JetBrains Mono,monospace;">&#8377;{v:,.2f}</div></div>' for l,v,c in [("Total Buy",tb,"#f87171"),("Total Sell",ts,"#4ade80"),("Net P&L",np2,npc)]])+
                            '</div>', unsafe_allow_html=True)
                    except Exception: pass
                except Exception: st.json(pos)
            else:
                st.markdown('<div style="color:#334155;padding:20px;text-align:center;">No open positions today</div>', unsafe_allow_html=True)

        with pt2:
            hold = (api_get("/api/kotak/holdings") or {}).get("holdings",[])
            if hold and isinstance(hold,list) and len(hold)>0:
                try:
                    df=pd.DataFrame(hold)
                    rn={"displaySymbol":"Symbol","instrumentName":"Name","quantity":"Qty","averagePrice":"Avg Price","closingPrice":"Close","mktValue":"Mkt Value","unrealisedGainLoss":"Unrealised P&L","sellableQuantity":"Sellable","exchangeSegment":"Exchange","subType":"Type"}
                    df=df.rename(columns={k:v for k,v in rn.items() if k in df.columns})
                    show=[c for c in ["Symbol","Name","Qty","Avg Price","Close","Mkt Value","Unrealised P&L","Sellable","Exchange","Type"] if c in df.columns]
                    st.dataframe(df[show] if show else df,use_container_width=True,hide_index=True)
                    try:
                        tc=sum(float(h.get("holdingCost",0)) for h in hold)
                        tv=sum(float(h.get("mktValue",0)) for h in hold)
                        tp=sum(float(h.get("unrealisedGainLoss",0)) for h in hold)
                        tpc="#4ade80" if tp>=0 else "#f87171"
                        st.markdown(f'<div style="display:flex;gap:12px;margin-top:12px;flex-wrap:wrap;">'+
                            "".join([f'<div style="background:rgba(255,255,255,0.025);border:1px solid rgba(255,255,255,0.065);border-radius:10px;padding:12px 18px;flex:1;"><div style="font-size:0.62rem;color:#334155;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:4px;">{l}</div><div style="font-size:1rem;font-weight:700;color:{c};font-family:JetBrains Mono,monospace;">&#8377;{v:,.2f}</div></div>' for l,v,c in [("Total Cost",tc,"#94a3b8"),("Market Value",tv,"#60a5fa"),("Unrealised P&L",tp,tpc)]])+
                            '</div>', unsafe_allow_html=True)
                    except Exception: pass
                except Exception: st.json(hold)
            else:
                st.markdown('<div style="color:#334155;padding:20px;text-align:center;">No holdings found</div>', unsafe_allow_html=True)

        with pt3:
            elog=(api_get("/api/kotak/execution/log") or {}).get("log",[])
            if elog:
                df=pd.DataFrame(elog)
                show=[c for c in ["timestamp","symbol","action","status","ltp","quantity","sl_price","message"] if c in df.columns]
                st.dataframe(df[show] if show else df,use_container_width=True,hide_index=True)
            else:
                st.markdown('<div style="color:#334155;padding:20px;text-align:center;">No AI execution history this session</div>', unsafe_allow_html=True)

        # Order Book
        st.markdown(sec("📋 Today's Orders","","#60a5fa"), unsafe_allow_html=True)
        or1,or2,or3=st.columns([1,2,1])
        with or1:
            if st.button("🔄 Refresh",use_container_width=True,key="ord_ref"): st.rerun()
        with or2:
            cid=st.text_input("Order ID to cancel",placeholder="Paste order ID",key="port_cid",label_visibility="collapsed")
        with or3:
            if st.button("❌ Cancel",use_container_width=True,key="port_cancel"):
                if cid:
                    try:
                        r=requests.delete(f"{API}/api/kotak/order/{cid}",timeout=10)
                        st.success("Cancelled") if r.status_code==200 else st.error(r.json().get("detail",""))
                    except Exception as e: st.error(str(e))
                else: st.warning("Enter order ID")

        orders=(api_get("/api/kotak/orders") or {}).get("orders",[])
        if orders and isinstance(orders,list) and len(orders)>0:
            try:
                df=pd.DataFrame(orders)
                rn={"nOrdNo":"Order ID","ordSt":"Status","trdSym":"Symbol","qty":"Qty","prc":"Price","avgPrc":"Avg Price","trnsTp":"B/S","prcTp":"Type","vldt":"Validity","exSeg":"Exchange","rejRsn":"Reject Reason","ordDtTm":"Time"}
                df=df.rename(columns={k:v for k,v in rn.items() if k in df.columns})
                show=[c for c in ["Order ID","Symbol","B/S","Qty","Price","Avg Price","Type","Status","Validity","Exchange","Reject Reason","Time"] if c in df.columns]
                st.dataframe(df[show] if show else df,use_container_width=True,hide_index=True)
                st.markdown("<br>", unsafe_allow_html=True)
                hid=st.text_input("View order history (enter Order ID)",placeholder="e.g. 250720000007242",key="hist_id")
                if hid and st.button("📜 Load History",use_container_width=True,key="load_hist"):
                    hist=(api_get(f"/api/kotak/orders/{hid}/history") or {}).get("history",[])
                    if hist:
                        df_h=pd.DataFrame(hist)
                        rn_h={"nOrdNo":"Order ID","ordSt":"Status","flDtTm":"Time","rejRsn":"Reject Reason","qty":"Qty","prc":"Price","avgPrc":"Avg Price","prod":"Product","trnsTp":"B/S","prcTp":"Type"}
                        df_h=df_h.rename(columns={k:v for k,v in rn_h.items() if k in df_h.columns})
                        show_h=[c for c in ["Time","Status","Qty","Price","Avg Price","Product","B/S","Type","Reject Reason"] if c in df_h.columns]
                        st.markdown(f'<div style="font-size:0.72rem;font-weight:700;color:#64748b;margin-bottom:6px;">Order {hid} — {len(hist)} status updates</div>', unsafe_allow_html=True)
                        st.dataframe(df_h[show_h] if show_h else df_h,use_container_width=True,hide_index=True)
                    else: st.info("No history found.")
            except Exception: st.json(orders)
        else:
            st.markdown('<div style="color:#334155;padding:14px;text-align:center;">No orders today</div>', unsafe_allow_html=True)

        # Trade Book
        st.markdown(sec("💹 Trade Book","Executed","#4ade80"), unsafe_allow_html=True)
        trades=(api_get("/api/kotak/trades") or {}).get("trades",[])
        if trades and isinstance(trades,list) and len(trades)>0:
            try:
                df_t=pd.DataFrame(trades)
                rn_t={"nOrdNo":"Order ID","trdSym":"Symbol","qty":"Qty","avgPrc":"Avg Price","fldQty":"Filled","flDt":"Date","exTm":"Time","prcTp":"Type","prod":"Product","trnsTp":"B/S","exOrdId":"Exchange ID"}
                df_t=df_t.rename(columns={k:v for k,v in rn_t.items() if k in df_t.columns})
                show_t=[c for c in ["Symbol","B/S","Qty","Avg Price","Filled","Date","Time","Type","Product","Order ID"] if c in df_t.columns]
                st.dataframe(df_t[show_t] if show_t else df_t,use_container_width=True,hide_index=True)
                try:
                    bt=[t for t in trades if t.get("trnsTp","")=="B"]; st2=[t for t in trades if t.get("trnsTp","")=="S"]
                    bv=sum(float(t.get("avgPrc",0))*int(t.get("qty",0)) for t in bt)
                    sv=sum(float(t.get("avgPrc",0))*int(t.get("qty",0)) for t in st2)
                    st.markdown(f'<div style="display:flex;gap:12px;margin-top:12px;flex-wrap:wrap;">'+
                        "".join([f'<div style="background:rgba(255,255,255,0.025);border:1px solid rgba(255,255,255,0.065);border-radius:10px;padding:12px 18px;flex:1;"><div style="font-size:0.62rem;color:#334155;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:4px;">{l}</div><div style="font-size:1rem;font-weight:700;color:{c};font-family:JetBrains Mono,monospace;">{v}</div></div>' for l,v,c in [(f"Buy Trades ({len(bt)})",f"&#8377;{bv:,.2f}","#f87171"),(f"Sell Trades ({len(st2)})",f"&#8377;{sv:,.2f}","#4ade80"),("Total Trades",str(len(trades)),"#60a5fa")]])+
                        '</div>', unsafe_allow_html=True)
                except Exception: pass
            except Exception: st.json(trades)
        else:
            st.markdown('<div style="color:#334155;padding:14px;text-align:center;">No trades executed today</div>', unsafe_allow_html=True)
