"""
cultureQC dark theme — real lab-instrument software, not a Gradio default.

Every token is set for both the light and dark variants to the same dark
value, so the UI stays dark regardless of the browser's OS-level color
scheme preference (per UI_PLAN.md: "Dark theme only. No light mode toggle
needed.").
"""

import gradio as gr

BG_PRIMARY = "#0f1117"
BG_CARD = "#1a1d24"
BORDER = "#2a2d34"
TEXT_PRIMARY = "#f0f0f0"
TEXT_SECONDARY = "#9ca3af"
TEXT_MUTED = "#6b7280"
ACCENT = "#3b82f6"
ACCENT_HOVER = "#2563eb"

SYSTEM_SANS = "ui-sans-serif, -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif"
SYSTEM_MONO = "ui-monospace, 'SF Mono', 'JetBrains Mono', Menlo, Consolas, monospace"


class CultureQCTheme(gr.themes.Base):
    def __init__(self):
        super().__init__(
            primary_hue=gr.themes.colors.blue,
            secondary_hue=gr.themes.colors.gray,
            neutral_hue=gr.themes.colors.gray,
            font=SYSTEM_SANS.split(", "),
            font_mono=SYSTEM_MONO.split(", "),
        )
        both = {}

        def token(name, value):
            both[name] = value
            both[f"{name}_dark"] = value

        token("body_background_fill", BG_PRIMARY)
        token("background_fill_primary", BG_PRIMARY)
        token("background_fill_secondary", BG_CARD)
        token("body_text_color", TEXT_PRIMARY)
        token("body_text_color_subdued", TEXT_SECONDARY)
        token("border_color_primary", BORDER)
        token("border_color_accent", BORDER)
        token("border_color_accent_subdued", BORDER)
        token("color_accent", ACCENT)
        token("color_accent_soft", "#1c2333")
        token("link_text_color", ACCENT)

        token("block_background_fill", BG_CARD)
        token("block_border_color", BORDER)
        token("block_border_width", "1px")
        token("block_label_background_fill", "transparent")
        token("block_label_border_color", "transparent")
        token("block_label_text_color", TEXT_SECONDARY)
        token("block_title_text_color", TEXT_SECONDARY)
        token("block_info_text_color", TEXT_MUTED)
        token("panel_background_fill", BG_PRIMARY)
        token("panel_border_color", BORDER)

        token("input_background_fill", BG_CARD)
        token("input_border_color", BORDER)
        token("input_placeholder_color", TEXT_MUTED)

        token("checkbox_background_color", BG_CARD)
        token("checkbox_border_color", BORDER)
        token("checkbox_label_background_fill", BG_CARD)
        token("checkbox_label_background_fill_selected", ACCENT)
        token("checkbox_label_border_color", BORDER)
        token("checkbox_label_text_color", TEXT_SECONDARY)
        token("checkbox_label_text_color_selected", "#ffffff")

        token("button_primary_background_fill", ACCENT)
        token("button_primary_background_fill_hover", ACCENT_HOVER)
        token("button_primary_text_color", "#ffffff")
        token("button_primary_border_color", ACCENT)
        token("button_secondary_background_fill", BG_CARD)
        token("button_secondary_background_fill_hover", "#22252d")
        token("button_secondary_border_color", BORDER)
        token("button_secondary_text_color", TEXT_PRIMARY)

        token("shadow_drop", "none")
        token("shadow_drop_lg", "0 8px 24px rgba(0,0,0,0.35)")
        token("code_background_fill", "#12141a")

        import inspect

        valid = set(inspect.signature(gr.themes.Base.set).parameters) - {"self"}
        self.set(**{k: v for k, v in both.items() if k in valid})
