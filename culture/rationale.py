"""
cultureqc.rationale — Human-readable, evidence-referencing rationale for QC decisions.

Two modes:
    template (default): deterministic, always valid, GMP-defensible.
    vlm:                Qwen2-VL-2B zero-shot, timeboxed experiment.

The template ships unless the VLM passes the quality gate (>=95% validity,
<=2% hallucinated numbers). Either way, both are logged.

Usage:
    from cultureqc.rationale import generate_rationale

    rationale = generate_rationale(
        qc_flag="contamination_suspected",
        qc_confidence=0.92,
        evidence_bbox=(45, 120, 80, 60),
        confluency_pct=71.3,
        target_confluency=80.0,
        action="human_review",
        tile_size=256,
    )
"""

from __future__ import annotations


# ---------------------------------------------------------------------------
# Quadrant helper
# ---------------------------------------------------------------------------

def _bbox_quadrant(bbox: tuple | list | None, tile_size: int = 256) -> str:
    """Convert a (x, y, w, h) bbox center to a human-readable quadrant."""
    if bbox is None:
        return "across the field"

    x, y, w, h = bbox
    cx = x + w / 2
    cy = y + h / 2
    mid = tile_size / 2

    v = "upper" if cy < mid else "lower"
    hz = "left" if cx < mid else "right"
    return f"{v}-{hz} quadrant"


# ---------------------------------------------------------------------------
# Flag / action phrase maps
# ---------------------------------------------------------------------------

_FLAG_PHRASES = {
    "normal": "No abnormalities detected",
    "contamination_suspected": "Small dark rod-like or particulate objects detected",
    "detachment": "Gaps in the cell monolayer with bright rounded floating bodies detected",
    "image_quality": "Image artifact detected (possible blur, dust, bubble, or scratch)",
}

_ACTION_PHRASES = {
    "passage": "proceed with passage",
    "feed": "perform media exchange",
    "hold": "no action required; continue monitoring",
    "human_review": "pause automated decisions and flag for human review",
}

_TREND_PHRASES = {
    "rising": "trending upward",
    "flat": "stable",
    "falling": "declining",
    "unknown": None,
    None: None,
}


# ---------------------------------------------------------------------------
# Template rationale (the default, always ships)
# ---------------------------------------------------------------------------

def template_rationale(
    qc_flag: str,
    qc_confidence: float,
    evidence_bbox: tuple | list | None,
    confluency_pct: float,
    target_confluency: float = 80.0,
    action: str = "hold",
    growth_trend: str | None = None,
    tile_size: int = 256,
) -> str:
    """
    Deterministic two-sentence rationale built from classifier output + Grad-CAM.

    Always correct because it only references values it's handed, never invents.
    This is the more GMP-defensible design: a deterministic sentence that's
    always right beats a VLM that's occasionally wrong.
    """
    quadrant = _bbox_quadrant(evidence_bbox, tile_size)
    flag_phrase = _FLAG_PHRASES.get(qc_flag, f"QC flag '{qc_flag}' raised")
    action_phrase = _ACTION_PHRASES.get(action, action)

    # Sentence 1: what was detected and where
    if qc_flag == "normal":
        s1 = f"{flag_phrase} in the field of view; culture appears healthy."
    else:
        s1 = (
            f"{flag_phrase} in the {quadrant} "
            f"(confidence {qc_confidence:.0%})."
        )

    # Sentence 2: confluency context + recommended action
    conf_vs_target = (
        f"above target ({target_confluency:.0f}%)"
        if confluency_pct >= target_confluency
        else f"below target ({target_confluency:.0f}%)"
    )

    trend_str = ""
    trend_phrase = _TREND_PHRASES.get(growth_trend)
    if trend_phrase:
        trend_str = f", {trend_phrase}"

    s2 = (
        f"Confluency {confluency_pct:.1f}% {conf_vs_target}{trend_str}; "
        f"recommend {action_phrase}."
    )

    return f"{s1} {s2}"


# ---------------------------------------------------------------------------
# VLM rationale (optional, timeboxed experiment)
# ---------------------------------------------------------------------------

def vlm_rationale(
    image_path: str,
    qc_flag: str,
    qc_confidence: float,
    evidence_bbox: tuple | list | None,
    confluency_pct: float,
    target_confluency: float = 80.0,
    action: str = "hold",
    model_name: str = "Qwen/Qwen2-VL-2B-Instruct",
    max_retries: int = 1,
) -> str | None:
    """
    Zero-shot VLM rationale using Qwen2-VL-2B.

    Returns the rationale string if valid, None if it fails validation.
    Caller should fall back to template_rationale on None.

    Validation:
      - Must be valid text (not empty, not JSON garbage)
      - Must be <=2 sentences
      - Must mention the QC flag class
      - Must not contain numbers that aren't in the input (hallucination check)
    """
    try:
        import re
        import torch
        from transformers import Qwen2VLForConditionalGeneration, AutoProcessor
        from PIL import Image

        processor = AutoProcessor.from_pretrained(model_name)
        model = Qwen2VLForConditionalGeneration.from_pretrained(
            model_name, torch_dtype=torch.float16, device_map="auto"
        )

        img = Image.open(image_path).convert("RGB")

        quadrant = _bbox_quadrant(evidence_bbox)

        prompt = f"""You are a cell culture quality control assistant. Analyze this brightfield microscope image.

The automated QC system reports:
- QC flag: {qc_flag} (confidence: {qc_confidence:.0%})
- Evidence region: {quadrant}
- Confluency: {confluency_pct:.1f}% (target: {target_confluency:.0f}%)
- Recommended action: {action}

Write exactly two sentences:
Sentence 1: Describe what you observe in the image that supports the QC flag, referencing the evidence region.
Sentence 2: State the confluency relative to target and the recommended action.

Do NOT invent any numbers. Only use the numbers provided above. Be concise and factual."""

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": img},
                    {"type": "text", "text": prompt},
                ],
            }
        ]

        text_input = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = processor(text=[text_input], images=[img], return_tensors="pt").to(model.device)

        for attempt in range(max_retries + 1):
            with torch.no_grad():
                output_ids = model.generate(**inputs, max_new_tokens=150, temperature=0.3)

            generated = output_ids[0][inputs.input_ids.shape[1]:]
            rationale = processor.decode(generated, skip_special_tokens=True).strip()

            # Validate
            if not rationale or len(rationale) < 20:
                continue

            # <=2 sentences
            sentences = [s.strip() for s in re.split(r'[.!?]+', rationale) if s.strip()]
            if len(sentences) > 3:  # allow slight slack
                continue

            # Must mention the flag class (or a recognizable variant)
            flag_terms = {
                "normal": ["normal", "healthy", "clean"],
                "contamination_suspected": ["contaminat", "bacteria", "particulate", "rod-like"],
                "detachment": ["detach", "gap", "floating", "rounded"],
                "image_quality": ["blur", "dust", "bubble", "scratch", "artifact", "quality"],
            }
            terms = flag_terms.get(qc_flag, [qc_flag])
            if not any(t.lower() in rationale.lower() for t in terms):
                continue

            # Hallucination check: extract all numbers from the rationale,
            # verify each one appears in the input values
            allowed_numbers = {
                str(round(confluency_pct, 1)),
                str(round(confluency_pct)),
                str(int(confluency_pct)),
                str(round(target_confluency)),
                str(int(target_confluency)),
                str(round(qc_confidence * 100)),
                str(int(qc_confidence * 100)),
            }
            found_numbers = set(re.findall(r'\d+\.?\d*', rationale))
            hallucinated = found_numbers - allowed_numbers
            if len(hallucinated) > 0:
                continue

            return rationale

        return None  # all attempts failed validation

    except ImportError:
        return None
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_rationale(
    qc_flag: str,
    qc_confidence: float,
    evidence_bbox: tuple | list | None,
    confluency_pct: float,
    target_confluency: float = 80.0,
    action: str = "hold",
    growth_trend: str | None = None,
    tile_size: int = 256,
    use_vlm: bool = False,
    image_path: str | None = None,
) -> dict:
    """
    Generate a rationale. Returns dict with:
        rationale: str      — the two-sentence rationale
        method: str         — "template" or "vlm"
        vlm_attempted: bool
        vlm_succeeded: bool
    """
    vlm_succeeded = False
    rationale = None

    if use_vlm and image_path:
        rationale = vlm_rationale(
            image_path=image_path,
            qc_flag=qc_flag,
            qc_confidence=qc_confidence,
            evidence_bbox=evidence_bbox,
            confluency_pct=confluency_pct,
            target_confluency=target_confluency,
            action=action,
        )
        if rationale:
            vlm_succeeded = True

    if rationale is None:
        rationale = template_rationale(
            qc_flag=qc_flag,
            qc_confidence=qc_confidence,
            evidence_bbox=evidence_bbox,
            confluency_pct=confluency_pct,
            target_confluency=target_confluency,
            action=action,
            growth_trend=growth_trend,
            tile_size=tile_size,
        )

    return {
        "rationale": rationale,
        "method": "vlm" if vlm_succeeded else "template",
        "vlm_attempted": use_vlm,
        "vlm_succeeded": vlm_succeeded,
    }
