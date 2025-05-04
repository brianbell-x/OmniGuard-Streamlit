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
    conversation_id: str = None
    guardrails_input_context: Optional[str] = None
    guardrails_output_message: Optional[str] = None
    agent_messages: Optional[list] = None
    agent_system_prompt: str = None
    conversation_context: Optional[str] = None
    compliant: Optional[bool] = None
    action: Optional[str] = None
    guardrail_flags: dict = None # Added for stateful flags

    def __post_init__(self):
        self.messages = []
        self.conversation_id = str(uuid.uuid4()) + "-0"
        self.agent_system_prompt = agent_system_prompt
        self.guardrail_flags = {} # Initialize flags


def ensure_session_state(func: Callable):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not hasattr(st, "session_state"):
            st.session_state = {}
        return func(*args, **kwargs)

    return wrapper


@ensure_session_state
def generate_conversation_id(turn_number: int = 0) -> str:
    return str(uuid.uuid4()) + f"-{turn_number}"


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
    if "conversation_id" not in st.session_state:
        st.session_state.conversation_id = str(uuid.uuid4()) + "-0"


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


# --- SUPABASE CLIENT ---
def get_supabase_client():
    """
    Returns a Supabase client using credentials from app secrets.
    """
    try:
        from supabase import create_client
    except ImportError:
        raise ImportError(
            "supabase-py is not installed. Install it with 'pip install supabase'."
        )
    from guardrail.config import settings
    url = settings.supabase_url
    key = settings.supabase_key
    if not url or not key:
        raise RuntimeError(
            "Supabase URL and key must be set in app secrets."
        )
    return create_client(url, key)
