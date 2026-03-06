"""Tests for clipboard utility HTML generation."""
from credit_analyzer.ui.clipboard import clipboard_js_snippet


def test_clipboard_js_returns_html():
    html = clipboard_js_snippet()
    assert "<script>" in html
    assert "navigator.clipboard" in html


def test_clipboard_js_is_nonempty_string():
    html = clipboard_js_snippet()
    assert isinstance(html, str)
    assert len(html) > 50
