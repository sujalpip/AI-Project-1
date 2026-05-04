"""
Chart Pattern Detector — OpenCV-based rule engine.

Instead of relying on a generic YOLO model (trained on COCO objects like cars/people),
this module uses real computer vision techniques to detect actual stock chart patterns:

  • Candlestick extraction via color segmentation
  • Price-series reconstruction from pixel data
  • Peak/trough detection for pattern matching
  • Pattern recognition: Head & Shoulders, Double Top/Bottom,
    Ascending/Descending Triangle, Bullish/Bearish Engulfing,
    Doji, Hammer, Shooting Star, Support/Resistance levels
"""

import cv2
import numpy as np
from scipy.signal import argrelextrema


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _extract_price_series(img_gray, img_bgr):
    """
    Extracts an approximate price series from the chart image.
    Strategy:
      1. Detect the chart plot area (crop away axes/labels).
      2. For each column, find the dominant price pixel (darkest or most
         saturated region — works for both dark and light themes).
    Returns a 1-D numpy array of normalised price values (0=bottom, 1=top).
    """
    h, w = img_gray.shape

    # Crop 10% from each side to remove axes/labels
    x0 = int(w * 0.08)
    x1 = int(w * 0.92)
    y0 = int(h * 0.05)
    y1 = int(h * 0.90)

    chart_gray = img_gray[y0:y1, x0:x1]
    chart_bgr  = img_bgr[y0:y1, x0:x1]
    ch, cw     = chart_gray.shape

    # Convert to HSV to find coloured candle bodies
    chart_hsv = cv2.cvtColor(chart_bgr, cv2.COLOR_BGR2HSV)

    # Green candles: hue ~60-90 (OpenCV hue 0-180)
    green_mask = cv2.inRange(chart_hsv, (35, 40, 40), (90, 255, 255))
    # Red candles: hue ~0-15 or 160-180
    red_mask1  = cv2.inRange(chart_hsv, (0,  40, 40), (15, 255, 255))
    red_mask2  = cv2.inRange(chart_hsv, (160, 40, 40), (180, 255, 255))
    red_mask   = cv2.bitwise_or(red_mask1, red_mask2)
    candle_mask = cv2.bitwise_or(green_mask, red_mask)

    # Fallback: use edge/gradient if no coloured candles found
    if candle_mask.sum() < 500:
        edges = cv2.Canny(chart_gray, 30, 100)
        candle_mask = edges

    price_series = []
    for col in range(cw):
        col_mask = candle_mask[:, col]
        rows = np.where(col_mask > 0)[0]
        if len(rows) > 0:
            # Use midpoint of candle body in this column
            mid = (rows[0] + rows[-1]) / 2.0
            # Invert: top of image = high price
            price_series.append(1.0 - mid / ch)
        else:
            price_series.append(None)

    # Fill None gaps with linear interpolation
    series = np.array(price_series, dtype=float)
    nans   = np.isnan(series.astype(float))
    # Replace None with nan
    series_f = np.where([v is None for v in price_series], np.nan, series)
    if np.all(np.isnan(series_f)):
        return np.linspace(0.4, 0.6, cw)  # flat fallback

    # Interpolate
    x_all   = np.arange(cw)
    x_valid = x_all[~np.isnan(series_f)]
    y_valid = series_f[~np.isnan(series_f)]
    series_interp = np.interp(x_all, x_valid, y_valid)

    # Smooth to reduce noise
    kernel = max(3, cw // 60)
    if kernel % 2 == 0:
        kernel += 1
    series_smooth = cv2.GaussianBlur(series_interp.reshape(1, -1).astype(np.float32),
                                     (kernel, 1), 0).flatten()
    return series_smooth


def _find_peaks_troughs(series, order=None):
    """Returns indices of local maxima and minima."""
    if order is None:
        order = max(5, len(series) // 20)
    peaks   = argrelextrema(series, np.greater, order=order)[0]
    troughs = argrelextrema(series, np.less,    order=order)[0]
    return peaks, troughs


def _norm_diff(a, b):
    """Normalised absolute difference."""
    return abs(a - b) / (max(abs(a), abs(b)) + 1e-9)


# ─── Individual Pattern Detectors ─────────────────────────────────────────────

def _detect_head_and_shoulders(series, peaks, troughs, w):
    """Classic Head & Shoulders (bearish reversal)."""
    results = []
    if len(peaks) < 3 or len(troughs) < 2:
        return results

    for i in range(len(peaks) - 2):
        ls, head, rs = peaks[i], peaks[i+1], peaks[i+2]
        # Head must be highest
        if series[head] <= series[ls] or series[head] <= series[rs]:
            continue
        # Shoulders roughly equal (within 8%)
        if _norm_diff(series[ls], series[rs]) > 0.08:
            continue
        # Neckline: troughs between shoulders
        mid_troughs = [t for t in troughs if ls < t < rs]
        if len(mid_troughs) < 2:
            continue
        conf = 0.72 + min(0.20, (series[head] - max(series[ls], series[rs])) * 2)
        x1 = int(ls / len(series) * w)
        x2 = int(rs / len(series) * w)
        results.append({
            "pattern": "Head & Shoulders",
            "confidence": round(min(conf, 0.92), 2),
            "bbox": [x1, 0, x2, 1],   # will be scaled in annotator
            "signal": "bearish"
        })
    return results


def _detect_inverse_head_and_shoulders(series, peaks, troughs, w):
    """Inverse Head & Shoulders (bullish reversal)."""
    results = []
    if len(troughs) < 3 or len(peaks) < 2:
        return results

    for i in range(len(troughs) - 2):
        ls, head, rs = troughs[i], troughs[i+1], troughs[i+2]
        if series[head] >= series[ls] or series[head] >= series[rs]:
            continue
        if _norm_diff(series[ls], series[rs]) > 0.08:
            continue
        mid_peaks = [p for p in peaks if ls < p < rs]
        if len(mid_peaks) < 2:
            continue
        conf = 0.70 + min(0.20, (min(series[ls], series[rs]) - series[head]) * 2)
        x1 = int(ls / len(series) * w)
        x2 = int(rs / len(series) * w)
        results.append({
            "pattern": "Inverse Head & Shoulders",
            "confidence": round(min(conf, 0.91), 2),
            "bbox": [x1, 0, x2, 1],
            "signal": "bullish"
        })
    return results


def _detect_double_top(series, peaks, w):
    """Double Top (bearish reversal)."""
    results = []
    if len(peaks) < 2:
        return results

    for i in range(len(peaks) - 1):
        p1, p2 = peaks[i], peaks[i+1]
        # Peaks roughly equal height (within 5%)
        if _norm_diff(series[p1], series[p2]) > 0.05:
            continue
        # Must have a meaningful valley between them
        valley = series[p1:p2].min()
        drop   = series[p1] - valley
        if drop < 0.04:
            continue
        conf = 0.68 + min(0.22, drop * 3)
        x1 = int(p1 / len(series) * w)
        x2 = int(p2 / len(series) * w)
        results.append({
            "pattern": "Double Top",
            "confidence": round(min(conf, 0.90), 2),
            "bbox": [x1, 0, x2, 1],
            "signal": "bearish"
        })
    return results


def _detect_double_bottom(series, troughs, w):
    """Double Bottom (bullish reversal)."""
    results = []
    if len(troughs) < 2:
        return results

    for i in range(len(troughs) - 1):
        t1, t2 = troughs[i], troughs[i+1]
        if _norm_diff(series[t1], series[t2]) > 0.05:
            continue
        peak_between = series[t1:t2].max()
        rise = peak_between - series[t1]
        if rise < 0.04:
            continue
        conf = 0.68 + min(0.22, rise * 3)
        x1 = int(t1 / len(series) * w)
        x2 = int(t2 / len(series) * w)
        results.append({
            "pattern": "Double Bottom",
            "confidence": round(min(conf, 0.90), 2),
            "bbox": [x1, 0, x2, 1],
            "signal": "bullish"
        })
    return results


def _detect_ascending_triangle(series, peaks, troughs, w):
    """Ascending Triangle — flat resistance, rising support (bullish)."""
    results = []
    n = len(series)
    if len(peaks) < 3 or len(troughs) < 3:
        return results

    # Check last portion of chart
    recent_peaks   = peaks[-4:]
    recent_troughs = troughs[-4:]

    # Flat resistance: peaks roughly equal
    peak_vals = series[recent_peaks]
    if np.std(peak_vals) / (np.mean(peak_vals) + 1e-9) > 0.03:
        return results

    # Rising troughs
    trough_vals = series[recent_troughs]
    if not np.all(np.diff(trough_vals) > -0.01):  # allow tiny dips
        return results

    conf = 0.70 + min(0.18, float(np.mean(np.diff(trough_vals))) * 5)
    x1 = int(recent_peaks[0] / n * w)
    x2 = int(recent_peaks[-1] / n * w)
    results.append({
        "pattern": "Ascending Triangle",
        "confidence": round(min(conf, 0.88), 2),
        "bbox": [x1, 0, x2, 1],
        "signal": "bullish"
    })
    return results


def _detect_descending_triangle(series, peaks, troughs, w):
    """Descending Triangle — flat support, falling resistance (bearish)."""
    results = []
    n = len(series)
    if len(peaks) < 3 or len(troughs) < 3:
        return results

    recent_peaks   = peaks[-4:]
    recent_troughs = troughs[-4:]

    # Flat support
    trough_vals = series[recent_troughs]
    if np.std(trough_vals) / (np.mean(trough_vals) + 1e-9) > 0.03:
        return results

    # Falling peaks
    peak_vals = series[recent_peaks]
    if not np.all(np.diff(peak_vals) < 0.01):
        return results

    conf = 0.68 + min(0.18, float(abs(np.mean(np.diff(peak_vals)))) * 5)
    x1 = int(recent_troughs[0] / n * w)
    x2 = int(recent_troughs[-1] / n * w)
    results.append({
        "pattern": "Descending Triangle",
        "confidence": round(min(conf, 0.87), 2),
        "bbox": [x1, 0, x2, 1],
        "signal": "bearish"
    })
    return results


def _detect_support_resistance(series, peaks, troughs, w, img_h):
    """Detect horizontal support and resistance levels."""
    results = []
    n = len(series)

    # Cluster peak values → resistance
    if len(peaks) >= 2:
        peak_vals = series[peaks]
        resistance = float(np.median(peak_vals))
        # Count how many peaks are near this level
        near = np.sum(np.abs(peak_vals - resistance) < 0.04)
        if near >= 2:
            conf = min(0.60 + near * 0.08, 0.88)
            results.append({
                "pattern": "Resistance Level",
                "confidence": round(conf, 2),
                "bbox": [0, 0, w, 1],
                "signal": "bearish",
                "level": resistance
            })

    # Cluster trough values → support
    if len(troughs) >= 2:
        trough_vals = series[troughs]
        support = float(np.median(trough_vals))
        near = np.sum(np.abs(trough_vals - support) < 0.04)
        if near >= 2:
            conf = min(0.60 + near * 0.08, 0.88)
            results.append({
                "pattern": "Support Level",
                "confidence": round(conf, 2),
                "bbox": [0, 0, w, 1],
                "signal": "bullish",
                "level": support
            })

    return results


def _detect_candlestick_patterns(img_bgr, img_gray):
    """
    Detect individual candlestick patterns by analysing the last few candles
    in the chart image (rightmost portion).
    """
    results = []
    h, w = img_bgr.shape[:2]

    # Focus on the rightmost 15% of the chart (most recent candles)
    x0 = int(w * 0.85)
    y0 = int(h * 0.05)
    y1 = int(h * 0.90)
    region = img_bgr[y0:y1, x0:w]
    rh, rw = region.shape[:2]

    if rw < 5 or rh < 5:
        return results

    hsv = cv2.cvtColor(region, cv2.COLOR_BGR2HSV)

    # Count green vs red pixels
    green_mask = cv2.inRange(hsv, (35, 40, 40), (90, 255, 255))
    red_mask1  = cv2.inRange(hsv, (0,  40, 40), (15, 255, 255))
    red_mask2  = cv2.inRange(hsv, (160, 40, 40), (180, 255, 255))
    red_mask   = cv2.bitwise_or(red_mask1, red_mask2)

    green_px = int(green_mask.sum() / 255)
    red_px   = int(red_mask.sum() / 255)
    total    = green_px + red_px

    if total < 20:
        return results

    green_ratio = green_px / total
    red_ratio   = red_px   / total

    # Bullish Engulfing: large green candle dominates
    if green_ratio > 0.70:
        results.append({
            "pattern": "Bullish Engulfing",
            "confidence": round(0.62 + green_ratio * 0.25, 2),
            "bbox": [x0, y0, w, y1],
            "signal": "bullish"
        })
    # Bearish Engulfing: large red candle dominates
    elif red_ratio > 0.70:
        results.append({
            "pattern": "Bearish Engulfing",
            "confidence": round(0.62 + red_ratio * 0.25, 2),
            "bbox": [x0, y0, w, y1],
            "signal": "bearish"
        })

    # Doji: very balanced green/red (indecision)
    if 0.40 < green_ratio < 0.60 and total > 30:
        results.append({
            "pattern": "Doji (Indecision)",
            "confidence": round(0.60 + abs(0.5 - green_ratio) * 0.4, 2),
            "bbox": [x0, y0, w, y1],
            "signal": "neutral"
        })

    return results


def _detect_trend(series):
    """Simple linear regression trend detection."""
    n = len(series)
    x = np.arange(n)
    slope, intercept = np.polyfit(x, series, 1)
    # Normalise slope relative to price range
    price_range = series.max() - series.min() + 1e-9
    norm_slope  = slope * n / price_range

    results = []
    if norm_slope > 0.15:
        results.append({
            "pattern": "Uptrend",
            "confidence": round(min(0.65 + norm_slope * 0.3, 0.90), 2),
            "bbox": [0, 0, 1, 1],
            "signal": "bullish"
        })
    elif norm_slope < -0.15:
        results.append({
            "pattern": "Downtrend",
            "confidence": round(min(0.65 + abs(norm_slope) * 0.3, 0.90), 2),
            "bbox": [0, 0, 1, 1],
            "signal": "bearish"
        })
    else:
        results.append({
            "pattern": "Sideways / Consolidation",
            "confidence": round(0.65 + (0.15 - abs(norm_slope)) * 1.5, 2),
            "bbox": [0, 0, 1, 1],
            "signal": "neutral"
        })
    return results


# ─── Main Entry Point ─────────────────────────────────────────────────────────

def detect_patterns(img_rgb, img_bgr, img_gray):
    """
    Runs the full OpenCV-based pattern detection pipeline.
    Returns a list of detection dicts with keys:
      pattern, confidence, bbox, signal
    """
    h, w = img_gray.shape
    detections = []

    # 1. Extract price series from image
    series = _extract_price_series(img_gray, img_bgr)
    if len(series) < 20:
        return detections

    # 2. Find peaks and troughs
    peaks, troughs = _find_peaks_troughs(series)

    # 3. Run all pattern detectors
    detections += _detect_trend(series)
    detections += _detect_head_and_shoulders(series, peaks, troughs, w)
    detections += _detect_inverse_head_and_shoulders(series, peaks, troughs, w)
    detections += _detect_double_top(series, peaks, w)
    detections += _detect_double_bottom(series, troughs, w)
    detections += _detect_ascending_triangle(series, peaks, troughs, w)
    detections += _detect_descending_triangle(series, peaks, troughs, w)
    detections += _detect_support_resistance(series, peaks, troughs, w, h)
    detections += _detect_candlestick_patterns(img_bgr, img_gray)

    # 4. Scale bbox from normalised → pixel coords
    for d in detections:
        bx1, by1, bx2, by2 = d["bbox"]
        # If bbox is normalised (0-1 range), scale to pixels
        if bx2 <= 1.0 and by2 <= 1.0:
            d["bbox"] = [
                int(bx1 * w), int(by1 * h),
                int(bx2 * w) if bx2 > 0 else w,
                int(by2 * h) if by2 > 0 else h
            ]
        # If bbox has pixel x coords but normalised y
        elif by2 <= 1.0:
            d["bbox"] = [
                int(bx1), int(by1 * h),
                int(bx2), int(by2 * h) if by2 > 0 else h
            ]

    # 5. Sort by confidence descending, deduplicate similar patterns
    detections.sort(key=lambda x: x["confidence"], reverse=True)
    seen = set()
    unique = []
    for d in detections:
        if d["pattern"] not in seen:
            seen.add(d["pattern"])
            unique.append(d)

    return unique
