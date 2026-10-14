"""Turn diagram data (nodes and edges) into Mermaid flowchart text.

Claude never writes Mermaid. Every label is escaped here, node ids are checked and prefixed, and
the direction is restricted, so nothing in summary.json can add Mermaid syntax.
"""

from __future__ import annotations

import re

NODE_ID = re.compile(r"^[A-Za-z0-9_]+$")
DIRECTIONS = {"TB", "LR"}

# Order matters: "#" goes first so the entity codes added after it are not touched.
_ESCAPES = [
    ("#", "#35;"),
    ('"', "#quot;"),
    ("<", "#lt;"),
    (">", "#gt;"),
    ("&", "#amp;"),
    ("`", "#96;"),
]


def escape_label(text: str) -> str:
    """Make a node, group or edge label safe inside Mermaid quotes."""
    out = " ".join(text.split())
    for char, entity in _ESCAPES:
        out = out.replace(char, entity)
    return out


def _node_ref(node_id: str) -> str:
    if not NODE_ID.match(node_id):
        raise ValueError(f"node id {node_id!r} may only use letters, digits and underscore")
    return f"n_{node_id}"


def to_flowchart(nodes: list[dict], edges: list[dict], direction: str = "TB") -> str:
    """Return Mermaid text. Nodes with the same `group` share a subgraph."""
    if direction not in DIRECTIONS:
        raise ValueError(f"direction must be one of {', '.join(sorted(DIRECTIONS))}")
    lines = [f"flowchart {direction}"]

    groups: dict[str, list[dict]] = {}
    for node in nodes:
        if node.get("group"):
            groups.setdefault(node["group"], []).append(node)
    for number, (name, members) in enumerate(groups.items(), start=1):
        lines.append(f'  subgraph g_{number}["{escape_label(name)}"]')
        lines.extend(f'    {_node_ref(n["id"])}["{escape_label(n["label"])}"]' for n in members)
        lines.append("  end")
    lines.extend(
        f'  {_node_ref(n["id"])}["{escape_label(n["label"])}"]' for n in nodes if not n.get("group")
    )

    for edge in edges:
        label = f'|"{escape_label(edge["label"])}"|' if edge.get("label") else ""
        lines.append(f"  {_node_ref(edge['from'])} -->{label} {_node_ref(edge['to'])}")
    return "\n".join(lines)
