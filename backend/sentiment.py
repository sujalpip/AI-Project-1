import feedparser
from transformers import pipeline
import re
import warnings

warnings.filterwarnings("ignore")

# Initialize FinBERT pipeline
# Using ProsusAI/finbert which is specifically trained for financial text
try:
    sentiment_pipeline = pipeline("text-classification", model="ProsusAI/finbert")
except Exception as e:
    sentiment_pipeline = None
    print(f"Failed to load FinBERT: {e}")

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
    if not sentiment_pipeline or not news_items:
        return {"average_sentiment": "Neutral", "score": 0, "articles": []}
    
    results = sentiment_pipeline(news_items)
    
    analyzed_articles = []
    score_map = {"positive": 1, "neutral": 0, "negative": -1}
    total_score = 0
    
    for news, res in zip(news_items, results):
        label = res['label']
        total_score += score_map.get(label, 0)
        analyzed_articles.append({"headline": news, "sentiment": label, "confidence": res['score']})
        
    avg = total_score / len(news_items)
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
