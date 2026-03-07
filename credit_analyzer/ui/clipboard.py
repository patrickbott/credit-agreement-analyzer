"""Clipboard and tooltip integration for Streamlit via injected JavaScript."""

from __future__ import annotations


def definition_tooltip_js_snippet() -> str:
    """Return JS that manages definition tooltip show/hide.

    Ensures only one tooltip is visible at a time, supports hover preview,
    click-to-pin, close button, click-outside dismiss, and Escape key.

    Inject once per page via ``st.components.v1.html(snippet, height=0)``.
    """
    return """
    <script>
    (function() {
        var root;
        try { root = parent.document; } catch(e) { root = document; }
        if (root._defTipAttached) return;
        root._defTipAttached = true;

        function clearAll() {
            var els = root.querySelectorAll('.def-hl-hover, .def-hl-active');
            for (var i = 0; i < els.length; i++) {
                els[i].classList.remove('def-hl-hover', 'def-hl-active');
            }
        }

        function clearHovers() {
            var els = root.querySelectorAll('.def-hl-hover');
            for (var i = 0; i < els.length; i++) {
                els[i].classList.remove('def-hl-hover');
            }
        }

        /* Hover: show preview — use mouseover/mouseout (they bubble) */
        root.addEventListener('mouseover', function(e) {
            var hl = e.target.closest ? e.target.closest('.def-hl') : null;
            if (!hl) return;
            /* Skip if inside a tooltip */
            if (e.target.closest && e.target.closest('.def-tip')) return;
            /* Don't hover-show if this one is already active/pinned */
            if (hl.classList.contains('def-hl-active')) return;
            if (hl.classList.contains('def-hl-hover')) return;
            clearHovers();
            hl.classList.add('def-hl-hover');
        }, false);

        root.addEventListener('mouseout', function(e) {
            var hl = e.target.closest ? e.target.closest('.def-hl') : null;
            if (!hl) return;
            /* Stay hovered if moving within the same .def-hl */
            var related = e.relatedTarget;
            if (related && related.closest && related.closest('.def-hl') === hl) return;
            hl.classList.remove('def-hl-hover');
        }, false);

        /* Click: toggle pin, or close via close button */
        root.addEventListener('click', function(e) {
            /* Close button */
            var closeBtn = e.target.closest ? e.target.closest('[data-def-close]') : null;
            if (closeBtn) {
                var parentHl = closeBtn.closest('.def-hl');
                if (parentHl) parentHl.classList.remove('def-hl-active', 'def-hl-hover');
                e.preventDefault();
                e.stopPropagation();
                return;
            }

            /* Click on a def-hl term (not inside tooltip content) */
            var hl = e.target.closest ? e.target.closest('.def-hl') : null;
            if (hl && !(e.target.closest && e.target.closest('.def-tip'))) {
                var wasActive = hl.classList.contains('def-hl-active');
                clearAll();
                if (!wasActive) {
                    hl.classList.add('def-hl-active');
                }
                e.preventDefault();
                e.stopPropagation();
                return;
            }

            /* Click outside any def-hl — close all */
            if (!e.target.closest || !e.target.closest('.def-hl')) {
                clearAll();
            }
        }, true);

        /* Escape key dismisses all */
        root.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') clearAll();
        }, true);
    })();
    </script>
    """


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
        var root;
        try { root = parent.document; } catch(e) { root = document; }
        if (root._copyListenerAttached) return;
        root._copyListenerAttached = true;
        root.addEventListener('click', function(e) {
            var btn = e.target;
            // Walk up to find .copy-btn (closest polyfill)
            while (btn && btn !== root) {
                if (btn.classList && btn.classList.contains('copy-btn')) break;
                btn = btn.parentElement;
            }
            if (!btn || !btn.classList || !btn.classList.contains('copy-btn')) return;
            e.preventDefault();
            e.stopPropagation();
            var targetId = btn.getAttribute('data-copy-target');
            var target = root.getElementById(targetId);
            if (!target) return;
            var text = target.innerText || target.textContent || '';

            // Strategy 1: Clipboard API on parent window
            try {
                var win = parent.window || window;
                if (win.navigator && win.navigator.clipboard && win.navigator.clipboard.writeText) {
                    win.navigator.clipboard.writeText(text).then(function() {
                        showCopied(btn);
                    }).catch(function() {
                        fallbackCopy(root, text, btn);
                    });
                    return;
                }
            } catch(e) {}

            // Strategy 2: execCommand fallback
            fallbackCopy(root, text, btn);
        });

        function fallbackCopy(doc, text, btn) {
            try {
                var ta = doc.createElement('textarea');
                ta.value = text;
                ta.setAttribute('readonly', '');
                ta.style.cssText = 'position:fixed;left:-9999px;top:-9999px;opacity:0;';
                doc.body.appendChild(ta);
                ta.focus();
                ta.select();
                try {
                    ta.setSelectionRange(0, text.length);
                } catch(e) {}
                var ok = doc.execCommand('copy');
                doc.body.removeChild(ta);
                if (ok) {
                    showCopied(btn);
                    return;
                }
            } catch(e) {}

            // Strategy 3: window.prompt fallback (last resort)
            try {
                var win = parent.window || window;
                win.prompt('Copy this text (Ctrl+C):', text);
                showCopied(btn);
            } catch(e) {}
        }

        function showCopied(btn) {
            btn.classList.add('copied');
            btn.setAttribute('title', 'Copied!');
            setTimeout(function() {
                btn.classList.remove('copied');
                btn.setAttribute('title', 'Copy to clipboard');
            }, 1500);
        }
    })();
    </script>
    """
