import cv2
import numpy as np
import base64


# Color palette (BGR)
COLORS = {
    "bullish": (80, 200, 120),    # green
    "bearish": (80, 100, 240),    # red
    "neutral": (80, 180, 240),    # orange/yellow
}

LABEL_BG = {
    "bullish": (30, 100, 50),
    "bearish": (40, 40, 160),
    "neutral": (40, 120, 160),
}


def _draw_label(img, text, x, y, color, bg_color):
    """Draw a filled-background label."""
    font       = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.48
    thickness  = 1
    (tw, th), baseline = cv2.getTextSize(text, font, font_scale, thickness)
    pad = 4
    # Background rect
    cv2.rectangle(img,
                  (x - pad, y - th - pad),
                  (x + tw + pad, y + baseline + pad),
                  bg_color, -1)
    # Border
    cv2.rectangle(img,
                  (x - pad, y - th - pad),
                  (x + tw + pad, y + baseline + pad),
                  color, 1)
    # Text
    cv2.putText(img, text, (x, y), font, font_scale, (240, 240, 240), thickness, cv2.LINE_AA)


def draw_annotations(img_bgr, detections):
    """
    Draws bounding boxes, labels, and a legend on the image.
    Returns the annotated image as a base64-encoded PNG string.
    """
    img = img_bgr.copy()
    h, w = img.shape[:2]

    # Semi-transparent overlay for boxes
    overlay = img.copy()

    for det in detections:
        sig    = det.get("signal", "neutral")
        color  = COLORS.get(sig, COLORS["neutral"])
        bg     = LABEL_BG.get(sig, LABEL_BG["neutral"])
        x1, y1, x2, y2 = det["bbox"]

        # Clamp to image bounds
        x1 = max(0, min(x1, w - 1))
        x2 = max(0, min(x2, w - 1))
        y1 = max(0, min(y1, h - 1))
        y2 = max(0, min(y2, h - 1))

        # Skip degenerate boxes
        if x2 - x1 < 4 or y2 - y1 < 4:
            # For full-width patterns (trend/support/resistance), draw a horizontal line
            if det["pattern"] in ("Uptrend", "Downtrend", "Sideways / Consolidation"):
                # Draw diagonal trend line
                cv2.line(img, (int(w * 0.08), int(h * 0.85)),
                         (int(w * 0.92), int(h * 0.15)), color, 2, cv2.LINE_AA)
            elif "Level" in det["pattern"] and "level" in det:
                level_y = int((1.0 - det["level"]) * h * 0.85 + h * 0.05)
                cv2.line(img, (int(w * 0.08), level_y),
                         (int(w * 0.92), level_y), color, 2, cv2.LINE_AA)
                _draw_label(img, f"{det['pattern']} ({det['confidence']:.0%})",
                            int(w * 0.08) + 4, level_y - 6, color, bg)
            continue

        # Fill box with semi-transparent color
        cv2.rectangle(overlay, (x1, y1), (x2, y2), color, -1)

        # Draw border
        cv2.rectangle(img, (x1, y1), (x2, y2), color, 2, cv2.LINE_AA)

        # Label
        conf_str = f"{det['confidence']:.0%}"
        label    = f"{det['pattern']}  {conf_str}"
        lx = x1 + 4
        ly = y1 + 18 if y1 + 18 < h else y2 - 6
        _draw_label(img, label, lx, ly, color, bg)

    # Blend overlay
    cv2.addWeighted(overlay, 0.12, img, 0.88, 0, img)

    # ── Legend ──────────────────────────────────────────────────────────────
    legend_items = [
        ("Bullish Pattern", COLORS["bullish"]),
        ("Bearish Pattern", COLORS["bearish"]),
        ("Neutral / Info",  COLORS["neutral"]),
    ]
    lx0, ly0 = 10, h - 10 - len(legend_items) * 22
    for i, (lbl, col) in enumerate(legend_items):
        ly = ly0 + i * 22
        cv2.rectangle(img, (lx0, ly), (lx0 + 14, ly + 14), col, -1)
        cv2.putText(img, lbl, (lx0 + 20, ly + 11),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42, (200, 200, 200), 1, cv2.LINE_AA)

    # ── Watermark ───────────────────────────────────────────────────────────
    cv2.putText(img, "StockSense AI  |  CV Analysis",
                (w - 230, h - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.40, (80, 80, 80), 1, cv2.LINE_AA)

    # Encode to PNG → base64
    success, buffer = cv2.imencode('.png', img)
    if not success:
        return ""
    return base64.b64encode(buffer).decode('utf-8')
