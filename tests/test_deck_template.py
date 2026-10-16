"""Accessibility and layout rules of the deck template (deck.css, deck.js, deck.html).

The browser checks (360 px, print, keyboard) were done by hand on the real deck. These tests lock
the rules that make them pass.
"""

import re
from pathlib import Path

import pytest

TEMPLATES = Path(__file__).resolve().parents[1] / "skill" / "exec-summary" / "templates"
CSS = (TEMPLATES / "deck.css").read_text(encoding="utf-8")
JS = (TEMPLATES / "deck.js").read_text(encoding="utf-8")
HTML = (TEMPLATES / "deck.html").read_text(encoding="utf-8")

TOKENS = (
    "bg",
    "surface",
    "text",
    "muted",
    "line",
    "accent",
    "accent-text",
    "accent-soft",
    "card",
    "hi",
    "med",
    "lo",
    "hi-bg",
    "med-bg",
    "lo-bg",
)
LEVELS = ("hi", "med", "lo")


def block(selector_start: str) -> str:
    """The body of the first CSS block whose selector line starts with selector_start."""
    start = CSS.index(selector_start)
    return CSS[CSS.index("{", start) + 1 : CSS.index("}", start)]


def tokens(body: str) -> dict[str, str]:
    found = re.findall(r"--([a-z-]+):\s*#([0-9a-fA-F]{3,6})\b", body)
    return {name: "#" + (h if len(h) == 6 else "".join(c * 2 for c in h)) for name, h in found}


def dark_block() -> str:
    start = CSS.index("@media (prefers-color-scheme: dark)")
    return CSS[CSS.index("{", CSS.index("{", start) + 1) + 1 :].split("}")[0]


def luminance(hex_colour: str) -> float:
    channels = [int(hex_colour[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def ratio(a: str, b: str) -> float:
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def blend(front: str, back: str, opacity: float) -> str:
    mixed = [
        round(int(front[i : i + 2], 16) * opacity + int(back[i : i + 2], 16) * (1 - opacity))
        for i in (1, 3, 5)
    ]
    return "#" + "".join(f"{c:02x}" for c in mixed)


THEMES = {
    "light": tokens(block(":root {")),
    "dark": tokens(dark_block()),
    "print": tokens(block('  :root,\n  :root[data-theme="dark"]')),
}


@pytest.mark.parametrize("theme", THEMES)
def test_every_theme_defines_every_colour_token(theme):
    assert set(TOKENS) <= set(THEMES[theme])


@pytest.mark.parametrize("theme", THEMES)
def test_body_text_meets_wcag_aa_contrast(theme):
    t = THEMES[theme]
    assert ratio(t["text"], t["surface"]) >= 4.5
    assert ratio(t["muted"], t["surface"]) >= 4.5
    assert ratio(t["accent"], t["surface"]) >= 4.5
    assert ratio(t["accent-text"], t["accent"]) >= 4.5


@pytest.mark.parametrize("theme", THEMES)
def test_text_stays_readable_on_cards_tiles_and_pills(theme):
    t = THEMES[theme]
    for ink in ("text", "muted", "accent"):
        assert ratio(t[ink], t["card"]) >= 4.5, ink
    assert ratio(t["accent"], t["accent-soft"]) >= 4.5


@pytest.mark.parametrize("theme", THEMES)
def test_source_column_contrast_after_its_opacity(theme):
    t = THEMES[theme]
    found = re.search(r"td\.src \{[^}]*opacity:\s*([0-9.]+)", CSS)
    opacity = float(found.group(1)) if found else 1.0  # none: small and light is enough
    assert ratio(blend(t["muted"], t["surface"], opacity), t["surface"]) >= 4.5
    assert ratio(blend(t["muted"], t["card"], opacity), t["card"]) >= 4.5


def test_only_the_source_column_may_break_inside_a_word():
    """At 360 px, "sample/SPEC_sample.md" in the Source column pushed tables wider than the
    screen. overflow-wrap: break-word does not lower the minimum width, "anywhere" does. It is
    kept to the Source column so ordinary words like "Framework" are never split."""
    assert "overflow-wrap: anywhere" in block("th.src,\ntd.src {")
    assert "overflow-wrap: anywhere" in block("td.path {")  # file names on the title slide
    assert "overflow-wrap: anywhere" not in block("th,\ntd {")


@pytest.mark.parametrize("level", LEVELS)
@pytest.mark.parametrize("theme", THEMES)
def test_impact_colours_meet_aa_on_the_slide_cards_and_badges(theme, level):
    t = THEMES[theme]
    assert ratio(t[level], t["surface"]) >= 4.5
    assert ratio(t[level], t["card"]) >= 4.5
    assert ratio(t[level], t[f"{level}-bg"]) >= 4.5


def test_impact_levels_take_their_colour_from_the_tokens_in_every_theme():
    for level, token in (("high", "hi"), ("med", "med"), ("low", "lo")):
        rule = block(f".impact-{level} {{")
        assert f"color: var(--{token})" in rule
        assert f"background: var(--{token}-bg)" in rule
    assert ".impact-high" not in dark_block() and 'data-theme="dark"] .impact' not in CSS


def test_no_colour_is_written_outside_the_token_definitions():
    stray = [
        line.strip()
        for line in CSS.splitlines()
        if re.search(r"#[0-9a-fA-F]{3,6}\b", line) and not line.strip().startswith("--")
    ]
    assert stray == []


def test_tables_use_hairlines_and_no_zebra_stripes():
    assert "nth-child(even)" not in CSS
    assert "text-transform: uppercase" in block("\nth {")


def test_the_slide_is_a_rounded_frame_with_one_soft_shadow():
    rule = block(".slide {")
    assert "--radius-slide: 14px" in block(":root {")
    assert "border-radius: var(--radius-slide)" in rule
    assert rule.count("box-shadow") == 1
    screen = CSS[: CSS.index("@media print")]
    assert screen.count("box-shadow") == 1  # print switches it off


def test_the_only_gradients_are_the_wireframe_image_placeholder():
    """The title-slide glow is added in Task 14; until then no other gradient may appear."""
    uses = re.findall(r"[a-z-]*gradient\(", CSS)
    assert uses == ["repeating-linear-gradient("]


def test_on_a_desktop_window_the_page_stays_put_and_the_slide_scrolls_inside_itself():
    desktop = CSS[CSS.index("@media (min-width: 720px)") :]
    assert re.search(r"\.js body \{[^}]*overflow:\s*hidden", desktop)
    active = re.search(r"\.js \.slide\.active \{([^}]*)\}", desktop).group(1)
    assert "overflow-y: auto" in active
    assert "min-height: 0" in active
    assert "calc(100vh" not in CSS  # the old "grow past the window" rule is gone


def test_buttons_in_the_bar_are_pills():
    assert "border-radius: 999px" in block("button {")


def test_focus_ring_is_visible_and_not_removed():
    assert ":focus-visible" in CSS
    assert re.search(r":focus-visible \{[^}]*outline:\s*3px", CSS)
    assert not re.search(r"outline:\s*(none|0)\b", CSS)


def test_every_control_in_the_bar_is_a_real_button_or_summary():
    assert '<button type="button" id="prev">' in HTML
    assert '<button type="button" id="next">' in HTML
    assert 'role="switch"' in HTML and 'aria-checked="false"' in HTML
    assert "<summary>Contents</summary>" in HTML


def test_slide_keys_still_work_while_a_checkbox_has_focus():
    """After ticking a box with Space, Home/End/arrows must still move between slides. Only
    fields where the user types text may swallow them."""
    handler = JS[JS.index('addEventListener("keydown"') :]
    assert 'tag === "INPUT"' not in handler
    assert "isTyping" in handler


def test_the_narrow_source_and_file_columns_keep_a_readable_minimum_width():
    assert re.search(r"min-width:\s*\d+(\.\d+)?em", block("td.path {"))
    narrow = CSS[CSS.index("@media (max-width: 719px)") :]
    assert re.search(r"td\.src \{[^}]*min-width:\s*\d+(\.\d+)?em", narrow)


def test_phone_layout_gives_the_content_more_width():
    """With a 15 px scrollbar a 360 px phone has 345 px; four-column tables need the room."""
    narrow = CSS[CSS.index("@media (max-width: 719px)") :].split("\n}\n\n")[0:3]
    text = "\n".join(narrow)
    assert re.search(r"#deck \{[^}]*padding:\s*8px", text)
    assert re.search(r"\.slide \{[^}]*padding:\s*20px 12px", text)


def test_arrow_keys_do_not_steal_keys_from_buttons_with_modifiers():
    assert "event.altKey || event.ctrlKey || event.metaKey" in JS
    for key in ("ArrowRight", "ArrowLeft", "Home", "End"):
        assert f'"{key}"' in JS


def test_print_shows_every_slide_one_per_page_in_light_colours():
    printed = CSS[CSS.index("@media print") :]
    assert "break-after: page" in printed
    assert re.search(r"\.bar \{\s*display: none", printed)
    assert "--bg: #fff" in printed


def test_motion_is_switched_off_when_the_reader_asks_for_less():
    assert "@media (prefers-reduced-motion: reduce)" in CSS
