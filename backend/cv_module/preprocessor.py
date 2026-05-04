import cv2
import numpy as np

def process_uploaded_image(image_bytes: bytes):
    """
    Decodes an uploaded image from bytes.
    Returns (img_bgr, img_rgb, img_gray).
    """
    nparr = np.frombuffer(image_bytes, np.uint8)
    img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if img_bgr is None:
        raise ValueError("Failed to decode image. Ensure it is a valid image file.")

    # Resize to a standard width for consistent analysis (keep aspect ratio)
    max_width = 1200
    h, w = img_bgr.shape[:2]
    if w > max_width:
        scale = max_width / w
        img_bgr = cv2.resize(img_bgr, (max_width, int(h * scale)), interpolation=cv2.INTER_AREA)

    img_rgb  = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    img_gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    return img_bgr, img_rgb, img_gray
