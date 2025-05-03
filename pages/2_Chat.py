import streamlit as st
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
import logging
from supabase import create_client, Client
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


def feedback_callback(): # No 'feedback' argument
    """Callback function for st.feedback. Reads value from session state."""
    # Reconstruct the key used for the feedback widget in the current turn
    feedback_key = f"feedback_guardrail_{st.session_state.get('turn_number', 0)}"
    feedback_value = st.session_state.get(feedback_key) # Get the raw value (0 or 1 for thumbs)

    if feedback_value is None:
        # This can happen if the user clears their selection or on initial load.
        # We only want to log feedback if a selection (0 or 1) is actively made.
        logger.info(f"Feedback callback triggered for key {feedback_key}, but value is None (no selection or cleared). No feedback logged.")
        # Optionally, you could update the DB entry to remove flags if feedback is cleared.
        # For now, we just return without logging to Supabase.
        return

    # Convert raw value (0=down, 1=up) to the string type expected by the database
    feedback_type = "thumbs_down" if feedback_value == 0 else "thumbs_up"

    # Retrieve the comment using the key from the text input
    comment_key = f"feedback_comment_{st.session_state.get('turn_number', 0)}"
    feedback_text = st.session_state.get(comment_key, None) # Get comment or None if empty

    # --- Rest of the original logic using derived feedback_type ---

    # Get the IDs of the checks from the *latest* interaction stored in session state
    user_check_id = st.session_state.get("latest_user_check_id") # Use new fixed key
    agent_check_id = st.session_state.get("latest_agent_check_id") # Use new fixed key

    # === Robustness Check ===
    # Ensure at least one ID exists before proceeding. If not, it means feedback
    # was likely clicked before any interaction was logged for this turn.
    if user_check_id is None and agent_check_id is None:
        logger.warning(f"Feedback callback triggered for key {feedback_key}, but no interaction IDs (user_check_id, agent_check_id) found in session state for this turn. Skipping feedback logging.")
        st.toast("Feedback can only be submitted after an interaction.", icon="ℹ️")
        return
    # ========================

    if not supabase:
        st.error("Feedback system connection error.")
        logger.error("Supabase client not available in feedback_callback.")
        return

    last_action = st.session_state.get("action")
    target_interaction_id = None

    # Heuristic for which check to update (Now we know at least one ID exists)
    # Prioritize agent check ID if available, as feedback usually relates to the final output/refusal
    if agent_check_id:
        target_interaction_id = agent_check_id
        logger.info(f"Feedback targets latest Agent Check ID: {agent_check_id} (Action: {last_action})")
    elif user_check_id:
        # Fallback to user check ID if agent check ID isn't available (e.g., user input refused directly)
        target_interaction_id = user_check_id
        logger.info(f"Feedback targets latest User Check ID: {user_check_id} (Action: {last_action}, Agent ID missing)")
    # The robustness check above ensures target_interaction_id will not be None here

    # Log the feedback to the determined interaction ID
    if target_interaction_id: # This check is slightly redundant due to robustness check, but safe
        try:
            # We only log feedback when a thumb is actively selected (value is 0 or 1)
            update_data = {
                "is_flagged": True, # Mark as flagged when feedback is given
                "feedback_type": feedback_type, # Use the derived type
                "user_comment": feedback_text # Use the retrieved comment text here
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

    # Display messages from history
    display_messages(st.session_state.messages)

    user_input = get_user_input()
    if user_input:
        process_user_message(
            user_input, st.session_state, generate_conversation_id, update_conversation_context
        )
        st.rerun()  # Rerun to display the new messages and the feedback widget

    display_debug_expanders(
        st.session_state.get("guardrails_input_context"),
        st.session_state.get("guardrails_output_message"),
        st.session_state.get("agent_messages"),
        feedback_callback=feedback_callback # Pass the callback here
    )

if __name__ == "__main__":
    main()
