"""Display artifacts from actual inference tensors; never used to compute records.

Cellpose's raw cell score is mapped through sigmoid for display (not calibrated
probability). Grad-CAM is mapped back to the exact center crop used by QC.
"""
import base64
import cv2
import numpy as np


def png(image):
    h, w = image.shape[:2]
    if max(h, w) > 1024:
        image = cv2.resize(image, (round(w * 1024 / max(h, w)), round(h * 1024 / max(h, w))), interpolation=cv2.INTER_NEAREST)
    ok, buf = cv2.imencode('.png', image)
    if not ok:
        raise ValueError('Could not encode inference artifact')
    return 'data:image/png;base64,' + base64.b64encode(buf).decode('ascii')


def segmentation_visuals(img, score, mask):
    strength = (255 / (1 + np.exp(-np.clip(score, -30, 30)))).astype(np.uint8)
    rgba = np.zeros((*mask.shape, 4), np.uint8)
    rgba[..., :3] = (140, 220, 110)  # BGRA, microscopy green
    rgba[..., 3] = mask.astype(np.uint8) * 130
    edge = cv2.morphologyEx(mask.astype(np.uint8), cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8))
    contour = rgba.copy()
    contour[..., 3] = edge * 255
    return dict(raw=png(img), probability=png(strength), mask=png(rgba), contour=png(contour))


def qc_visual(cam, width, height):
    heat = cv2.applyColorMap((np.clip(cam, 0, 1) * 255).astype(np.uint8), cv2.COLORMAP_INFERNO)
    heat = np.dstack((heat, (np.clip(cam, 0, 1) * 200).astype(np.uint8)))
    if width >= 256 and height >= 256:
        canvas = np.zeros((height, width, 4), np.uint8)
        x, y = width // 2 - 128, height // 2 - 128
        canvas[y:y+256, x:x+256] = heat
        return png(canvas)
    return png(cv2.resize(heat, (width, height)))
