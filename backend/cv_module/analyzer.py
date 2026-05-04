from .preprocessor import process_uploaded_image
from .detector    import detect_patterns
from .annotator   import draw_annotations


def analyze_chart_pipeline(image_bytes: bytes):
    """
    Full Computer Vision pipeline:
      1. Preprocess image (decode, resize, colour-space conversions)
      2. Detect patterns using OpenCV rule-based engine
      3. Annotate image with bounding boxes and labels
      4. Generate a consolidated trade signal + explanation
    """
    # 1. Preprocess
    img_bgr, img_rgb, img_gray = process_uploaded_image(image_bytes)

    # 2. Detect
    detections = detect_patterns(img_rgb, img_bgr, img_gray)

    # 3. Annotate
    annotated_b64 = draw_annotations(img_bgr, detections)

    # 4. Signal logic — weighted vote across all detections
    bullish_score = 0.0
    bearish_score = 0.0
    neutral_score = 0.0

    # Pattern weights (higher = more reliable signal)
    WEIGHTS = {
        "Head & Shoulders":           2.5,
        "Inverse Head & Shoulders":   2.5,
        "Double Top":                 2.0,
        "Double Bottom":              2.0,
        "Ascending Triangle":         1.8,
        "Descending Triangle":        1.8,
        "Bullish Engulfing":          1.5,
        "Bearish Engulfing":          1.5,
        "Doji (Indecision)":          0.5,
        "Uptrend":                    1.2,
        "Downtrend":                  1.2,
        "Sideways / Consolidation":   0.8,
        "Support Level":              1.0,
        "Resistance Level":           1.0,
    }

    bullish_patterns = []
    bearish_patterns = []
    neutral_patterns = []

    for d in detections:
        w   = WEIGHTS.get(d["pattern"], 1.0)
        sig = d.get("signal", "neutral")
        conf = d["confidence"]
        score = w * conf
        if sig == "bullish":
            bullish_score += score
            bullish_patterns.append(d["pattern"])
        elif sig == "bearish":
            bearish_score += score
            bearish_patterns.append(d["pattern"])
        else:
            neutral_score += score
            neutral_patterns.append(d["pattern"])

    total = bullish_score + bearish_score + neutral_score + 1e-9

    # Determine signal
    if bullish_score > bearish_score * 1.3:
        signal = "Buy"
        pct    = round(bullish_score / total * 100)
        pats   = ", ".join(bullish_patterns[:3]) if bullish_patterns else "bullish price action"
        explanation = (
            f"The chart shows predominantly <strong>bullish signals</strong> ({pct}% bullish weight). "
            f"Detected patterns: <strong>{pats}</strong>. "
            f"These formations suggest upward momentum and a potential buying opportunity. "
            f"Consider confirming with volume and broader market context before entering."
        )
    elif bearish_score > bullish_score * 1.3:
        signal = "Sell"
        pct    = round(bearish_score / total * 100)
        pats   = ", ".join(bearish_patterns[:3]) if bearish_patterns else "bearish price action"
        explanation = (
            f"The chart shows predominantly <strong>bearish signals</strong> ({pct}% bearish weight). "
            f"Detected patterns: <strong>{pats}</strong>. "
            f"These formations suggest downward pressure and a potential selling or exit opportunity. "
            f"Use stop-loss levels and confirm with volume before acting."
        )
    else:
        signal = "Hold"
        all_pats = ", ".join((bullish_patterns + bearish_patterns + neutral_patterns)[:4])
        explanation = (
            f"The chart shows <strong>mixed or neutral signals</strong>. "
            f"Detected: <strong>{all_pats if all_pats else 'no strong directional patterns'}</strong>. "
            f"Bullish and bearish forces appear balanced. "
            f"It is advisable to wait for a clearer breakout or confirmation signal before trading."
        )

    # Clean detections for JSON output (remove internal 'level' key if present)
    output_detections = []
    for d in detections:
        output_detections.append({
            "pattern":    d["pattern"],
            "confidence": d["confidence"],
            "signal":     d.get("signal", "neutral"),
            "bbox":       d["bbox"]
        })

    return {
        "patterns":             output_detections,
        "annotated_image_b64":  annotated_b64,
        "signal":               signal,
        "explanation":          explanation,
        "bullish_score":        round(bullish_score, 2),
        "bearish_score":        round(bearish_score, 2),
    }
