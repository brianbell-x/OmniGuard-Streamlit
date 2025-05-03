"""
Chat UI for Guardrails Chatbot

Handles message display, debug info, sidebar, and user input.
"""

import streamlit as st
from typing import Dict, Any, Protocol, Callable, Optional


def display_messages(messages: list[dict]) -> None:
    """Render chat messages with role-based formatting."""
    for msg in messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])


def display_debug_expanders(
    guardrails_input_context: Optional[str],
    guardrails_output_message: Optional[str],
    agent_messages: Optional[list[str]],
    feedback_callback: Optional[Callable] = None,
) -> None:
    """Show debug info in expanders/popovers, optionally including feedback."""
    if guardrails_input_context:
        with st.expander("Guardrail"):
            with st.popover("To: Guardrail"):
                st.code(guardrails_input_context, language="xml")
            if guardrails_output_message:
                with st.popover("From: Guardrail"):
                    st.json(guardrails_output_message, expanded=True)

            # Feedback widget (if callback and at least one check ID present)
            if feedback_callback and (
                st.session_state.get("latest_user_check_id") is not None or
                st.session_state.get("latest_agent_check_id") is not None
            ):
                st.divider()
                turn_number = st.session_state.get("turn_number", 0)
                feedback_key = f"feedback_guardrail_{turn_number}"
                comment_key = f"feedback_comment_{turn_number}"
                st.feedback(
                    options="thumbs",
                    key=feedback_key,
                    on_change=feedback_callback,
                )
                st.text_input(
                    "Comment (optional)",
                    key=comment_key,
                    placeholder="Add any additional feedback here...",
                    on_change=feedback_callback,
                )

            st.caption(
                "Feedback only applies to the final step shown (agent response or refusal). "
                "Use the text box if you want to comment specifically on the initial check of your own input, "
                "especially if it passed when it shouldn't have."
            )

    if agent_messages:
        with st.expander("Agent"):
            with st.popover("To: Agent"):
                st.write(agent_messages)
            with st.popover("From: Agent"):
                messages = st.session_state.get("messages", [])
                if messages:
                    last_messages = messages[-1:] if len(messages) >= 2 else messages
                    st.json(last_messages)
                elif st.session_state.get("agent_raw_api_response"):
                    response = st.session_state.get("agent_raw_api_response")
                    try:
                        agent_output = response["output"][0]["content"][0]["text"]
                    except (KeyError, IndexError, TypeError):
                        agent_output = "[Error: No agent output returned]"
                    st.write("Agent's final response:")
                    st.write(agent_output)
                elif st.session_state.get("agent_output"):
                    agent_output = st.session_state.get("agent_output")
                    st.write("Agent's final response:")
                    st.write(agent_output)
                else:
                    st.write("No agent response available")


class ResetCallback(Protocol):
    def __call__(self) -> None: ...


def setup_sidebar(session_state: Dict[str, Any], reset_callback: ResetCallback) -> None:
    """Setup sidebar with controls and help."""
    with st.sidebar:
        if st.button("CLEAR CHAT", use_container_width=True) and session_state.get("messages"):
            reset_callback()
            st.rerun()

        st.divider()
        st.caption("Need Help? Message [Brian](https://x.com/brianbellx)")


def get_user_input() -> Optional[str]:
    """Capture user input with constraints."""
    return st.chat_input(
        "Type your message here",
        max_chars=20000,
        key="chat_input",
    )
