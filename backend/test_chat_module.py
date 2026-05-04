"""
Test script to diagnose chat AI module issues
"""

import sys

print("=" * 80)
print("TESTING CHAT AI MODULE")
print("=" * 80)

# Test 1: Import modules
print("\n[TEST 1] Importing modules...")
try:
    from nlp_utils import extract_ticker_and_intent, generate_ai_response
    print("✅ nlp_utils imported successfully")
except Exception as e:
    print(f"❌ Error importing nlp_utils: {e}")
    sys.exit(1)

try:
    from sentiment import get_stock_sentiment
    print("✅ sentiment module imported successfully")
except Exception as e:
    print(f"❌ Error importing sentiment: {e}")
    sys.exit(1)

try:
    from data_fetcher import get_stock_data, get_fundamentals
    print("✅ data_fetcher imported successfully")
except Exception as e:
    print(f"❌ Error importing data_fetcher: {e}")
    sys.exit(1)

try:
    from tech_indicators import add_technical_indicators
    print("✅ tech_indicators imported successfully")
except Exception as e:
    print(f"❌ Error importing tech_indicators: {e}")
    sys.exit(1)

try:
    from model import train_predict_model
    print("✅ model imported successfully")
except Exception as e:
    print(f"❌ Error importing model: {e}")
    sys.exit(1)

try:
    from decision import generate_recommendation
    print("✅ decision imported successfully")
except Exception as e:
    print(f"❌ Error importing decision: {e}")
    sys.exit(1)

# Test 2: Extract ticker and intent
print("\n[TEST 2] Testing extract_ticker_and_intent...")
test_queries = [
    "Should I buy RELIANCE stock?",
    "What about TCS?",
    "Is INFY a good buy?",
    "Sell HDFC Bank?"
]

for query in test_queries:
    try:
        ticker, intent = extract_ticker_and_intent(query)
        print(f"✅ Query: '{query}'")
        print(f"   → Ticker: {ticker}, Intent: {intent}")
    except Exception as e:
        print(f"❌ Error processing '{query}': {e}")

# Test 3: Test sentiment analysis
print("\n[TEST 3] Testing sentiment analysis...")
try:
    print("Fetching sentiment for RELIANCE...")
    sentiment_data = get_stock_sentiment("RELIANCE")
    print(f"✅ Sentiment data retrieved:")
    print(f"   Average Sentiment: {sentiment_data.get('average_sentiment')}")
    print(f"   Score: {sentiment_data.get('score')}")
    print(f"   Articles: {len(sentiment_data.get('articles', []))} found")
except Exception as e:
    print(f"❌ Error in sentiment analysis: {e}")
    import traceback
    traceback.print_exc()

# Test 4: Test full pipeline
print("\n[TEST 4] Testing full chat pipeline...")
try:
    query = "Should I buy RELIANCE stock?"
    print(f"Query: {query}")
    
    # Extract ticker and intent
    ticker, intent = extract_ticker_and_intent(query)
    print(f"✅ Extracted - Ticker: {ticker}, Intent: {intent}")
    
    if not ticker:
        print("❌ No ticker extracted")
    else:
        # Fetch data
        print(f"Fetching data for {ticker}...")
        df = get_stock_data(ticker, "6mo")
        if df.empty:
            print(f"❌ No data found for {ticker}")
        else:
            print(f"✅ Data fetched: {len(df)} rows")
            
            # Get fundamentals
            fundamentals = get_fundamentals(ticker)
            print(f"✅ Fundamentals retrieved")
            
            # Add technical indicators
            df = add_technical_indicators(df)
            print(f"✅ Technical indicators added")
            
            # Train model
            tech_pred = train_predict_model(df)
            print(f"✅ ML prediction: {tech_pred}")
            
            # Get sentiment
            search_ticker = ticker.split(".")[0]
            sentiment_data = get_stock_sentiment(search_ticker)
            print(f"✅ Sentiment: {sentiment_data.get('average_sentiment')}")
            
            # Generate recommendation
            decision = generate_recommendation(tech_pred, sentiment_data)
            print(f"✅ Decision: {decision.get('action')}")
            
            # Generate AI response
            ai_response = generate_ai_response(ticker, intent, decision, sentiment_data, fundamentals)
            print(f"✅ AI Response generated (length: {len(ai_response)} chars)")
            print(f"\nAI Response:\n{ai_response[:300]}...")

except Exception as e:
    print(f"❌ Error in full pipeline: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("TEST COMPLETE")
print("=" * 80)
