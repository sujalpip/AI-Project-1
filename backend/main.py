from fastapi import FastAPI, HTTPException, File, UploadFile, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import math
import logging
import os

from pydantic import BaseModel
from typing import Optional, List, Dict

from data_fetcher import get_stock_data, get_fundamentals
from tech_indicators import add_technical_indicators
from sentiment import get_stock_sentiment
from model import train_predict_model
from decision import generate_recommendation
from nlp_utils import extract_ticker_and_intent, generate_ai_response
from cv_module.analyzer import analyze_chart_pipeline
from kotak_service import kotak
from signal_executor import executor
from trading_engine import scalping_bot, auto_trader
from ai_signals import signal_service
from websocket_feed import market_feed, order_feed

# ─── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("trading.log", encoding="utf-8")
    ]
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI Stock Analysis & Trading API",
    description="FinBERT + ML + Kotak Neo Live Trading",
    version="3.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    signal_service.start_background_refresh()
    logger.info("AI Signal background refresh started")


# ─── Pydantic Models ──────────────────────────────────────────────────────────
class AskRequest(BaseModel):
    query: str

class ExecuteSignalRequest(BaseModel):
    symbol: str
    action: str
    confidence: float
    product: str = "MIS"
    dry_run: bool = True   # default safe: simulate only

class PlaceOrderRequest(BaseModel):
    symbol: str
    transaction_type: str   # "B" or "S"
    quantity: int
    order_type: str = "MKT" # "MKT", "L", "SL"
    price: float = 0.0
    trigger_price: float = 0.0
    product: str = "MIS"

class ModifyOrderRequest(BaseModel):
    order_id: str
    price: Optional[float] = None
    quantity: Optional[int] = None
    trigger_price: Optional[float] = None

class ManualLoginRequest(BaseModel):
    totp: str = ""

class UpdateSecretRequest(BaseModel):
    totp_secret: str

class ScalpingConfigRequest(BaseModel):
    symbol:        str   = "BANKNIFTY"
    option_type:   str   = "CE"
    lots:          int   = 1
    sl_points:     int   = 30
    rr_ratio:      float = 3.0
    dry_run:       bool  = True

class AutoTraderConfigRequest(BaseModel):
    symbols:           List[str] = ["RELIANCE", "TCS", "INFY"]
    scan_interval_s:   int       = 300
    min_confidence:    float     = 68.0
    product:           str       = "MIS"
    dry_run:           bool      = True
    max_trades_day:    int       = 10

class WatchlistRequest(BaseModel):
    symbols: List[str]

class WSSubscribeRequest(BaseModel):
    tokens: List[Dict]   # [{"exchange":"nse_cm","scrip_id":"11536"}]


# ─── Helpers ──────────────────────────────────────────────────────────────────
def clean_dict(d):
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

@app.get("/api/analyze/{ticker}")
async def analyze_stock(ticker: str, period: str = "1y"):
    try:
        # 1. Fetch Data
        df = get_stock_data(ticker, period)
        if df.empty:
            raise HTTPException(status_code=404, detail="No data found for ticker")
            
        fundamentals = get_fundamentals(ticker)
        
        # 2. Technical Indicators
        df = add_technical_indicators(df)
        
        # 3. Predict with ML
        tech_pred = train_predict_model(df)
        
        # 4. Sentiment Analysis
        # Strip .NS or .BO for news search
        search_ticker = ticker.split(".")[0]
        sentiment_data = get_stock_sentiment(search_ticker)
        
        # 5. Decision Engine
        decision = generate_recommendation(tech_pred, sentiment_data)
        
        # Prepare chart data (last 100 days for performance)
        chart_data = df.tail(100).reset_index()
        chart_data['Date'] = chart_data['Date'].astype(str) # Serialize datetime
        
        # We need to fill NaNs in chart data before sending to JSON
        chart_data = chart_data.replace({pd.NA: None, float('nan'): None})
        chart_list = chart_data.to_dict(orient="records")
        chart_list = clean_dict(chart_list)
        
        return clean_dict({
            "ticker": ticker.upper(),
            "fundamentals": fundamentals,
            "technical_prediction": tech_pred,
            "sentiment": sentiment_data,
            "decision": decision,
            "chart_data": chart_list
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
        
@app.get("/api/bot/chat")
async def chat_bot(query: str):
    query_lower = query.lower()
    
    # Basic rule-based bot
    if "buy" in query_lower or "sell" in query_lower or "recommend" in query_lower:
        words = query_lower.split()
        for word in words:
            # Simple heuristic: try to find common Indian tickers
            if word in ["tcs", "reliance", "infy", "sbi", "hdfcbank", "itc", "zomato", "paytm", "tatamotors"]:
                return {"reply": f"To get a detailed recommendation for {word.upper()}, please use the main dashboard on the left. It will run FinBERT sentiment analysis and machine learning models!"}
        return {"reply": "Could you specify which stock you're asking about? E.g., 'Should I buy RELIANCE?'"}
    
    if "sentiment" in query_lower:
        return {"reply": "I can fetch recent news and use FinBERT to analyze sentiment! Just type the stock symbol in the search bar."}
        
    return {"reply": "I am your AI Stock Assistant. I use Technical Indicators, Random Forest ML models, and FinBERT Sentiment Analysis to help you trade in the Indian Market. How can I help?"}

@app.post("/ask")
async def ask_assistant(request: AskRequest):
    try:
        query = request.query
        ticker, intent = extract_ticker_and_intent(query)
        
        if not ticker:
            return {"response": "I couldn't identify a valid Indian stock ticker in your query. Please ask about a specific stock like RELIANCE, TCS, or INFY."}
            
        # 1. Fetch Data
        df = get_stock_data(ticker, "6mo") # slightly shorter timeframe for speed on chat
        if df.empty:
            return {"response": f"I couldn't find market data for {ticker.split('.')[0]}. It might be delisted or the ticker symbol is incorrect."}
            
        fundamentals = get_fundamentals(ticker)
        
        # 2. Technical Indicators
        df = add_technical_indicators(df)
        
        # 3. Predict with ML
        tech_pred = train_predict_model(df)
        
        # 4. Sentiment Analysis
        search_ticker = ticker.split(".")[0]
        sentiment_data = get_stock_sentiment(search_ticker)
        
        # 5. Decision Engine
        decision = generate_recommendation(tech_pred, sentiment_data)
        
        # 6. Generate AI Response
        ai_response = generate_ai_response(ticker, intent, decision, sentiment_data, fundamentals)
        
        return {"response": ai_response}
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="An error occurred while processing your request.")

@app.post("/analyze-chart")
async def analyze_chart(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        result = analyze_chart_pipeline(contents)
        return result
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════════════
# KOTAK NEO TRADING ROUTES
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/api/kotak/status")
async def kotak_status():
    """Check Kotak service availability and login status."""
    return {
        "available": kotak.is_available(),
        "logged_in": kotak.is_logged_in,
        "message": (
            "Ready to trade" if kotak.is_logged_in
            else "Not logged in — call /api/kotak/login"
            if kotak.is_available()
            else "Kotak not configured — check .env file"
        )
    }


@app.post("/api/kotak/login")
async def kotak_login(req: ManualLoginRequest = ManualLoginRequest()):
    """
    Authenticate with Kotak Neo via TOTP.
    On success, automatically connects HSM market feed and HSI order feed WebSockets.
    """
    if not kotak.is_available():
        raise HTTPException(status_code=503,
            detail="Kotak not configured. Add credentials to backend/.env")
    try:
        result = kotak.login(manual_totp=req.totp)

        # Auto-connect WebSockets on successful login
        if result.get("status") == "success":
            dc = kotak.trade_sid[:3] if kotak.trade_sid else ""
            try:
                import threading
                def _connect_ws():
                    market_feed.connect(kotak.trade_token, kotak.trade_sid, dc)
                    order_feed.connect(kotak.trade_token, kotak.trade_sid, dc)
                threading.Thread(target=_connect_ws, daemon=True).start()
                logger.info("WebSocket auto-connect initiated")
            except Exception as e:
                logger.warning(f"WebSocket auto-connect failed (non-critical): {e}")

        return result
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(status_code=401, detail=str(e))


@app.post("/api/kotak/logout")
async def kotak_logout():
    """Terminate the Kotak session."""
    try:
        return kotak.logout()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/kotak/update-secret")
async def update_totp_secret(req: UpdateSecretRequest):
    """
    Update KOTAK_TOTP_SECRET in .env with a new Base32 secret.
    Use this when the saved secret doesn't match Google Authenticator.
    """
    import base64, re
    from pathlib import Path

    raw = req.totp_secret.strip().replace(" ", "").upper()

    # Validate Base32
    if not re.match(r'^[A-Z2-7]+=*$', raw + "=" * ((8 - len(raw) % 8) % 8)):
        raise HTTPException(status_code=400,
            detail="Invalid Base32 secret. Must contain only A-Z and 2-7.")

    try:
        padded = raw + "=" * ((8 - len(raw) % 8) % 8)
        base64.b32decode(padded)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid Base32 encoding.")

    # Update .env file
    env_path = Path(__file__).parent / ".env"
    if not env_path.exists():
        raise HTTPException(status_code=500, detail=".env file not found.")

    content = env_path.read_bytes()
    text    = content.decode("utf-8")

    old_secret = os.getenv("KOTAK_TOTP_SECRET", "").strip()

    if f"KOTAK_TOTP_SECRET={old_secret}" in text:
        text = text.replace(f"KOTAK_TOTP_SECRET={old_secret}",
                            f"KOTAK_TOTP_SECRET={raw}")
    elif "KOTAK_TOTP_SECRET=" in text:
        import re as _re
        text = _re.sub(r"KOTAK_TOTP_SECRET=.*",
                       f"KOTAK_TOTP_SECRET={raw}", text)
    else:
        text += f"\nKOTAK_TOTP_SECRET={raw}\n"

    env_path.write_text(text, encoding="utf-8")

    # Reload env in current process
    os.environ["KOTAK_TOTP_SECRET"] = raw

    # Verify it generates a valid TOTP
    import pyotp
    test_totp = pyotp.TOTP(raw).now()

    logger.info(f"TOTP secret updated. Test TOTP: {test_totp}")
    return {
        "status":     "updated",
        "message":    f"Secret updated. Test TOTP generated: {test_totp}. Now click Login.",
        "test_totp":  test_totp,
        "new_secret": raw,
    }


# ── Market Data ───────────────────────────────────────────────────────────────

@app.get("/api/kotak/ltp/{symbol}")
async def get_ltp(symbol: str, exchange: str = "nse_cm"):
    """Get last traded price for a symbol."""
    if not kotak.is_logged_in:
        raise HTTPException(status_code=401, detail="Not logged in to Kotak")
    try:
        ltp = kotak.get_ltp(symbol.upper(), exchange)
        return {"symbol": symbol.upper(), "ltp": ltp, "exchange": exchange}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/kotak/quote/{symbol}")
async def get_quote(symbol: str, exchange: str = "nse_cm", quote_type: str = "all"):
    """Get detailed quote (ohlc, depth, ltp, 52w, oi, circuit_limits)."""
    if not kotak.is_logged_in:
        raise HTTPException(status_code=401, detail="Not logged in to Kotak")
    try:
        return kotak.get_quote(symbol.upper(), exchange, quote_type)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── Portfolio ─────────────────────────────────────────────────────────────────

@app.get("/api/kotak/positions")
async def get_positions():
    """Get all open positions."""
    if not kotak.is_logged_in:
        raise HTTPException(status_code=401, detail="Not logged in to Kotak")
    try:
        return {"positions": kotak.get_positions()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/kotak/holdings")
async def get_holdings():
    """Get portfolio holdings (long-term demat)."""
    if not kotak.is_logged_in:
        raise HTTPException(status_code=401, detail="Not logged in to Kotak")
    try:
        return {"holdings": kotak.get_holdings()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/kotak/orders")
async def get_orders():
    """
    GET /quick/user/orders — today's full order book.
    Fields: nOrdNo, ordSt, trdSym, qty, prc, avgPrc,
            trnsTp, prcTp, vldt, rejRsn, exSeg, ordDtTm
    """
    if not kotak.is_logged_in:
        raise HTTPException(status_code=401, detail="Not logged in to Kotak")
    try:
        return {"orders": kotak.get_order_book()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/kotak/orders/{order_id}/history")
async def get_order_history(order_id: str):
    """
    POST /quick/user/order/history — full lifecycle of one order.
    Pass nOrdNo as path param.
    Fields: nOrdNo, ordSt, flDtTm, rejRsn, qty, prc, avgPrc, prod
    """
    if not kotak.is_logged_in:
        raise HTTPException(status_code=401, detail="Not logged in to Kotak")
    try:
        return {"history": kotak.get_order_history(order_id)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/kotak/trades")
async def get_trades():
    """
    GET /quick/user/trades — executed trades for today.
    Fields: nOrdNo, trdSym, qty, avgPrc, fldQty,
            flDt, exTm, prcTp, prod, trnsTp, exOrdId
    """
    if not kotak.is_logged_in:
        raise HTTPException(status_code=401, detail="Not logged in to Kotak")
    try:
        return {"trades": kotak.get_trade_book()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/kotak/margin")
async def get_margin(segment: str = "ALL", exchange: str = "ALL", product: str = "ALL"):
    """
    Get available trading margin.
    POST /quick/user/limits — returns Net, CollateralValue, MarginUsed.
    """
    if not kotak.is_logged_in:
        raise HTTPException(status_code=401, detail="Not logged in to Kotak")
    try:
        margin = kotak.get_available_margin(segment, exchange, product)
        return {"available_margin": margin, "segment": segment, "exchange": exchange}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/kotak/limits/full")
async def get_full_limits(segment: str = "ALL", exchange: str = "ALL", product: str = "ALL"):
    """
    Full limits response — Net, CollateralValue, MarginUsed,
    UnrealizedMtomPrsnt, RealizedMtomPrsnt, BoardLotLimit, etc.
    """
    if not kotak.is_logged_in:
        raise HTTPException(status_code=401, detail="Not logged in to Kotak")
    try:
        return kotak.get_full_limits(segment, exchange, product)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/kotak/margin/check")
async def check_margin(
    symbol: str,
    exchange: str = "nse_cm",
    price: float = 0.0,
    order_type: str = "MKT",
    product: str = "MIS",
    quantity: int = 1,
    transaction_type: str = "B"
):
    """
    Pre-trade margin check via POST /quick/user/check-margin.
    Returns: avlCash, avlMrgn, ordMrgn, reqdMrgn, insufFund, rmsVldtd.
    rmsVldtd = 'OK' means you have enough margin.
    """
    if not kotak.is_logged_in:
        raise HTTPException(status_code=401, detail="Not logged in to Kotak")
    try:
        result = kotak.check_margin(
            symbol=symbol.upper(), exchange=exchange,
            price=price, order_type=order_type,
            product=product, quantity=quantity,
            transaction_type=transaction_type
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/kotak/margin/raw")
async def get_margin_raw():
    """Returns the raw limits() API response for debugging."""
    if not kotak.is_logged_in:
        raise HTTPException(status_code=401, detail="Not logged in to Kotak")
    try:
        return {"raw_response": kotak.get_raw_limits()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/kotak/scrip/search")
async def search_scrip(symbol: str, exchange: str = "nse_cm"):
    """
    Search for a symbol in the scrip master.
    Returns instrument_token, trading_symbol, lot_size.
    """
    if not kotak.is_available():
        raise HTTPException(status_code=503, detail="Kotak not configured")
    try:
        result = kotak.get_instrument_token(symbol.upper(), exchange)
        return result
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/api/kotak/quotes")
async def get_multi_quotes(symbols: str, exchange: str = "nse_cm",
                           quote_type: str = "ltp"):
    """
    Get quotes for multiple symbols (comma-separated).
    Uses official Quotes API: /script-details/1.0/quotes/neosymbol/{queries}/{filter}
    quote_type: all, ltp, ohlc, depth, 52W, scrip_details, circuit_limits, oi
    """
    if not kotak.is_logged_in:
        raise HTTPException(status_code=401, detail="Not logged in to Kotak")
    try:
        sym_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
        results  = {}
        for sym in sym_list:
            try:
                results[sym] = kotak.get_quote(sym, exchange, quote_type)
            except Exception as e:
                results[sym] = {"error": str(e)}
        return {"quotes": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Order Management ──────────────────────────────────────────────────────────

@app.post("/api/kotak/order/place")
async def place_order(req: PlaceOrderRequest):
    """
    Place an order manually.
    transaction_type: 'B' (Buy) or 'S' (Sell)
    order_type: 'MKT', 'L', 'SL'
    product: 'MIS' (intraday), 'CNC' (delivery), 'NRML'
    """
    if not kotak.is_logged_in:
        raise HTTPException(status_code=401, detail="Not logged in to Kotak")
    try:
        if req.order_type == "MKT":
            resp = kotak.place_market_order(
                req.symbol.upper(), req.transaction_type,
                req.quantity, req.product
            )
        elif req.order_type == "L":
            resp = kotak.place_limit_order(
                req.symbol.upper(), req.transaction_type,
                req.quantity, req.price, req.product
            )
        elif req.order_type == "SL":
            resp = kotak.place_sl_order(
                req.symbol.upper(), req.transaction_type,
                req.quantity, req.price, req.trigger_price, req.product
            )
        else:
            raise HTTPException(status_code=400, detail=f"Unknown order_type: {req.order_type}")

        return {"status": "success", "order": resp}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.put("/api/kotak/order/modify")
async def modify_order(req: ModifyOrderRequest):
    """Modify an existing order."""
    if not kotak.is_logged_in:
        raise HTTPException(status_code=401, detail="Not logged in to Kotak")
    try:
        resp = kotak.modify_order(
            req.order_id, req.price, req.quantity, req.trigger_price
        )
        return {"status": "success", "order": resp}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/api/kotak/order/{order_id}")
async def cancel_order(order_id: str):
    """Cancel an order (with pre-check)."""
    if not kotak.is_logged_in:
        raise HTTPException(status_code=401, detail="Not logged in to Kotak")
    try:
        resp = kotak.cancel_order(order_id, verify=True)
        return {"status": "success", "response": resp}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── AI Signal Execution ───────────────────────────────────────────────────────

@app.post("/api/kotak/execute")
async def execute_ai_signal(req: ExecuteSignalRequest):
    """
    Execute an AI trading signal via Kotak Neo.
    
    By default dry_run=True (simulate only).
    Set dry_run=False to place real orders.
    
    The executor will:
      1. Check risk limits
      2. Get current LTP
      3. Calculate position size (1% risk rule)
      4. Place market order
      5. Place stop-loss order (1.5% from entry)
    """
    try:
        result = executor.execute_signal(
            symbol=req.symbol.upper(),
            action=req.action,
            confidence=req.confidence,
            product=req.product,
            dry_run=req.dry_run
        )
        return result
    except Exception as e:
        logger.error(f"Signal execution error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/kotak/risk/status")
async def risk_status():
    """Get current risk manager status (positions, daily P&L, limits)."""
    return executor.get_risk_status()


@app.get("/api/kotak/execution/log")
async def execution_log():
    """Get full execution history for this session."""
    return {"log": executor.get_execution_log()}


# ── Analyse + Auto-Execute (Full Pipeline) ───────────────────────────────────

@app.get("/api/analyze-and-trade/{ticker}")
async def analyze_and_trade(
    ticker: str,
    period: str = "1y",
    auto_execute: bool = False,
    dry_run: bool = True,
    product: str = "MIS"
):
    """
    Full pipeline: Analyse stock → Generate AI signal → Optionally execute order.
    
    auto_execute=False  → analysis only (default, safe)
    auto_execute=True   → execute signal via Kotak
    dry_run=True        → simulate order (default, safe)
    dry_run=False       → place REAL order (use with caution!)
    """
    try:
        # 1. Fetch & analyse
        df = get_stock_data(ticker, period)
        if df.empty:
            raise HTTPException(status_code=404, detail="No data found for ticker")

        fundamentals = get_fundamentals(ticker)
        df = add_technical_indicators(df)
        tech_pred = train_predict_model(df)
        search_ticker = ticker.split(".")[0]
        sentiment_data = get_stock_sentiment(search_ticker)
        decision = generate_recommendation(tech_pred, sentiment_data)

        # 2. Chart data
        chart_data = df.tail(100).reset_index()
        chart_data['Date'] = chart_data['Date'].astype(str)
        chart_data = chart_data.replace({pd.NA: None, float('nan'): None})
        chart_list = clean_dict(chart_data.to_dict(orient="records"))

        result = clean_dict({
            "ticker": ticker.upper(),
            "fundamentals": fundamentals,
            "technical_prediction": tech_pred,
            "sentiment": sentiment_data,
            "decision": decision,
            "chart_data": chart_list,
            "execution": None
        })

        # 3. Execute if requested
        if auto_execute:
            execution = executor.execute_signal(
                symbol=search_ticker,
                action=decision["action"],
                confidence=decision["confidence"],
                product=product,
                dry_run=dry_run
            )
            result["execution"] = execution
            logger.info(f"Auto-execute [{ticker}]: {execution['status']} — {execution['message']}")

        return result

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════════════
# AI SIGNALS
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/api/signals/all")
async def get_all_signals():
    """Get cached AI signals for entire watchlist."""
    return {"signals": signal_service.get_all_signals()}

@app.get("/api/signals/{symbol}")
async def get_signal(symbol: str, refresh: bool = False):
    """Get AI signal for one symbol. refresh=true forces recompute."""
    return signal_service.get_signal(symbol.upper(), force_refresh=refresh)

@app.post("/api/signals/watchlist")
async def set_watchlist(req: WatchlistRequest):
    """Update the signal watchlist."""
    signal_service.set_watchlist(req.symbols)
    return {"status": "updated", "watchlist": signal_service.watchlist}

@app.get("/api/signals/watchlist")
async def get_watchlist():
    return {"watchlist": signal_service.watchlist}


# ═══════════════════════════════════════════════════════════════════════════════
# SCALPING BOT
# ═══════════════════════════════════════════════════════════════════════════════

@app.post("/api/scalping/configure")
async def configure_scalping(req: ScalpingConfigRequest):
    scalping_bot.configure(
        symbol=req.symbol, option_type=req.option_type,
        lots=req.lots, sl_points=req.sl_points,
        rr_ratio=req.rr_ratio, dry_run=req.dry_run,
        target_points=int(req.sl_points * req.rr_ratio)
    )
    return {"status": "configured", "config": scalping_bot.config}

@app.post("/api/scalping/start")
async def start_scalping():
    if not kotak.is_logged_in:
        raise HTTPException(status_code=401, detail="Login to Kotak first")
    return scalping_bot.start()

@app.post("/api/scalping/stop")
async def stop_scalping():
    return scalping_bot.stop()

@app.get("/api/scalping/status")
async def scalping_status():
    return scalping_bot.get_status()

@app.get("/api/scalping/log")
async def scalping_log():
    return {"log": scalping_bot.get_log()}


# ═══════════════════════════════════════════════════════════════════════════════
# AUTO TRADER
# ═══════════════════════════════════════════════════════════════════════════════

@app.post("/api/autotrader/configure")
async def configure_autotrader(req: AutoTraderConfigRequest):
    auto_trader.configure(
        symbols=req.symbols, scan_interval_s=req.scan_interval_s,
        min_confidence=req.min_confidence, product=req.product,
        dry_run=req.dry_run, max_trades_day=req.max_trades_day
    )
    return {"status": "configured", "config": auto_trader.config}

@app.post("/api/autotrader/start")
async def start_autotrader():
    if not kotak.is_logged_in:
        raise HTTPException(status_code=401, detail="Login to Kotak first")
    return auto_trader.start()

@app.post("/api/autotrader/stop")
async def stop_autotrader():
    return auto_trader.stop()

@app.get("/api/autotrader/status")
async def autotrader_status():
    return auto_trader.get_status()

@app.get("/api/autotrader/log")
async def autotrader_log(n: int = 50):
    return {"log": auto_trader.get_log(n)}


# ═══════════════════════════════════════════════════════════════════════════════
# WEBSOCKET FEED ROUTES
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/api/ws/status")
async def ws_status():
    """Status of HSM (market feed) and HSI (order feed) WebSocket connections."""
    return {
        "market_feed": market_feed.get_status(),
        "order_feed":  order_feed.get_status(),
    }


@app.post("/api/ws/connect")
async def ws_connect():
    """
    Manually connect HSM + HSI WebSockets.
    Uses trade_token and trade_sid from current Kotak session.
    dataCenter is derived from trade_sid prefix.
    """
    if not kotak.is_logged_in:
        raise HTTPException(status_code=401, detail="Login to Kotak first")
    try:
        dc = kotak.trade_sid[:3] if kotak.trade_sid else ""
        import threading
        def _connect():
            mf = market_feed.connect(kotak.trade_token, kotak.trade_sid, dc)
            of = order_feed.connect(kotak.trade_token, kotak.trade_sid, dc)
            logger.info(f"WS connect: market={mf} order={of}")
        threading.Thread(target=_connect, daemon=True).start()
        return {"status": "connecting", "data_center": dc}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/ws/disconnect")
async def ws_disconnect():
    """Disconnect both WebSocket feeds."""
    market_feed.disconnect()
    order_feed.disconnect()
    return {"status": "disconnected"}


@app.post("/api/ws/subscribe")
async def ws_subscribe(req: WSSubscribeRequest):
    """
    Subscribe to market feed for given instruments.
    tokens: [{"exchange":"nse_cm","scrip_id":"11536","feed_type":1}]
    feed_type: 1=scrip, 2=index, 3=depth
    Max 200 scrips total.
    """
    if not market_feed.connected:
        raise HTTPException(status_code=400,
            detail="Market feed not connected. Call /api/ws/connect first.")
    count = market_feed.subscribe_many(req.tokens)
    return {
        "subscribed": count,
        "total":      len(market_feed.subscribed),
        "max":        200,
    }


@app.post("/api/ws/subscribe/symbol")
async def ws_subscribe_symbol(symbol: str, exchange: str = "nse_cm"):
    """
    Subscribe to a symbol by name (auto-looks up scrip_id from master).
    """
    if not kotak.is_logged_in:
        raise HTTPException(status_code=401, detail="Not logged in")
    try:
        inst = kotak.get_instrument_token(symbol.upper(), exchange)
        scrip_id = inst.get("instrument_token", "")
        if not scrip_id:
            raise HTTPException(status_code=404, detail=f"Token not found for {symbol}")
        ok = market_feed.subscribe(exchange, scrip_id, feed_type=1)
        return {
            "symbol":   symbol.upper(),
            "scrip_id": scrip_id,
            "exchange": exchange,
            "subscribed": ok,
            "format":   f"{exchange}|{scrip_id}&1",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/ws/ticks")
async def ws_get_ticks():
    """Get all latest ticks received from market feed."""
    return {"ticks": market_feed.get_all_ticks()}


@app.get("/api/ws/tick/{scrip_id}")
async def ws_get_tick(scrip_id: str):
    """Get latest tick for a specific scrip_id."""
    tick = market_feed.get_tick(scrip_id)
    if not tick:
        return {"scrip_id": scrip_id, "tick": None, "message": "No data yet"}
    return {"scrip_id": scrip_id, "tick": tick}


@app.get("/api/ws/orders/feed")
async def ws_order_feed(n: int = 50):
    """Get latest order updates from HSI order feed."""
    return {
        "updates": order_feed.get_updates(n),
        "status":  order_feed.get_status(),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
