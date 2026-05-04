import yfinance as yf
import pandas as pd

def get_stock_data(ticker: str, period: str = "1y", interval: str = "1d"):
    if not ticker.endswith(".NS") and not ticker.endswith(".BO"):
        ticker += ".NS"  # Default to NSE
    stock = yf.Ticker(ticker)
    hist = stock.history(period=period, interval=interval)
    return hist

def get_fundamentals(ticker: str):
    if not ticker.endswith(".NS") and not ticker.endswith(".BO"):
        ticker += ".NS"
    stock = yf.Ticker(ticker)
    info = stock.info
    return {
        "P/E Ratio": info.get("trailingPE", "N/A"),
        "EPS": info.get("trailingEps", "N/A"),
        "Market Cap": info.get("marketCap", "N/A"),
        "52 Week High": info.get("fiftyTwoWeekHigh", "N/A"),
        "52 Week Low": info.get("fiftyTwoWeekLow", "N/A"),
        "Current Price": info.get("currentPrice", "N/A")
    }
