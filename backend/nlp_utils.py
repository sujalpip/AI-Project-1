import re

# Simple dictionary mapping common names to NSE tickers
COMMON_TICKERS = {
    "RELIANCE": "RELIANCE.NS",
    "TCS": "TCS.NS",
    "INFY": "INFY.NS",
    "INFOSYS": "INFY.NS",
    "HDFC": "HDFCBANK.NS",
    "HDFCBANK": "HDFCBANK.NS",
    "ICICI": "ICICIBANK.NS",
    "ICICIBANK": "ICICIBANK.NS",
    "SBI": "SBIN.NS",
    "SBIN": "SBIN.NS",
    "ITC": "ITC.NS",
    "ZOMATO": "ZOMATO.NS",
    "PAYTM": "PAYTM.NS",
    "TATA MOTORS": "TATAMOTORS.NS",
    "TATAMOTORS": "TATAMOTORS.NS",
    "WIPRO": "WIPRO.NS",
    "AIRTEL": "BHARTIARTL.NS",
    "BHARTIARTL": "BHARTIARTL.NS",
}

def extract_ticker_and_intent(query: str):
    """
    Extracts the stock ticker and intent from a natural language query.
    Returns a tuple: (ticker_symbol, intent)
    """
    query_upper = query.upper()
    
    # 1. Extract Ticker
    extracted_ticker = None
    # Check against known tickers first
    for name, symbol in COMMON_TICKERS.items():
        if name in query_upper:
            extracted_ticker = symbol
            break
            
    # If not found in common, look for any uppercase word that looks like a ticker
    # or just try to extract the last word if it's uppercase.
    if not extracted_ticker:
        # Match words like RELIANCE, INFY, etc.
        words = re.findall(r'\b[A-Z]{3,10}\b', query_upper)
        # Filter out common intent words
        ignore_words = {"BUY", "SELL", "HOLD", "SHOULD", "STOCK", "SHARE"}
        for word in words:
            if word not in ignore_words:
                extracted_ticker = f"{word}.NS" # Default to NSE
                break
                
    # 2. Extract Intent
    intent = "analysis"
    if "BUY" in query_upper:
        intent = "buy"
    elif "SELL" in query_upper:
        intent = "sell"
    elif "HOLD" in query_upper:
        intent = "hold"
        
    return extracted_ticker, intent

def generate_ai_response(ticker: str, intent: str, decision: dict, sentiment_data: dict, fundamentals: dict):
    """
    Programmatically generates a human-like response based on the backend data.
    """
    ticker_clean = ticker.split('.')[0]
    action = decision.get("action", "Hold")
    confidence = decision.get("confidence", 50)
    sentiment = sentiment_data.get("average_sentiment", "Neutral")
    current_price = fundamentals.get("Current Price", "N/A")
    
    # Constructing the response
    response_parts = []
    
    # Introduction / Direct Answer
    if intent == "buy":
        if "Buy" in action:
            response_parts.append(f"**Yes**, it looks like a good time to consider buying **{ticker_clean}**.")
        elif "Sell" in action:
            response_parts.append(f"**Caution**: Our models suggest it might **not** be the best time to buy **{ticker_clean}** right now.")
        else:
            response_parts.append(f"**Hold on**: For **{ticker_clean}**, it might be better to wait for a clearer signal.")
    elif intent == "sell":
        if "Sell" in action:
            response_parts.append(f"**Yes**, it might be a good time to consider selling **{ticker_clean}** to lock in profits or prevent losses.")
        elif "Buy" in action:
            response_parts.append(f"**Reconsider**: Our models indicate **{ticker_clean}** has strong upward momentum right now. Selling might be premature.")
        else:
            response_parts.append(f"**Hold**: The signals for **{ticker_clean}** are currently neutral. You might want to hold your position.")
    else:
        response_parts.append(f"Here is the analysis for **{ticker_clean}**:")

    # Detailed Explanation
    response_parts.append(f"\n### 📊 Analysis Breakdown")
    response_parts.append(f"- **Current Price:** ₹{current_price}")
    response_parts.append(f"- **AI Recommendation:** **{action}** (Confidence: {confidence}%)")
    response_parts.append(f"- **Market Sentiment (FinBERT):** **{sentiment}**")
    
    # Textual reasoning based on data
    reasoning = "\n**Reasoning:**\n"
    if "Buy" in action:
        reasoning += f"The technical indicators for {ticker_clean} show bullish momentum. "
    elif "Sell" in action:
        reasoning += f"The technical indicators for {ticker_clean} show bearish trends. "
    else:
        reasoning += f"The technical indicators for {ticker_clean} are currently mixed or neutral. "
        
    if sentiment == "Positive":
        reasoning += "This is supported by positive news sentiment in the market."
    elif sentiment == "Negative":
        reasoning += "Additionally, recent news sentiment is negative, which could create downward pressure."
    else:
        reasoning += "Recent news sentiment is neutral, having no major impact."
        
    response_parts.append(reasoning)
    
    # Risk Disclaimer
    response_parts.append("\n---\n*Disclaimer: This is an AI-generated analysis based on technical indicators and news sentiment. It is not financial advice. Please do your own research or consult a financial advisor before trading in the stock market.*")
    
    return "\n".join(response_parts)
