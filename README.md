# AI-Powered Indian Stock Prediction & Sentiment Analysis System

This is a full-stack intelligent system that analyzes Indian stock market data using sentiment analysis, technical indicators, and fundamental signals to generate Buy/Sell/Hold recommendations.

## Features
- **Data Fetching:** Real-time and historical stock data from NSE/BSE using `yfinance`.
- **Sentiment Analysis Engine:** Uses **FinBERT** to classify financial news (fetched via Google News RSS) into Positive/Negative/Neutral.
- **Technical Analysis:** Calculates SMA, EMA, RSI, MACD, and Bollinger Bands using the `ta` library.
- **Fundamental Analysis:** Extracts P/E Ratio, EPS, Market Cap, etc.
- **Prediction Model:** A Random Forest classifier trained on technical indicators to predict short-term stock movement.
- **Decision Engine:** Combines Sentiment, Technicals, and ML predictions to output a final Buy/Sell/Hold action with confidence score.
- **Visualization Dashboard:** A clean Streamlit UI with interactive Plotly candlestick charts, indicator overlays, and a sentiment recommendation panel.
- **AI Bot Assistant:** A rule-based assistant to guide the user.

## Tech Stack
- **Backend:** Python (FastAPI), Scikit-learn, Transformers (FinBERT), yfinance, pandas, ta.
- **Frontend:** Streamlit, Plotly.

## Project Structure
```
projectml11/
├── backend/
│   ├── main.py              # FastAPI app
│   ├── data_fetcher.py      # yfinance data fetching
│   ├── sentiment.py         # FinBERT and news fetching
│   ├── tech_indicators.py   # Technical indicators calculation
│   ├── model.py             # Random Forest prediction model
│   ├── decision.py          # Decision engine combining signals
│   └── requirements.txt
├── frontend/
│   ├── app.py               # Streamlit dashboard
│   └── requirements.txt
├── run.bat                  # Windows startup script
└── README.md
```

## Setup Instructions

### Prerequisites
- Python 3.8+
- Git (optional)

### One-Click Start (Windows)
Simply double-click the `run.bat` file. It will:
1. Install backend dependencies.
2. Install frontend dependencies.
3. Start the FastAPI backend on port 8000.
4. Start the Streamlit frontend on port 8501.

### Manual Setup
If you prefer to start them manually or are on Mac/Linux:

**1. Backend:**
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

**2. Frontend:**
```bash
cd frontend
pip install -r requirements.txt
streamlit run app.py
```

## Important Notes
- The first time you analyze a stock, the backend will download the `ProsusAI/finbert` model (around 400MB) from HuggingFace. This may take a minute depending on your internet connection.
- Ensure your tickers are valid NSE/BSE symbols (e.g., `RELIANCE`, `TCS`, `INFY`, `TATAMOTORS`). The system automatically appends `.NS` for Indian market symbols.
