"""Extract file-upload paths after Gradio's upload-cache validation, without image conversion."""


def image_upload_path(payload):
    if payload is None or isinstance(payload, str):
        return payload
    if not isinstance(payload, dict) or not isinstance(payload.get("path"), str) or not payload["path"]:
        raise ValueError("Upload an original image file; inline image data is unsupported")
    if (payload.get("url") or "").startswith("data:"):
        raise ValueError("Upload an original image file instead of an inline data URL")
    return payload["path"]
