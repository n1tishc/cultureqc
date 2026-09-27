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


def anomaly_tile_view(img, result, zoom=2):
    """The 256 px QC tile, enlarged, with the patch-distance heatmap over the
    224 px region DINOv2 scores (culture.anomaly). Colour is on a fixed scale
    anchored at the bin's threshold, never per-image min-max: transparent
    below half the threshold, full at 1.5x. The TOP_PATCHES patches that set
    the image score are outlined. Returns RGB uint8, or None if unavailable."""
    from culture.anomaly import CROP_PX, GRID, PATCH_PX, TILE_PX
    from culture.cache import qc_tile_from

    if result is None or result.status != "ok":
        return None
    tile = cv2.cvtColor(qc_tile_from(img), cv2.COLOR_GRAY2RGB)
    d = np.asarray(result.patch_distances, dtype=np.float32)
    thr = float(result.threshold)
    level = np.clip((d - 0.5 * thr) / thr, 0.0, 1.0)                   # 0 at 0.5·thr, 1 at 1.5·thr
    off = (TILE_PX - CROP_PX) // 2
    heat = cv2.resize(level, (CROP_PX, CROP_PX), interpolation=cv2.INTER_NEAREST)
    colour = cv2.cvtColor(cv2.applyColorMap((heat * 255).astype(np.uint8), cv2.COLORMAP_INFERNO), cv2.COLOR_BGR2RGB)
    alpha = (0.65 * heat)[..., None]
    region = tile[off:off + CROP_PX, off:off + CROP_PX].astype(np.float32)
    tile[off:off + CROP_PX, off:off + CROP_PX] = (colour * alpha + region * (1 - alpha)).astype(np.uint8)
    tile = cv2.resize(tile, (TILE_PX * zoom, TILE_PX * zoom), interpolation=cv2.INTER_NEAREST)
    s = zoom
    cv2.rectangle(tile, (off * s, off * s), ((off + CROP_PX) * s - 1, (off + CROP_PX) * s - 1), (80, 200, 255), 1)
    for r, c in result.top_patches:
        y0, x0 = (off + r * PATCH_PX) * s, (off + c * PATCH_PX) * s
        cv2.rectangle(tile, (x0, y0), (x0 + PATCH_PX * s - 1, y0 + PATCH_PX * s - 1), (255, 255, 255), 2)
    assert GRID * PATCH_PX == CROP_PX
    return tile


def outline_scored_region(rgb, height, width):
    """Outline, on the full frame, the 224 px region the anomaly score reads."""
    from culture.anomaly import CROP_PX, TILE_PX, tile_box

    x0, y0, sx, sy = tile_box(height, width)
    off = (TILE_PX - CROP_PX) // 2
    p0 = (int(x0 + sx * off), int(y0 + sy * off))
    p1 = (int(x0 + sx * (off + CROP_PX)) - 1, int(y0 + sy * (off + CROP_PX)) - 1)
    out = rgb.copy()
    cv2.rectangle(out, p0, p1, (80, 200, 255), max(2, round(min(height, width) / 300)))
    return out
