import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler

def train_predict_model(df: pd.DataFrame):
    if len(df) < 50:
        return {"prediction": "Hold", "confidence": 50.0, "error": "Not enough data"}
        
    # Feature Engineering
    df = df.copy()
    df['Target'] = (df['Close'].shift(-1) > df['Close']).astype(int) # 1 if next day close is higher
    
    features = ['SMA_20', 'EMA_20', 'RSI', 'MACD', 'BB_High', 'BB_Low']
    
    # Drop NaNs
    df_clean = df.dropna(subset=features + ['Target'])
    
    if len(df_clean) < 20:
        return {"prediction": "Hold", "confidence": 50.0, "error": "Not enough data after cleaning"}
        
    X = df_clean[features]
    y = df_clean['Target']
    
    # Scale
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # Train
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_scaled[:-1], y.iloc[:-1]) # Train on all except the last row
    
    # Predict the last row (which represents the most recent day, trying to predict tomorrow)
    last_row = X_scaled[-1].reshape(1, -1)
    pred = model.predict(last_row)[0]
    prob = model.predict_proba(last_row)[0]
    
    confidence = prob[pred]
    prediction_label = "Buy" if pred == 1 else "Sell"
    
    return {
        "prediction": prediction_label,
        "confidence": round(float(confidence) * 100, 2)
    }
