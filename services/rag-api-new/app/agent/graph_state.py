"""Agent graph state definition.

Shared between ``graph.py``, ``router.py``, and ``cv_nodes.py``
to avoid circular imports.
"""
from __future__ import annotations

from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """State for the top-level StateGraph.

    Attributes:
        messages: Conversation history (append-only via ``add_messages``).
        pending_action: Active multi-turn flow (``""`` = none,
            ``"cv_awaiting_email"`` = waiting for email address).
    """

    messages: Annotated[list, add_messages]
    pending_action: str
