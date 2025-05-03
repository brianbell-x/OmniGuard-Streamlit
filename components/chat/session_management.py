"""
Streamlit session management utilities for Strengthening Guardrails chat application.
Handles conversation state and session initialization.
"""

import uuid
import json
import streamlit as st
from typing import Callable, Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from functools import wraps
from guardrail.prompts import guardrails_system_prompt, agent_system_prompt


@dataclass
class SessionDefaults:
    """Default values for session state initialization."""

    messages: list = None
    base_conversation_id: str = None
    turn_number: int = 0
    conversation_id: str = None
    guardrails_input_context: Optional[str] = None
    guardrails_output_message: Optional[str] = None
    guardrails_raw_api_response: Optional[dict] = None
    agent_messages: Optional[list] = None
    guardrails_system_prompt: str = None
    agent_system_prompt: str = None
    conversation_context: Optional[str] = None
    schema_violation: bool = False
    schema_violation_context: Optional[str] = None
    compliant: Optional[bool] = None
    action: Optional[str] = None

    def __post_init__(self):
        self.messages = []
        self.base_conversation_id = str(uuid.uuid4())
        self.conversation_id = f"{self.base_conversation_id}-{self.turn_number}"
        self.guardrails_system_prompt = guardrails_system_prompt
        self.agent_system_prompt = agent_system_prompt


def ensure_session_state(func: Callable):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not hasattr(st, "session_state"):
            st.session_state = {}
        return func(*args, **kwargs)

    return wrapper


@ensure_session_state
def generate_conversation_id(turn_number: int = 0) -> str:
    if "base_conversation_id" not in st.session_state:
        st.session_state.base_conversation_id = str(uuid.uuid4())
        st.session_state.turn_number = 0
    return f"{st.session_state.base_conversation_id}-{turn_number}"


@ensure_session_state
def reset_chat_session_state(update_conversation_context: Callable) -> None:
    defaults = SessionDefaults()
    for key, value in asdict(defaults).items():
        setattr(st.session_state, key, value)
    update_conversation_context()


@ensure_session_state
def init_chat_session_state(update_conversation_context: Callable) -> None:
    defaults = SessionDefaults()
    for key, value in asdict(defaults).items():
        if key not in st.session_state:
            setattr(st.session_state, key, value)

    # Initialize conversation_context if not present
    if (
        "conversation_context" not in st.session_state
        or st.session_state.conversation_context is None
    ):
        initial_conversation = build_conversation_json(st.session_state.messages)
        st.session_state.conversation_context = format_conversation_context(initial_conversation)
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "turn_number" not in st.session_state:
        st.session_state.turn_number = 0
    if "base_conversation_id" not in st.session_state:
        st.session_state.base_conversation_id = str(uuid.uuid4())
    if "conversation_id" not in st.session_state:
        st.session_state.conversation_id = (
            f"{st.session_state.base_conversation_id}-{st.session_state.turn_number}"
        )


# *** CONVERSATION UTILITIES ***
def build_conversation_json(messages: List[Dict[str, str]]) -> Dict[str, Any]:
    """
    Constructs and returns a dictionary representing the conversation structure.
    """
    system_prompt = st.session_state.agent_system_prompt
    full_messages = [{"role": "system", "content": system_prompt}]
    full_messages.extend(messages)
    return {
        "id": st.session_state.conversation_id,
        "messages": full_messages,
    }


def format_conversation_context(conversation: Dict[str, Any]) -> str:
    """
    Formats a conversation dictionary into the XML-like structure expected by the system.
    """
    conversation_json = json.dumps(conversation, indent=2)
    return f"<input>\n{conversation_json}\n</input>"
