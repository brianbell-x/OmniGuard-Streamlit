import logging

import streamlit as st
from supabase import create_client, Client

from components.chat.chat_ui import (
    display_messages,
    display_debug_expanders,
    setup_sidebar,
    get_user_input,
)
from components.chat.chat_logic import (
    process_user_message,
    build_conversation_json,
    format_conversation_context,
)
from components.chat.session_management import (
    init_chat_session_state,
    reset_chat_session_state,
    generate_conversation_id,
)
from guardrail.config import settings

st.set_page_config(page_title="Strengthening Guardrails", page_icon="🛡️")

logger = logging.getLogger(__name__)

# --- Initialize Supabase Client for feedback ---
supabase: Client | None = None
try:
    if settings.supabase_url and settings.supabase_key:
        supabase = create_client(settings.supabase_url, settings.supabase_key)
        logger.info("Supabase client initialized successfully for feedback.")
    else:
        logger.error("Supabase URL or Key not found for feedback.")
except Exception as e:
    logger.error(f"Failed to initialize Supabase client for feedback: {e}")
    supabase = None
# -----------------------------------------------

def update_conversation_context():
    conversation = build_conversation_json(st.session_state.messages)
    st.session_state.conversation_context = format_conversation_context(conversation)

def feedback_callback():
    """Callback for st.feedback. Reads value from session state and logs feedback to Supabase."""
    turn_number = st.session_state.get('turn_number', 0)
    feedback_key = f"feedback_guardrail_{turn_number}"
    feedback_value = st.session_state.get(feedback_key)

    if feedback_value is None:
        logger.info(f"Feedback callback triggered for key {feedback_key}, but value is None (no selection or cleared). No feedback logged.")
        return

    feedback_type = "thumbs_down" if feedback_value == 0 else "thumbs_up"
    comment_key = f"feedback_comment_{turn_number}"
    feedback_text = st.session_state.get(comment_key, None)

    user_check_id = st.session_state.get("latest_user_check_id")
    agent_check_id = st.session_state.get("latest_agent_check_id")

    if user_check_id is None and agent_check_id is None:
        logger.warning(f"Feedback callback triggered for key {feedback_key}, but no interaction IDs (user_check_id, agent_check_id) found in session state for this turn. Skipping feedback logging.")
        st.toast("Feedback can only be submitted after an interaction.", icon="ℹ️")
        return

    if not supabase:
        st.error("Feedback system connection error.")
        logger.error("Supabase client not available in feedback_callback.")
        return

    last_action = st.session_state.get("action")
    target_interaction_id = agent_check_id or user_check_id

    if agent_check_id:
        logger.info(f"Feedback targets latest Agent Check ID: {agent_check_id} (Action: {last_action})")
    elif user_check_id:
        logger.info(f"Feedback targets latest User Check ID: {user_check_id} (Action: {last_action}, Agent ID missing)")

    if target_interaction_id:
        try:
            update_data = {
                "is_flagged": True,
                "feedback_type": feedback_type,
                "user_comment": feedback_text,
            }
            supabase.table("guardrail_interactions").update(update_data).eq("id", target_interaction_id).execute()
            st.toast(f"Feedback submitted for check ID {target_interaction_id}.", icon="👍")
            logger.info(f"Feedback recorded for interaction ID: {target_interaction_id}")
        except Exception as e:
            st.error("Failed to submit feedback.")
            logger.error(f"Error updating feedback for interaction ID {target_interaction_id}: {e}", exc_info=True)
    else:
        st.error("Could not identify the interaction to apply feedback to.")

def main():
    init_chat_session_state(update_conversation_context)

    setup_sidebar(
        st.session_state,
        reset_callback=lambda: reset_chat_session_state(update_conversation_context),
    )

    display_messages(st.session_state.messages)

    user_input = get_user_input()
    if user_input:
        process_user_message(
            user_input, st.session_state, generate_conversation_id, update_conversation_context
        )
        st.rerun()

    display_debug_expanders(
        st.session_state.get("guardrails_input_context"),
        st.session_state.get("guardrails_output_message"),
        st.session_state.get("agent_messages"),
        feedback_callback=feedback_callback,
    )

if __name__ == "__main__":
    main()
