import pytest
import wireframe

ALL_TYPES = ["header", "nav", "stats", "chart", "list", "form", "button", "text", "image"]


def screen(*blocks: tuple[str, str]) -> dict:
    return {
        "title": "Home",
        "blocks": [{"type": kind, "label": label} for kind, label in blocks],
    }


@pytest.mark.parametrize("kind", ALL_TYPES)
def test_each_block_type_renders_its_label_and_class(kind):
    html = wireframe.render_wireframe(screen((kind, "My label")))
    assert f"wf-{kind}" in html
    assert "My label" in html


def test_block_types_match_the_schema_list():
    assert list(wireframe.BLOCK_TYPES) == ALL_TYPES


def test_unknown_block_type_is_rejected():
    with pytest.raises(ValueError, match="block type"):
        wireframe.render_wireframe(screen(("video", "x")))


def test_every_wireframe_is_labelled_as_an_example():
    html = wireframe.render_wireframe(screen(("header", "Top")))
    assert "Example layout, not the final design" in html


def test_title_and_labels_are_escaped():
    evil = "<script>alert(1)</script>"
    html = wireframe.render_wireframe(
        {
            "title": evil,
            "blocks": [{"type": "header", "label": evil}, {"type": "nav", "label": evil}],
        }
    )
    assert "<script>" not in html
    assert html.count("&lt;script&gt;") >= 3


def test_nav_and_stats_split_comma_lists_into_items():
    html = wireframe.render_wireframe(screen(("nav", "Home, Records, Export")))
    assert html.count('class="wf-item"') == 3
    html = wireframe.render_wireframe(screen(("stats", "Money in, Money out")))
    assert html.count('class="wf-item"') == 2


def test_long_lists_are_capped():
    html = wireframe.render_wireframe(screen(("nav", ",".join(f"i{n}" for n in range(20)))))
    assert html.count('class="wf-item"') == wireframe.MAX_ITEMS
