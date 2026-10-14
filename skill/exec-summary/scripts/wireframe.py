"""Turn a screen description into a grayscale HTML wireframe.

A screen is {"title": ..., "blocks": [{"type": ..., "label": ...}]}. Only the block types listed
in BLOCK_TYPES exist, and every string is escaped, so nothing in summary.json becomes markup.
"""

from __future__ import annotations

from html import escape

BLOCK_TYPES = ("header", "nav", "stats", "chart", "list", "form", "button", "text", "image")
MAX_ITEMS = 6
EXAMPLE_NOTE = "Example layout, not the final design"


def esc(value: object) -> str:
    return escape(str(value), quote=True)


def _items(label: str) -> list[str]:
    """Split a comma-separated label into at most MAX_ITEMS items."""
    parts = [p.strip() for p in label.split(",") if p.strip()]
    return (parts or [label])[:MAX_ITEMS]


def _item_row(label: str) -> str:
    return "".join(f'<span class="wf-item">{esc(item)}</span>' for item in _items(label))


def _bars() -> str:
    return "".join(f'<i style="height:{h}%"></i>' for h in (45, 70, 55, 85, 60))


def _lines(count: int) -> str:
    return "".join('<span class="wf-line"></span>' for _ in range(count))


def render_block(block: dict) -> str:
    kind, label = block["type"], block["label"]
    if kind not in BLOCK_TYPES:
        raise ValueError(f"unknown block type {kind!r}")
    text = esc(label)
    if kind in ("nav", "stats"):
        inner = _item_row(label)
    elif kind == "chart":
        inner = f'<span class="wf-caption">{text}</span><span class="wf-bars">{_bars()}</span>'
    elif kind == "list":
        inner = f'<span class="wf-caption">{text}</span>{_lines(3)}'
    elif kind == "form":
        fields = "".join(f'<span class="wf-field">{esc(item)}</span>' for item in _items(label))
        inner = fields
    elif kind == "text":
        inner = f'<span class="wf-caption">{text}</span>{_lines(2)}'
    else:  # header, button, image
        inner = text
    return f'<div class="wf-block wf-{kind}">{inner}</div>'


def render_wireframe(screen: dict) -> str:
    blocks = "".join(render_block(b) for b in screen["blocks"])
    return (
        '<figure class="wireframe">'
        f"<figcaption>{esc(screen['title'])}</figcaption>"
        f'<div class="wf-screen">{blocks}</div>'
        f'<p class="wf-note">{EXAMPLE_NOTE}</p>'
        "</figure>"
    )
