import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import math

# ═══════════════════════════════════════════════════════════════════════════════
# PAGE CONFIG
# ═══════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="StockSense AI",
    layout="wide",
    page_icon="⚡",
    initial_sidebar_state="collapsed"
)

# ═══════════════════════════════════════════════════════════════════════════════
# API CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════
API_URL = "https://ai-project-1-ooli.onrender.com"

# ═══════════════════════════════════════════════════════════════════════════════
# STYLING
# ═══════════════════════════════════════════════════════════════════════════════
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
.stTabs [data-baseweb="tab-list"]{background:rgba(255,255,255,0.02)!important;border-radius:14px!important;padding:5px!important;border:1px solid var(--b1)!important;gap:3px!important;}
.stTabs [data-baseweb="tab"]{background:transparent!important;border-radius:10px!important;color:var(--t3)!important;font-weight:600!important;font-size:0.82rem!important;padding:8px 16px!important;transition:all 0.2s!important;border:none!important;letter-spacing:0.01em!important;}
.stTabs [aria-selected="true"]{background:linear-gradient(135deg,rgba(96,165,250,0.18),rgba(167,139,250,0.18))!important;color:var(--t1)!important;box-shadow:0 2px 16px rgba(96,165,250,0.2),inset 0 1px 0 rgba(255,255,255,0.07)!important;}
.stTabs [data-baseweb="tab"]:hover{color:var(--t1)!important;background:rgba(255,255,255,0.05)!important;}
.stButton>button[kind="primary"]{background:linear-gradient(135deg,#1d4ed8 0%,#7c3aed 100%)!important;border:none!important;border-radius:10px!important;color:#fff!important;font-weight:700!important;font-size:0.85rem!important;letter-spacing:0.05em!important;padding:0.58rem 1.4rem!important;transition:all 0.22s!important;box-shadow:0 4px 18px rgba(29,78,216,0.4)!important;text-transform:uppercase!important;}
.stButton>button[kind="primary"]:hover{transform:translateY(-2px)!important;box-shadow:0 8px 30px rgba(29,78,216,0.6)!important;filter:brightness(1.1)!important;}
.stDataFrame{border-radius:12px!important;overflow:hidden!important;}
.stDataFrame thead th{background:rgba(255,255,255,0.05)!important;color:var(--t3)!important;font-size:0.7rem!important;text-transform:uppercase!important;letter-spacing:0.1em!important;font-weight:700!important;border-bottom:1px solid var(--b1)!important;}
.stDataFrame tbody td{color:var(--t2)!important;font-size:0.83rem!important;border-color:var(--b1)!important;}
.stDataFrame tbody tr:hover td{background:rgba(255,255,255,0.025)!important;}
.stMetric{background:rgba(255,255,255,0.03)!important;border:1px solid rgba(255,255,255,0.07)!important;border-radius:14px!important;padding:20px 14px!important;}
::-webkit-scrollbar{width:5px;height:5px;}
::-webkit-scrollbar-track{background:transparent;}
::-webkit-scrollbar-thumb{background:rgba(255,255,255,0.1);border-radius:3px;}
::-webkit-scrollbar-thumb:hover{background:rgba(255,255,255,0.2);}
</style>""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def api_get(path, params=None):
    """Make GET request to backend API"""
    try:
        r = requests.get(f"{API_URL}{path}", params=params, timeout=8)
        return r.json() if r.status_code == 200 else None
    except Exception as e:
        return None

def api_post(path, data=None):
    """Make POST request to backend API"""
    try:
        r = requests.post(f"{API_URL}{path}", json=data or {}, timeout=20)
        return r.json() if r.status_code == 200 else None
    except Exception as e:
        return None

def action_color(action):
    """Get color for action signal"""
    colors = {
        "Strong Buy": "#4ade80",
        "Buy": "#86efac",
        "Hold": "#fbbf24",
        "Sell": "#f87171",
        "Strong Sell": "#ef4444"
    }
    return colors.get(action, "#94a3b8")

def format_number(value, prefix=""):
    """Format numbers for display"""
    if value is None or value == "N/A":
        return "N/A"
    try:
        v = float(value)
        if prefix == "₹" and v >= 1e7:
            return f"₹{v/1e7:.2f}Cr"
        return f"{prefix}{v:,.2f}"
    except:
        return str(value)

def clean_dict(d):
    """Clean NaN and inf values from dict"""
    if isinstance(d, dict):
        return {k: clean_dict(v) for k, v in d.items()}
    elif isinstance(d, list):
        return [clean_dict(x) for x in d]
    elif isinstance(d, float):
        if math.isnan(d) or math.isinf(d):
            return None
        return d
    else:
        return d

# ═══════════════════════════════════════════════════════════════════════════════
# PAGE HEADER
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("""<div style="margin-bottom:22px;">
<div style="font-size:1.9rem;font-weight:900;letter-spacing:-0.04em;line-height:1.1;
background:linear-gradient(135deg,#60a5fa 0%,#a78bfa 45%,#34d399 100%);
-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;">
⚡ StockSense AI — Indian Stock Intelligence</div>
<div style="font-size:0.83rem;color:#334155;margin-top:6px;font-weight:500;">
FinBERT Sentiment · ML Prediction · Live Trading · Options Scalping · Chart Vision
</div></div>""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN TABS
# ═══════════════════════════════════════════════════════════════════════════════
tab_dashboard, tab_portfolio, tab_logs, tab_analysis = st.tabs([
    "📊 Dashboard",
    "📈 Portfolio",
    "📜 Logs",
    "🤖 AI Analysis"
])

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1: DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════════
with tab_dashboard:
    st.markdown("### Key Metrics")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📡 Total Signals", "12", "+2 today")
    
    with col2:
        st.metric("⚡ Active Trades", "3", "₹45,230 P&L")
    
    with col3:
        st.metric("📊 Market Status", "Open", "NSE/BSE")
    
    with col4:
        st.metric("🎯 Win Rate", "68%", "+5% this week")
    
    st.markdown("---")
    
    # Signals Overview Chart
    st.markdown("### Signals Overview")
    signals_data = {
        "Signal": ["Buy", "Sell", "Hold", "Strong Buy", "Strong Sell"],
        "Count": [5, 3, 2, 1, 1]
    }
    signals_df = pd.DataFrame(signals_data)
    
    fig = go.Figure(data=[
        go.Bar(x=signals_df["Signal"], y=signals_df["Count"], 
               marker_color=["#86efac", "#f87171", "#fbbf24", "#4ade80", "#ef4444"])
    ])
    fig.update_layout(
        template="plotly_dark",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        height=300,
        margin=dict(l=0, r=0, t=0, b=0)
    )
    st.plotly_chart(fig, use_container_width=True)

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2: PORTFOLIO
# ═══════════════════════════════════════════════════════════════════════════════
with tab_portfolio:
    st.markdown("### Open Positions")
    
    with st.spinner("Fetching positions..."):
        positions = api_get("/api/kotak/positions")
    
    if positions and "positions" in positions:
        pos_list = positions["positions"]
        if pos_list:
            # Format positions data
            pos_data = []
            for pos in pos_list:
                pos_data.append({
                    "Symbol": pos.get("trdSym", "N/A"),
                    "Quantity": pos.get("qty", 0),
                    "Avg Price": format_number(pos.get("buyAmt", 0), "₹"),
                    "Current Price": format_number(pos.get("sellAmt", 0), "₹"),
                    "P&L": format_number(pos.get("sellAmt", 0) - pos.get("buyAmt", 0), "₹")
                })
            
            pos_df = pd.DataFrame(pos_data)
            st.dataframe(pos_df, use_container_width=True, hide_index=True)
        else:
            st.info("No open positions")
    else:
        st.warning("⚠️ Unable to fetch positions. Please check backend connection.")
    
    st.markdown("---")
    st.markdown("### Holdings (Demat)")
    
    with st.spinner("Fetching holdings..."):
        holdings = api_get("/api/kotak/holdings")
    
    if holdings and "holdings" in holdings:
        hold_list = holdings["holdings"]
        if hold_list:
            hold_data = []
            for hold in hold_list:
                hold_data.append({
                    "Symbol": hold.get("symbol", "N/A"),
                    "Quantity": hold.get("quantity", 0),
                    "Avg Price": format_number(hold.get("averagePrice", 0), "₹"),
                    "Current Price": format_number(hold.get("closingPrice", 0), "₹"),
                    "Market Value": format_number(hold.get("mktValue", 0), "₹")
                })
            
            hold_df = pd.DataFrame(hold_data)
            st.dataframe(hold_df, use_container_width=True, hide_index=True)
        else:
            st.info("No holdings")
    else:
        st.warning("⚠️ Unable to fetch holdings. Please check backend connection.")

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3: LOGS
# ═══════════════════════════════════════════════════════════════════════════════
with tab_logs:
    st.markdown("### Execution Logs")
    
    log_filter = st.selectbox("Filter by Level", ["All", "Info", "Warning", "Error"])
    
    with st.spinner("Fetching logs..."):
        exec_log = api_get("/api/kotak/execution/log")
    
    if exec_log and "log" in exec_log:
        logs = exec_log["log"]
        if logs:
            log_data = []
            for log in logs:
                log_data.append({
                    "Timestamp": log.get("timestamp", "N/A"),
                    "Level": log.get("level", "INFO"),
                    "Message": log.get("message", "N/A")
                })
            
            log_df = pd.DataFrame(log_data)
            
            # Apply filter
            if log_filter != "All":
                log_df = log_df[log_df["Level"] == log_filter.upper()]
            
            st.dataframe(log_df, use_container_width=True, hide_index=True)
        else:
            st.info("No logs available")
    else:
        st.warning("⚠️ Unable to fetch logs. Please check backend connection.")
    
    st.markdown("---")
    st.markdown("### Scalping Bot Logs")
    
    with st.spinner("Fetching scalping logs..."):
        scalp_log = api_get("/api/scalping/log")
    
    if scalp_log and "log" in scalp_log:
        logs = scalp_log["log"]
        if logs:
            st.text_area("Scalping Logs", value="\n".join(logs), height=200, disabled=True)
        else:
            st.info("No scalping logs")
    else:
        st.warning("⚠️ Unable to fetch scalping logs.")

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 4: AI ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════════
with tab_analysis:
    st.markdown("### Stock Analysis")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        ticker = st.text_input("Enter Ticker Symbol", value="RELIANCE", placeholder="e.g., TCS, INFY, SBIN")
    
    with col2:
        period = st.selectbox("Period", ["1mo", "3mo", "6mo", "1y", "2y"], index=3)
    
    if st.button("🔍 Analyze", type="primary", use_container_width=False):
        with st.spinner(f"Analyzing {ticker.upper()}..."):
            data = api_get(f"/api/analyze/{ticker}", {"period": period})
        
        if data:
            # Extract data
            fund = data.get("fundamentals", {})
            dec = data.get("decision", {})
            sent = data.get("sentiment", {})
            
            action = dec.get("action", "Hold")
            conf = dec.get("confidence", 0)
            sentiment_v = dec.get("sentiment_signal", "Neutral")
            price = fund.get("Current Price", "N/A")
            
            # Display metrics
            st.markdown(f"### {ticker.upper()} Analysis")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Current Price", f"₹{price}", "Live")
            
            with col2:
                st.metric("AI Signal", action, f"{conf}% confidence")
            
            with col3:
                st.metric("Sentiment", sentiment_v, "FinBERT")
            
            with col4:
                st.metric("ML Signal", dec.get("ml_signal", "N/A"), "Random Forest")
            
            st.markdown("---")
            
            # Fundamentals
            st.markdown("### Fundamentals")
            fund_data = {
                "Metric": ["Market Cap", "P/E Ratio", "EPS", "52W High", "52W Low"],
                "Value": [
                    format_number(fund.get("Market Cap"), "₹"),
                    format_number(fund.get("P/E Ratio"), ""),
                    format_number(fund.get("EPS"), "₹"),
                    format_number(fund.get("52 Week High"), "₹"),
                    format_number(fund.get("52 Week Low"), "₹")
                ]
            }
            fund_df = pd.DataFrame(fund_data)
            st.dataframe(fund_df, use_container_width=True, hide_index=True)
            
            st.markdown("---")
            
            # Chart
            st.markdown("### Price Chart")
            chart_data = pd.DataFrame(data.get("chart_data", []))
            
            if not chart_data.empty:
                fig = make_subplots(
                    rows=2, cols=1,
                    shared_xaxes=True,
                    vertical_spacing=0.1,
                    subplot_titles=("Price", "RSI"),
                    row_heights=[0.7, 0.3]
                )
                
                # Candlestick
                fig.add_trace(
                    go.Candlestick(
                        x=chart_data["Date"],
                        open=chart_data["Open"],
                        high=chart_data["High"],
                        low=chart_data["Low"],
                        close=chart_data["Close"],
                        name="Price",
                        increasing_line_color="#4ade80",
                        decreasing_line_color="#f87171"
                    ),
                    row=1, col=1
                )
                
                # RSI
                if "RSI" in chart_data.columns:
                    rsi = pd.to_numeric(chart_data["RSI"], errors="coerce")
                    fig.add_trace(
                        go.Scatter(
                            x=chart_data["Date"],
                            y=rsi,
                            name="RSI",
                            line=dict(color="#a78bfa", width=2)
                        ),
                        row=2, col=1
                    )
                
                fig.update_layout(
                    height=600,
                    template="plotly_dark",
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    xaxis_rangeslider_visible=False,
                    margin=dict(l=0, r=0, t=0, b=0)
                )
                
                st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("---")
            
            # News Sentiment
            st.markdown("### News Sentiment")
            articles = sent.get("articles", [])
            
            if articles:
                for art in articles:
                    sentiment = art.get("sentiment", "neutral")
                    confidence = int(art.get("confidence", 0) * 100)
                    headline = art.get("headline", "N/A")
                    
                    sentiment_emoji = {"positive": "🟢", "negative": "🔴", "neutral": "🟡"}.get(sentiment, "⚪")
                    
                    st.markdown(f"""
                    **{sentiment_emoji} {sentiment.upper()}** ({confidence}%)
                    
                    {headline}
                    """)
            else:
                st.info("No news articles found")
        
        else:
            st.error("⚠️ Unable to fetch analysis. Please check backend connection.")
    
    else:
        st.info("👈 Enter a ticker symbol and click 'Analyze' to get started")

# ═══════════════════════════════════════════════════════════════════════════════
# FOOTER
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("---")
st.markdown("""
<div style="text-align:center;font-size:0.75rem;color:#64748b;margin-top:20px;">
FinBERT NLP · Random Forest ML · YOLOv8 Vision · Kotak Neo API v2 · NSE/BSE
</div>
""", unsafe_allow_html=True)
