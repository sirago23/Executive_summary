import re

import mermaid
import pytest

NODE_LINE = re.compile(r'^  (?:  )?n_\w+\["[^"\n]*"\]$')
EDGE_LINE = re.compile(r'^  n_\w+ -->(?:\|"[^"\n]*"\|)? n_\w+$')


def nodes(*labels: str) -> list[dict]:
    return [{"id": f"a{i}", "label": label} for i, label in enumerate(labels)]


def test_escape_label_handles_quotes_newlines_and_markup():
    out = mermaid.escape_label('Say "hi"\nthen <script>alert(1)</script> & `x`')
    assert '"' not in out
    assert "\n" not in out
    assert "<" not in out and ">" not in out and "`" not in out
    assert "#quot;hi#quot;" in out
    assert "#lt;script#gt;" in out


def test_escape_label_keeps_brackets_inside_quotes_harmless():
    out = mermaid.escape_label("a[b](c){d}")
    assert out == "a[b](c){d}"


def test_literal_hash_cannot_form_an_entity():
    assert mermaid.escape_label("#quot;") == "#35;quot;"


def test_flowchart_has_header_nodes_and_edges():
    text = mermaid.to_flowchart(
        nodes("Start", "End"), [{"from": "a0", "to": "a1", "label": "go"}], "TB"
    )
    lines = text.splitlines()
    assert lines[0] == "flowchart TB"
    assert all(NODE_LINE.match(line) or EDGE_LINE.match(line) for line in lines[1:])
    assert '  n_a0["Start"]' in lines
    assert '  n_a0 -->|"go"| n_a1' in lines


def test_edge_without_label_has_no_label_part():
    text = mermaid.to_flowchart(nodes("A", "B"), [{"from": "a0", "to": "a1"}])
    assert "  n_a0 --> n_a1" in text.splitlines()


def test_groups_become_subgraphs_with_escaped_titles():
    items = [
        {"id": "a", "label": "App", "group": 'Your "computer"'},
        {"id": "b", "label": "Files", "group": 'Your "computer"'},
        {"id": "c", "label": "Cloud"},
    ]
    lines = mermaid.to_flowchart(items, []).splitlines()
    assert '  subgraph g_1["Your #quot;computer#quot;"]' in lines
    assert lines.count("  subgraph g_1" + '["Your #quot;computer#quot;"]') == 1
    assert '    n_a["App"]' in lines and '    n_b["Files"]' in lines
    assert lines.index("  end") > lines.index('    n_b["Files"]')
    assert '  n_c["Cloud"]' in lines


def test_node_ids_cannot_inject_mermaid_syntax():
    with pytest.raises(ValueError, match="node id"):
        mermaid.to_flowchart([{"id": "a-->b", "label": "x"}], [])


def test_node_id_named_end_is_safe_because_ids_are_prefixed():
    text = mermaid.to_flowchart([{"id": "end", "label": "Done"}], [])
    assert '  n_end["Done"]' in text.splitlines()


def test_direction_is_restricted():
    with pytest.raises(ValueError, match="direction"):
        mermaid.to_flowchart(nodes("A"), [], "LR; click a0 call alert()")


def test_a_node_id_with_a_trailing_newline_is_rejected():
    with pytest.raises(ValueError, match="node id"):
        mermaid.to_flowchart([{"id": "a\n", "label": "x"}], [])
