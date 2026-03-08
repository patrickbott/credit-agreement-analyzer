"""Custom Streamlit component: combined chat bar with chips and send/stop."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import streamlit.components.v1 as components

_COMPONENT_DIR = Path(__file__).parent
_component = components.declare_component("chat_bar", path=str(_COMPONENT_DIR))


def chat_bar(
    *,
    chips: list[dict[str, Any]],
    is_streaming: bool = False,
    placeholder: str = "Ask about pricing, covenants, structure...",
    disabled: bool = False,
    key: str = "chat-bar",
) -> dict[str, Any] | None:
    """Render the chat bar with chips, text input, and send/stop button.

    Returns a dict with a ``type`` key (``"submit"``, ``"stop"``, or
    ``"toggle"``) when the user interacts, or ``None`` otherwise.
    """
    return _component(
        chips=chips,
        is_streaming=is_streaming,
        placeholder=placeholder,
        disabled=disabled,
        key=key,
        default=None,
    )
