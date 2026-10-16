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
NL = chr(10)


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
    assert "overflow-wrap: anywhere" in block(".path {")  # file names on the title slide
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


def test_the_only_glows_are_on_the_title_and_launch_stage_and_the_wireframe_placeholder():
    uses = re.findall(r"[a-z-]*gradient\(", CSS)
    assert sorted(uses) == [
        "radial-gradient(",
        "radial-gradient(",
        "repeating-linear-gradient(",
    ]
    glow_selectors = [
        re.sub(r"/\*.*?\*/", "", m.group(1), flags=re.S).strip()
        for m in re.finditer(r"([^{}]+)\{([^}]*radial-gradient[^}]*)\}", CSS)
    ]
    assert glow_selectors == ["#s-title", ".stage.launch"]
    printed = CSS[CSS.index("@media print") :]
    assert "radial-gradient" not in printed
    assert re.search(r"#s-title(,[^{]*)? \{[^}]*background:\s*none", printed)


def font_size_maximums() -> list[tuple[str, float]]:
    """(selector, largest rem value) for every font-size declaration that uses rem."""
    found = []
    for selector, body in re.findall(r"([^{}]+)\{([^}]*)\}", CSS):
        for value in re.findall(r"font-size:\s*([^;]+);", body):
            rems = [float(x) for x in re.findall(r"([\d.]+)rem", value)]
            if rems:
                found.append((selector.strip(), max(rems)))
    return found


def test_only_two_titles_may_be_larger_than_the_slide_title_size():
    big = [(sel, size) for sel, size in font_size_maximums() if size > 2.75]
    # 84 px for the project name, 64 px for the title of a launch-stage text slide
    assert big == [("#s-title h1", 5.25), (".stage.launch h2", 4.0)]


def test_stat_tile_numbers_stay_at_44_px_or_less():
    sizes = dict(font_size_maximums())
    assert 0 < sizes[".stat b"] <= 2.75


def test_on_a_phone_the_tiles_use_two_columns_and_that_rule_comes_after_the_base_rule():
    base = CSS.index(".stats {\n  display: grid")
    phone = CSS.index("repeat(2, minmax(0, 1fr))")
    assert phone > base  # an earlier rule would lose to the base rule and leave four columns
    assert CSS.rindex("@media (max-width: 719px)", 0, phone) > base


def test_title_slide_footer_file_names_can_break_on_a_phone():
    assert "overflow-wrap: anywhere" in block(".path {")


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
    assert re.search(r"min-width:\s*\d+(\.\d+)?em", block(".path {"))
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


def test_cards_and_risk_rows_sit_on_the_card_colour_with_rounded_corners():
    for selector in (".card {", ".risk,\n.task {", ".step {", ".stat {"):
        rule = block(selector)
        assert "background: var(--card)" in rule, selector
        assert "border-radius: var(--radius)" in rule, selector


def test_the_impact_badge_has_a_dot_in_front_of_its_word():
    assert re.search(r"\.impact::before \{[^}]*content:", CSS)


def test_print_gives_cards_and_risk_rows_a_hairline_because_paper_drops_backgrounds():
    printed = CSS[CSS.index("@media print") :]
    border = re.search(r"([^{}]+)\{\s*border:\s*1px solid var\(--line\)", printed).group(1)
    for selector in (".card", ".risk", ".task", ".step", ".stat", ".checks li"):
        assert selector in border


def test_phase_steps_have_no_counter_label_because_the_id_pill_names_them():
    assert "counter-increment" not in CSS and 'content: "Step "' not in CSS


def test_checklist_items_are_cards_and_keep_their_big_checkbox():
    assert "background: var(--card)" in block(".checks li {")
    assert re.search(r"\.checks input \{[^}]*width:\s*20px", CSS)


def test_every_source_note_is_12_px_and_11_px_on_a_phone():
    base = block(NL + ".src {")
    assert float(re.search(r"font-size:\s*([\d.]+)rem", base).group(1)) <= 0.75
    phone = CSS[CSS.index("@media (max-width: 719px)") :]
    assert re.search(r"\.src \{[^}]*font-size:\s*0\.6875rem", phone)


def test_a_risk_row_keeps_its_source_in_the_third_column_and_a_task_row_in_the_second():
    """Risks have three columns (badge, text, source), tasks two (text, source). A shared rule
    that put both sources in column 2 broke the risks slide (it grew to 1478 px)."""
    assert "grid-column: 2" not in block(".risk .src {")
    task_src = block(".task .src {")
    assert "grid-column: 2" in task_src and "grid-row: 1 / span 2" in task_src
    assert "grid-column: 1" in block(".task strong," + NL + ".task .how {")


def test_diagrams_use_the_mermaid_base_theme_with_colours_read_from_the_css_tokens():
    assert '"base"' in JS and "themeVariables" in JS
    for token in (
        "--surface",
        "--card",
        "--text",
        "--muted",
        "--accent",
        "--accent-soft",
        "--line",
    ):
        assert f'"{token}"' in JS, token
    assert "getPropertyValue" in JS
    assert '"theme": "' not in JS and '"default"' not in JS  # the old built-in themes are gone


def test_the_screen_copy_follows_the_mode_and_the_print_copy_always_uses_light_tokens():
    assert 'diagramTheme(isDark() ? "dark" : "light")' in JS
    assert 'diagramTheme("light")' in JS


def test_reading_tokens_for_the_other_mode_puts_the_page_back_as_it_was():
    reader = JS[JS.index("function diagramTheme") :]
    reader = reader[: reader.index(NL + "  }" + NL)]
    assert 'getAttribute("data-theme")' in reader
    assert "removeAttribute" in reader and "setAttribute" in reader  # restored before returning


def test_a_wireframe_sits_in_a_card_and_keeps_a_hairline_in_print():
    rule = block(".wireframe {")
    assert "background: var(--card)" in rule and "border-radius: var(--radius)" in rule
    printed = CSS[CSS.index("@media print") :]
    border = re.search(r"([^{}]+)\{\s*border:\s*1px solid var\(--line\)", printed).group(1)
    assert ".wireframe" in border


def test_the_diagram_theme_does_not_set_a_font_family():
    """Setting themeVariables.fontFamily made Mermaid drop the font from the whole diagram. The
    labels then used the monospace font of the <pre> around them and 11 of 16 were cut off. The
    Mermaid default font is measured and drawn consistently, so it is left alone."""
    assert "fontFamily" not in JS


STAGE_TOKENS = ("stage", "stage-text", "stage-muted", "stage-accent")


def test_the_launch_stage_text_is_readable_on_its_dark_stage_and_on_paper():
    on_screen = tokens(block(":root {"))
    on_paper = THEMES["print"]
    for theme in (on_screen, on_paper):
        assert set(STAGE_TOKENS) <= set(theme)
        for ink in ("stage-text", "stage-muted", "stage-accent"):
            assert ratio(theme[ink], theme["stage"]) >= 4.5, ink
    assert luminance(on_screen["stage"]) < 0.05  # dark in light mode too
    assert luminance(on_paper["stage"]) > 0.9  # light in print


def test_the_launch_stage_stays_dark_in_both_modes_because_only_the_root_block_defines_it():
    assert "--stage:" not in dark_block() and "--stage:" not in block(':root[data-theme="dark"]')


def test_the_launch_stage_title_is_64_px_at_most_and_the_split_title_is_a_normal_title():
    launch = re.search(r"\.stage\.launch h2 \{[^}]*font-size:\s*clamp\([^)]*([\d.]+)rem\)", CSS)
    assert launch and float(launch.group(1)) <= 4.0
    assert "font-size: var(--fs-title)" in block(".stage.split .panel h2 {")


def test_the_split_stage_panel_is_the_accent_with_accent_text_and_stacks_on_a_phone():
    panel = block(".stage.split .panel {")
    assert "background: var(--accent)" in panel and "color: var(--accent-text)" in panel
    phone = CSS[CSS.index("@media (max-width: 719px)", CSS.index(".stage.split {")) :]
    assert re.search(r"\.stage\.split \{[^}]*grid-template-columns:\s*minmax\(0, 1fr\)", phone)


def test_a_slide_with_a_stage_has_no_padding_so_the_stage_fills_the_frame():
    assert re.search(r"\.slide:has\(> \.stage\) \{[^}]*padding:\s*0", CSS)


def test_print_shows_both_stages_light_and_gives_the_panel_a_hairline():
    printed = CSS[CSS.index("@media print") :]
    assert "--stage: #ffffff" in printed
    assert re.search(r"\.stage\.split \.panel \{[^}]*background:\s*var\(--accent-soft\)", printed)
    assert re.search(r"\.stage\.split \.panel \{[^}]*color:\s*var\(--text\)", printed)
    assert re.search(r"\.stage\.launch \{[^}]*background:\s*none", printed)


def test_a_flow_drawn_left_to_right_gets_narrow_boxes_so_its_text_stays_readable():
    assert "flowchart LR" in JS and "wrappingWidth" in JS


def test_on_a_desktop_window_a_tall_diagram_is_scaled_to_the_window_not_scrolled():
    desktop = CSS[CSS.index("On a desktop window a tall diagram") :]
    assert re.search(r"\.js \.diagram \.mermaid svg \{[^}]*max-height:\s*calc\(100dvh", desktop)


def test_on_a_desktop_window_the_example_screen_uses_two_columns_after_its_base_rules():
    two_columns = CSS.index("One example screen per slide")
    assert two_columns > CSS.index(".wf-screen {")  # an earlier rule would lose to the base rule
    assert two_columns > CSS.index(".wf-bars i {")
