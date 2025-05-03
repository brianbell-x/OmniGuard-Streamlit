"""
Chat Logic Module

Handles chat business logic: user input, safety checks, and agent responses.
"""

import logging
from typing import Dict, Any, List, Callable, Optional, Tuple

import streamlit as st
from supabase import create_client, Client

from guardrail.config import settings
from guardrail.compliance_layer import guardrails_check, SafetyResult, SCHEMA_ERROR_STATIC_REFUSAL

from components.api_client import openai_responses_create
from components.chat.session_management import (
    generate_conversation_id,
    build_conversation_json,
    format_conversation_context,
)

logger = logging.getLogger(__name__)

# --- Supabase Client Initialization ---
def _init_supabase() -> Optional[Client]:
    try:
        if settings.supabase_url and settings.supabase_key:
            client = create_client(settings.supabase_url, settings.supabase_key)
            logger.info("Supabase client initialized successfully.")
            return client
        else:
            logger.error("Supabase URL or Key not found in settings/secrets.")
    except Exception as e:
        logger.error(f"Failed to initialize Supabase client: {e}")
    return None

supabase: Optional[Client] = _init_supabase()
# --------------------------------------

def log_guardrail_interaction(
    base_conversation_id: str,
    turn_number: int,
    check_type: str,  # 'user_input' or 'agent_response'
    raw_input: Optional[List[Dict[str, Any]]],
    raw_output: Optional[Dict[str, Any]],
    parsed_result: Optional[SafetyResult]
) -> Optional[int]:
    """
    Logs the details of a guardrail check to the Supabase database and returns the inserted row's ID.
    """
    if not supabase:
        logger.warning("Supabase client not initialized. Skipping log.")
        return None

    if not all([base_conversation_id, isinstance(turn_number, int), check_type, raw_output, parsed_result]):
        logger.warning(f"Missing essential data for logging {base_conversation_id}-{turn_number}-{check_type}. Skipping log.")
        return None

    try:
        data_to_insert = {
            "base_conversation_id": base_conversation_id,
            "turn_number": turn_number,
            "check_type": check_type,
            "raw_openai_input": raw_input,
            "raw_openai_output": raw_output,
            "compliant": parsed_result.compliant,
            "action_taken": getattr(parsed_result.response, "action", None) if parsed_result.response else None,
            "rules_violated": getattr(parsed_result.response, "rules_violated", None) if parsed_result.response else None,
            "is_flagged": False,
            "feedback_type": None,
            "user_comment": None,
        }

        response = supabase.table("guardrail_interactions").insert(data_to_insert).execute()
        if response.data and len(response.data) > 0 and 'id' in response.data[0]:
            interaction_id = response.data[0]['id']
            logger.debug(f"Logged guardrail interaction {interaction_id} for {base_conversation_id}-{turn_number}-{check_type}.")
            return interaction_id
        else:
            logger.warning(f"Could not get interaction ID directly for {base_conversation_id}-{turn_number}-{check_type}.")
            return None

    except Exception as e:
        logger.error(f"Error logging guardrail interaction to Supabase for {base_conversation_id}-{turn_number}-{check_type}: {e}", exc_info=True)
        return None

# --- AGENT SERVICE ---

def verify_agent_configuration() -> bool:
    """Check if agent system prompt is set in session state."""
    if not st.session_state.get("agent_system_prompt"):
        logger.error("Agent system prompt is missing or empty")
        return False
    return True

def fetch_agent_response() -> str:
    """
    Fetch agent's response using the model. Stores raw API response in session state.
    """
    if not verify_agent_configuration():
        raise Exception("Invalid Agent configuration state")

    main_prompt = st.session_state.get("agent_system_prompt")
    if not main_prompt:
        raise Exception("Agent system prompt is missing")

    agent_messages = [{"role": "system", "content": [{"type": "input_text", "text": main_prompt}]}]
    for message in st.session_state.messages:
        agent_messages.append(
            {
                "role": message["role"],
                "content": [{"type": "input_text", "text": message["content"]}],
            }
        )
    st.session_state.agent_messages = agent_messages

    response = openai_responses_create(
        model=st.session_state.get("selected_agent_model", settings.agent_model),
        input_messages=agent_messages,
        text={"format": {"type": "text"}},
        temperature=0.6,
        max_output_tokens=4096,
    )
    st.session_state.assistant_raw_api_response = response

    try:
        return response["output"][0]["content"][0]["text"]
    except (KeyError, IndexError):
        return "[Error: No agent output returned]"

def _call_and_log_guardrails(context_xml: str, check_type: str) -> Tuple[SafetyResult, Optional[int]]:
    """
    Helper to call guardrails_check, log the interaction, and update session state for debugging/feedback.
    Returns the SafetyResult and the interaction_id.
    """
    session = st.session_state
    raw_input, raw_output, safety_result = guardrails_check(context_xml)

    # Update debug/feedback session state
    session.guardrails_input_context = context_xml
    session.guardrails_raw_api_response = raw_output
    session.guardrails_output_message = safety_result.model_dump_json()

    interaction_id = log_guardrail_interaction(
        base_conversation_id=session.get("base_conversation_id", ""),
        turn_number=session.get("turn_number", -1),
        check_type=check_type,
        raw_input=raw_input,
        raw_output=raw_output,
        parsed_result=safety_result
    )
    if check_type == "user_input":
        if interaction_id:
            session["latest_user_check_id"] = interaction_id
        else:
            session.pop("latest_user_check_id", None)
        session.pop("latest_agent_check_id", None)
    elif check_type == "agent_response":
        if interaction_id:
            session["latest_agent_check_id"] = interaction_id
        else:
            session.pop("latest_agent_check_id", None)
        session.pop("latest_user_check_id", None)
    return safety_result, interaction_id

def process_user_message(
    user_input: str,
    session_state: Dict[str, Any],
    generate_conversation_id: Callable[[int], str],
    update_conversation_context: Callable[[], None],
) -> None:
    """
    Process user message through conversation pipeline with safety checks.
    Orchestrates the entire turn, handling schema errors and refusal logic.
    """
    if not user_input or not isinstance(user_input, str):
        return

    user_input = user_input.strip()
    session_state["turn_number"] += 1
    session_state["conversation_id"] = generate_conversation_id(session_state["turn_number"])
    session_state["messages"].append({"role": "user", "content": user_input})
    update_conversation_context()

    with st.chat_message("user"):
        st.markdown(user_input)

    try:
        # Step 1: User Input Check
        with st.spinner("Compliance Layer (User)", show_time=True):
            temp_conversation = build_conversation_json(session_state["messages"])
            temp_context_xml = format_conversation_context(temp_conversation)
            user_safety_result, user_interaction_id = _call_and_log_guardrails(temp_context_xml, "user_input")

        # Step 2: Process User Check Result
        rules_violated = getattr(user_safety_result.response, "rules_violated", []) if user_safety_result.response else []
        if "SCHEMA_VALIDATION_ERROR" in rules_violated:
            logger.warning("User input safety check failed schema validation.")
            assistant_response_to_display = getattr(user_safety_result.response, "RefuseUser", SCHEMA_ERROR_STATIC_REFUSAL)
            final_assistant_message_role = "assistant"
            session_state["compliant"] = False
            session_state["action"] = "RefuseUser"
            session_state["rules_violated"] = rules_violated
            avatar = "🛡️"
            with st.chat_message(final_assistant_message_role, avatar=avatar):
                st.markdown(assistant_response_to_display)
            session_state["messages"].append({"role": final_assistant_message_role, "content": assistant_response_to_display})
            update_conversation_context()
            return
        elif not user_safety_result.compliant:
            logger.info("User input failed safety check, refusing user request.")
            assistant_response_to_display = getattr(user_safety_result.response, "RefuseUser", "I'm sorry, I can't help with that request.")
            final_assistant_message_role = "assistant"
            session_state["compliant"] = False
            session_state["action"] = getattr(user_safety_result.response, "action", "RefuseUser") if user_safety_result.response else "RefuseUser"
            session_state["rules_violated"] = rules_violated
            avatar = "🛡️"
            with st.chat_message(final_assistant_message_role, avatar=avatar):
                st.markdown(assistant_response_to_display)
            session_state["messages"].append({"role": final_assistant_message_role, "content": assistant_response_to_display})
            update_conversation_context()
            return

        # Step 3: Agent Call (only if user input was compliant)
        with st.spinner("Agent", show_time=True):
            try:
                potential_agent_response = fetch_agent_response()
            except Exception as agent_ex:
                logger.exception("Agent call failed.")
                potential_agent_response = "[Error: Agent failed to respond.]"

        # Step 4: Agent Response Check
        agent_check_messages = session_state["messages"].copy()
        agent_check_messages.append({"role": "assistant", "content": potential_agent_response})
        agent_check_conversation = build_conversation_json(agent_check_messages)
        agent_check_context_xml = format_conversation_context(agent_check_conversation)
        with st.spinner("Compliance Layer (Agent)", show_time=True):
            agent_safety_result, agent_interaction_id = _call_and_log_guardrails(agent_check_context_xml, "agent_response")

        # Step 5: Process Agent Check Result
        agent_rules_violated = getattr(agent_safety_result.response, "rules_violated", []) if agent_safety_result.response else []
        if "SCHEMA_VALIDATION_ERROR" in agent_rules_violated:
            logger.warning("Agent response safety check failed schema validation.")
            assistant_response_to_display = getattr(agent_safety_result.response, "RefuseAssistant", None) or getattr(agent_safety_result.response, "RefuseUser", SCHEMA_ERROR_STATIC_REFUSAL)
            session_state["compliant"] = False
            session_state["action"] = "RefuseAssistant"
            session_state["rules_violated"] = agent_rules_violated
            avatar = "🛡️"
        elif not agent_safety_result.compliant:
            logger.info("Agent response failed safety check, refusing agent response.")
            assistant_response_to_display = getattr(agent_safety_result.response, "RefuseAssistant", None) or getattr(agent_safety_result.response, "RefuseUser", "Agent response blocked for safety reasons.")
            session_state["compliant"] = False
            session_state["action"] = getattr(agent_safety_result.response, "action", "RefuseAssistant") if agent_safety_result.response else "RefuseAssistant"
            session_state["rules_violated"] = agent_rules_violated
            avatar = "🛡️"
        else:
            assistant_response_to_display = potential_agent_response
            avatar = None
            session_state["compliant"] = True
            session_state["action"] = "Allow"
            session_state["rules_violated"] = []

        # Step 6: Final Display
        with st.chat_message("assistant", avatar=avatar):
            st.markdown(assistant_response_to_display)
        session_state["messages"].append({"role": "assistant", "content": assistant_response_to_display})
        update_conversation_context()

    except Exception as ex:
        st.error(f"Safety system failure: {ex}")
        logger.exception("guardrail service exception during user message processing")
        error_safety_result = SafetyResult(
            conversation_id=session_state.get("conversation_id", "error"),
            analysis=f"guardrail check failed: {ex}",
            compliant=False,
            response=None,
        )
        log_guardrail_interaction(
            base_conversation_id=session_state.get("base_conversation_id", "error_id"),
            turn_number=session_state.get("turn_number", -1),
            check_type='user_input_error',
            raw_input=None,
            raw_output=None,
            parsed_result=error_safety_result
        )
        session_state["compliant"] = False
        session_state["action"] = "RefuseUser"
        session_state["rules_violated"] = []
        with st.chat_message("assistant", avatar="🛡️"):
            st.markdown("I'm sorry, I can't process that request due to a system error.")
        session_state["messages"].append(
            {"role": "assistant", "content": "I'm sorry, I can't process that request due to a system error."}
        )
        update_conversation_context()

# Remove legacy functions (now integrated into process_user_message and _call_and_log_guardrails)
# - call_guardrails_check
# - process_guardrails_result
