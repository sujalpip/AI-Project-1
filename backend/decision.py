def generate_recommendation(tech_pred, sentiment_data):
    sentiment = sentiment_data['average_sentiment']
    ml_pred = tech_pred.get('prediction', 'Hold')
    confidence = tech_pred.get('confidence', 50)
    
    # Rule-based decision engine
    if ml_pred == "Buy" and sentiment == "Positive":
        action = "Strong Buy"
        adj_confidence = min(100, confidence + 15)
    elif ml_pred == "Buy" and sentiment == "Neutral":
        action = "Buy"
        adj_confidence = confidence
    elif ml_pred == "Buy" and sentiment == "Negative":
        action = "Hold"
        adj_confidence = 50
    elif ml_pred == "Sell" and sentiment == "Negative":
        action = "Strong Sell"
        adj_confidence = min(100, confidence + 15)
    elif ml_pred == "Sell" and sentiment == "Neutral":
        action = "Sell"
        adj_confidence = confidence
    elif ml_pred == "Sell" and sentiment == "Positive":
        action = "Hold"
        adj_confidence = 50
    else:
        action = "Hold"
        adj_confidence = confidence
        
    return {
        "action": action,
        "confidence": round(adj_confidence, 2),
        "ml_signal": ml_pred,
        "sentiment_signal": sentiment
    }
