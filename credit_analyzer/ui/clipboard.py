"""Clipboard integration for Streamlit via injected JavaScript."""

from __future__ import annotations


def clipboard_js_snippet() -> str:
    """Return an HTML/JS snippet that enables copy-to-clipboard buttons.

    Inject once per page via ``st.components.v1.html(snippet, height=0)``.
    Any element with class ``copy-btn`` will copy the ``data-copy-target``
    element's ``innerText`` to the clipboard on click, then briefly show
    a "Copied" tooltip.
    """
    return """
    <script>
    (function() {
        const root = parent.document;
        if (root._copyListenerAttached) return;
        root._copyListenerAttached = true;
        root.addEventListener('click', function(e) {
            const btn = e.target.closest('.copy-btn');
            if (!btn) return;
            const targetId = btn.getAttribute('data-copy-target');
            const target = root.getElementById(targetId);
            if (!target) return;
            const text = target.innerText || target.textContent;
            navigator.clipboard.writeText(text).then(function() {
                btn.classList.add('copied');
                btn.setAttribute('title', 'Copied!');
                setTimeout(function() {
                    btn.classList.remove('copied');
                    btn.setAttribute('title', 'Copy');
                }, 1500);
            });
        });
    })();
    </script>
    """
