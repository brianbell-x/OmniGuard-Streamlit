from pathlib import Path

guardrails_system_prompt = (
    Path(__file__).with_name("prompts").joinpath("guardrail_instructions.md").read_text()
)
agent_system_prompt = "You are a helpful assistant."
