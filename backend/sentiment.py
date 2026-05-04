import feedparser
import re
import warnings
import os

warnings.filterwarnings("ignore")

# Initialize FinBERT pipeline
# Using ProsusAI/finbert which is specifically trained for financial text
sentiment_pipeline = None

def _load_sentiment_pipeline():
    """Lazy load the sentiment pipeline to avoid blocking on import"""
    global sentiment_pipeline
    if sentiment_pipeline is not None:
        return sentiment_pipeline
    
    try:
        from transformers import pipeline
        # Set cache directory to avoid permission issues
        cache_dir = os.path.join(os.path.expanduser("~"), ".cache", "huggingface", "hub")
        os.makedirs(cache_dir, exist_ok=True)
        
        sentiment_pipeline = pipeline(
            "text-classification", 
            model="ProsusAI/finbert",
            cache_dir=cache_dir,
            device=-1  # Use CPU
        )
        return sentiment_pipeline
    except Exception as e:
        print(f"Failed to load FinBERT: {e}")
        return None

def clean_html(raw_html):
    cleanr = re.compile('<.*?>')
    cleantext = re.sub(cleanr, '', raw_html)
    return cleantext

def fetch_news(query: str, limit: int = 5):
    # Google News RSS for Indian market context
    query_encoded = query.replace(" ", "+")
    url = f"https://news.google.com/rss/search?q={query_encoded}+stock+india&hl=en-IN&gl=IN&ceid=IN:en"
    feed = feedparser.parse(url)
    
    news_items = []
    for entry in feed.entries[:limit]:
        title = entry.title
        news_items.append(title)
        
    return news_items

def analyze_sentiment(news_items: list):
    pipeline = _load_sentiment_pipeline()
    if not pipeline or not news_items:
        return {"average_sentiment": "Neutral", "score": 0, "articles": []}
    
    results = pipeline(news_items)
    
    analyzed_articles = []
    score_map = {"positive": 1, "neutral": 0, "negative": -1}
    total_score = 0
    
    for news, res in zip(news_items, results):
        label = res['label'].lower()
        total_score += score_map.get(label, 0)
        analyzed_articles.append({"headline": news, "sentiment": label, "confidence": res['score']})
        
    avg = total_score / len(news_items) if news_items else 0
    if avg > 0.33:
        overall_sentiment = "Positive"
    elif avg < -0.33:
        overall_sentiment = "Negative"
    else:
        overall_sentiment = "Neutral"
        
    return {
        "average_sentiment": overall_sentiment,
        "score": avg,
        "articles": analyzed_articles
    }

def get_stock_sentiment(ticker: str):
    news = fetch_news(ticker)
    return analyze_sentiment(news)
