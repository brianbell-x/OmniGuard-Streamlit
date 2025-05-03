import logging
from pydantic import BaseModel, ValidationError
from typing import Literal, List, Dict, Any, Tuple
from components.api_client import openai_responses_create
from guardrail.prompts import guardrails_system_prompt
from guardrail.config import settings

logger = logging.getLogger(__name__)

SCHEMA_ERROR_STATIC_REFUSAL = (
    "I encountered an issue processing the safety check response structure. "
    "Please try again or rephrase your message."
)

class ResponseObj(BaseModel):
    action: Literal["RefuseUser", "RefuseAssistant"]
    rules_violated: List[str]
    RefuseUser: str | None = None
    RefuseAssistant: str | None = None

class SafetyResult(BaseModel):
    conversation_id: str
    analysis: str
    compliant: bool
    response: ResponseObj | None = None

def guardrails_check(conversation_xml: str) -> Tuple[list, dict, SafetyResult]:
    input_messages = [
        {"role": "developer", "content": [{"type": "input_text", "text": guardrails_system_prompt}]},
        {"role": "user", "content": [{"type": "input_text", "text": conversation_xml}]},
    ]
    raw_response = {}
    try:
        raw_response = openai_responses_create(
            model=settings.safety_model,
            input_messages=input_messages,
            text={"format": {"type": "json_object"}},
            reasoning={"summary": "detailed"},
        )
        message = next(
            (item for item in raw_response.get("output", [])
             if item.get("type") == "message" and item.get("role") == "assistant"),
            None,
        )
        if (
            not message
            or "content" not in message
            or not isinstance(message["content"], list)
            or not message["content"]
            or "text" not in message["content"][0]
        ):
            raise ValueError("Missing or invalid message content in safety LLM response.")
        content = message["content"][0]["text"]
        try:
            parsed_result = SafetyResult.model_validate_json(content)
        except ValidationError as ve:
            logger.error(
                f"Schema validation failed: {ve}. Raw content: '{content}'. Full response: {str(raw_response)[:500]}"
            )
            parsed_result = SafetyResult(
                conversation_id="error-schema",
                analysis="Safety check response failed schema validation.",
                compliant=False,
                response=ResponseObj(
                    action="RefuseUser",
                    rules_violated=["SCHEMA_VALIDATION_ERROR"],
                    RefuseUser=SCHEMA_ERROR_STATIC_REFUSAL
                ),
            )
            return input_messages, raw_response, parsed_result
    except ValidationError as ve:
        logger.error(
            f"Schema validation failed (outer): {ve}. Full response: {str(raw_response)[:500]}"
        )
        parsed_result = SafetyResult(
            conversation_id="error-schema",
            analysis="Safety check response failed schema validation.",
            compliant=False,
            response=ResponseObj(
                action="RefuseUser",
                rules_violated=["SCHEMA_VALIDATION_ERROR"],
                RefuseUser=SCHEMA_ERROR_STATIC_REFUSAL
            ),
        )
        return input_messages, raw_response, parsed_result
    except Exception as e:
        logger.exception(f"Unexpected error during safety validation: {e}")
        parsed_result = SafetyResult(
            conversation_id="error-parsing",
            analysis=f"An unexpected error occurred during safety validation: {e}",
            compliant=False,
            response=ResponseObj(
                action="RefuseUser",
                rules_violated=["SYSTEM_ERROR"],
                RefuseUser="An internal error occurred during safety validation."
            ),
        )
        return input_messages, raw_response, parsed_result

    return input_messages, raw_response, parsed_result
