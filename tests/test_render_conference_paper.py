from __future__ import annotations

from scripts.render_conference_paper import RenderError, render

import pytest


def test_renderer_preserves_scientific_literals_and_escapes_text() -> None:
    source = "# Result & Scope\n\n| Arm | AP |\n|---|---:|\n| decoupled | 0.9891 |\n"

    rendered = render(source)

    assert "<h1>Result &amp; Scope</h1>" in rendered
    assert "<td>0.9891</td>" in rendered
    assert rendered == render(source)


def test_renderer_rejects_unsupported_markdown() -> None:
    with pytest.raises(RenderError, match="unsupported Markdown"):
        render("# Title\n\n- hidden list semantics\n")
