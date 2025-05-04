from guardrail.config import settings
from openai import OpenAI

def openai_responses_create(
    model: str,
    input_messages: list[dict],
    text: dict = None,
    temperature: float = 1.0,
    max_output_tokens: int = 4096,
    top_p: float = 1.0,
    **kwargs
) -> dict:
    client = OpenAI(api_key=settings.openai_api_key)
    params = {
        "model": model,
        "input": input_messages,
        "max_output_tokens": max_output_tokens,
        "store": True,
    }
    if model != settings.safety_model:
        params["temperature"] = temperature
        params["top_p"] = top_p
    else:
        # For the safety model, set reasoning effort to "low"
        params["reasoning"] = {"effort": "low"}
    if text is not None:
        params["text"] = text
    params.update(kwargs)
    response = client.responses.create(**params)
    return response.model_dump() if hasattr(response, "model_dump") else response
