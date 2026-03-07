"""Clipboard and tooltip integration for Streamlit via injected JavaScript."""

from __future__ import annotations


def clipboard_js_snippet() -> str:
    """Return an HTML/JS snippet that enables copy-to-clipboard and definition tooltips.

    Inject once per page via ``st.html(snippet, unsafe_allow_javascript=True)``.
    Runs directly in the main page context (not iframed).
    """
    return """
    <script>
    (function() {
        /* ---- Clipboard copy ---- */
        if (!document._copyListenerAttached) {
            document._copyListenerAttached = true;
            document.addEventListener('click', function(e) {
                var btn = e.target;
                while (btn && btn !== document) {
                    if (btn.classList && btn.classList.contains('copy-btn')) break;
                    btn = btn.parentElement;
                }
                if (!btn || !btn.classList || !btn.classList.contains('copy-btn')) return;
                e.preventDefault();
                e.stopPropagation();
                var targetId = btn.getAttribute('data-copy-target');
                var target = document.getElementById(targetId);
                if (!target) return;
                var text = target.innerText || target.textContent || '';

                try {
                    navigator.clipboard.writeText(text).then(function() {
                        showCopied(btn);
                    }).catch(function() {
                        fallbackCopy(text, btn);
                    });
                } catch(ignore) {
                    fallbackCopy(text, btn);
                }
            });
        }

        function fallbackCopy(text, btn) {
            try {
                var ta = document.createElement('textarea');
                ta.value = text;
                ta.setAttribute('readonly', '');
                ta.style.cssText = 'position:fixed;left:-9999px;top:-9999px;opacity:0;';
                document.body.appendChild(ta);
                ta.focus();
                ta.select();
                var ok = document.execCommand('copy');
                document.body.removeChild(ta);
                if (ok) showCopied(btn);
            } catch(ignore) {}
        }

        function showCopied(btn) {
            btn.classList.add('copied');
            btn.setAttribute('title', 'Copied!');
            setTimeout(function() {
                btn.classList.remove('copied');
                btn.setAttribute('title', 'Copy to clipboard');
            }, 1500);
        }

        /* ---- Definition tooltip click-to-pin ---- */
        if (!document._defTipAttached) {
            document._defTipAttached = true;

            function clearActive() {
                var els = document.querySelectorAll('.def-hl-active');
                for (var i = 0; i < els.length; i++) {
                    els[i].classList.remove('def-hl-active');
                }
            }

            document.addEventListener('click', function(e) {
                /* Close button inside tooltip */
                var closeBtn = e.target.closest ? e.target.closest('[data-def-close]') : null;
                if (closeBtn) {
                    var parentHl = closeBtn.closest('.def-hl');
                    if (parentHl) parentHl.classList.remove('def-hl-active');
                    e.preventDefault();
                    e.stopPropagation();
                    return;
                }

                /* Clicks inside the tooltip (scrolling, selecting text) — do nothing */
                if (e.target.closest && e.target.closest('.def-tip')) {
                    return;
                }

                /* Click on a defined term — toggle pinned */
                var hl = e.target.closest ? e.target.closest('.def-hl') : null;
                if (hl) {
                    var wasActive = hl.classList.contains('def-hl-active');
                    clearActive();
                    if (!wasActive) {
                        hl.classList.add('def-hl-active');
                    }
                    e.preventDefault();
                    e.stopPropagation();
                    return;
                }

                /* Click outside — close all */
                clearActive();
            }, true);

            /* Escape key dismisses all */
            document.addEventListener('keydown', function(e) {
                if (e.key === 'Escape') clearActive();
            }, true);
        }
    })();
    </script>
    """
