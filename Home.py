import streamlit as st

from components.chat.session_management import get_supabase_client


def introduction() -> None:
    """Render the main introduction and explanation of the project."""
    with st.expander("How it Works", expanded=False):
        st.markdown(
            """
            This project demonstrates a robust approach to **LLM guardrailing** by enforcing compliance checks on **both user and assistant messages** using a dedicated guardrail layer.

            Unlike simple keyword filters or relying on the LLM's internal safety, this system uses a **structured, schema-driven guardrail** that evaluates every user input and every assistant output before they are processed or shown.

            **Key Benefits:**
            - **Double-sided checking:** Both user and assistant messages are checked for compliance with defined rules.
            - **Structured outputs:** The guardrail returns results in a strict schema (using Pydantic models), making compliance status, violations, and refusal actions explicit and machine-verifiable.
            - **Fail-safe error handling:** If the guardrail fails (e.g., LLM error, schema validation error, or unexpected output), the system blocks the message and shows a static refusal. This ensures that even if the guardrail itself is compromised or malfunctions, no unsafe content is delivered.

            **Flow:**
            1. **User Input:** User sends a message.
            2. **Guardrail Check (User):** The message and conversation history are checked for compliance.
                - If non-compliant or guardrail fails, the message is blocked and a refusal is shown.
                - If compliant, the message is sent to the assistant.
            3. **Assistant Response:** The assistant generates a response.
            4. **Guardrail Check (Assistant):** The assistant's response and conversation history are checked.
                - If non-compliant or guardrail fails, the response is blocked and a refusal is shown.
                - If compliant, the response is delivered to the user.

            **Diagram:**
            ```
            ┌─────────┐        ┌────────────────────┐        ┌────────────┐
            │         │        │ Guardrail Check    │        │            │
            │  USER   │───────►│ (User+History)     │───────►│  ASSISTANT │
            │         │        │                    │        │   (LLM)    │
            │         │◄───────│ Guardrail Check    │◄───────│            │
            └─────────┘        │ (Assistant+History)│        └────────────┘
                               └────────────────────┘
            ```

            This approach ensures that **no single failure can result in unsafe output**: every message is checked, and any error in the guardrail logic results in a safe refusal rather than a silent pass-through.

            **Recent Enhancements (Balancing Safety & Usability):**
            To further strengthen the guardrails while minimizing unnecessary refusals (false positives), several enhancements have been implemented in the guardrail's instructions and logic:
            - **Dynamic Context Scope:** The guardrail now uses a shorter context window when checking for immediate harms (like hate speech or illegal acts) but maintains a longer memory when looking for multi-step adversarial attacks (like prompt injection attempts spread across several turns). This prevents distant, unrelated past violations from causing refusals for current benign messages.
            - **Recovery Logic:** After a refusal, if the conversation clearly shifts to a compliant topic for a few turns, the guardrail is instructed to reduce its suspicion level, allowing the conversation to recover more naturally.
            - **Stateful Flags:** The system now tracks potentially suspicious (but not immediately violating) user actions (like initiating roleplay or attempting overrides) using temporary flags. These flags provide targeted context to the guardrail for specific attack detection rules without causing persistent general defensiveness, as they expire after a few turns.

            These refinements aim to create a more nuanced and adaptive guardrail system that is both robust against attacks and less likely to impede safe, productive conversations.

            > **Note:** This method increases robustness and transparency, but also adds latency and complexity. It is not a complete AI safety solution, but a strong step toward reliable compliance enforcement.
            """
        )


def core_concepts() -> None:
    """Explain the key concepts and advantages."""
    with st.expander("Core Concepts", expanded=False):
        st.markdown(
            """
            - **Bidirectional Guardrailing:** Both user and assistant messages are checked, preventing unsafe content from either side.
            - **Structured Compliance Results:** The guardrail always returns a structured JSON object (validated by schema), making compliance status, violations, and refusal actions explicit and reliable.
            - **Fail-Safe by Design:** If the guardrail check fails (e.g., LLM error, schema mismatch, or unexpected output), the system blocks the message and shows a static refusal, ensuring no unsafe content leaks through.
            - **Explicit Rule Enforcement:** Rules are clearly defined and enforced, not left to implicit LLM behavior.
            - **Jailbreak and Bypass Resistance:** Double-sided, schema-driven checks make it much harder for prompt injection or manipulation to succeed.
            """
        )


def system_prompt_details() -> None:
    """Display details about the system prompt used for the guardrails check."""
    with st.expander("Guardrail Instructions", expanded=False):
        try:
            from guardrail.prompts import guardrails_system_prompt

            with st.popover("View Instructions"):
                st.code(guardrails_system_prompt, language="markdown")
        except ImportError:
            st.warning("Could not load guardrails system prompt.")

        st.markdown(
            """
            **Prompt Structure:**

            1. **Purpose:** Instructs the LLM to act *only* as a compliance checker, not as a conversational agent.
            2. **Instructions:** Specifies how to analyze both user and assistant messages, what rules to apply, and how to handle ambiguity.
            3. **Rule Definitions:** Lists the compliance rules (e.g., no harmful content, no PII, no adversarial prompts) with examples.
            4. **Output Schema:** Requires a strict JSON output, including:
                - `compliant` (bool): Whether the message is compliant.
                - `analysis` (str): Explanation of the decision.
                - `response` (object): If non-compliant, includes action (`RefuseUser` or `RefuseAssistant`), violated rules, and a refusal message.

            **Why Structured Output?**
            - The system parses the output using a schema (Pydantic models). If the output is malformed or missing required fields, the system blocks the message and shows a static refusal.
            - This ensures that even if the guardrail LLM is attacked or fails, no unsafe content is delivered.

            This prompt and schema-driven approach ensures **consistent, explicit, and verifiable compliance checks** for every message.
            """
        )


def technical_details() -> None:
    """Render technical implementation details."""
    with st.expander("Technical Details & Integration", expanded=False):
        st.markdown(
            """
            **Data Flow & Structure:**

            - **Input to Guardrail:** Each check receives the full conversation history and the message (user or assistant) to be checked.
            - **Output from Guardrail:** Always a structured JSON object, validated by schema. If the output is missing fields or malformed, the system blocks the message and shows a static refusal.

            **Example Guardrail Output:**
            ```json
            {
              "conversation_id": "...",
              "analysis": "The assistant's response contains PII, violating rule P1.",
              "compliant": false,
              "response": {
                "action": "RefuseAssistant",
                "rules_violated": ["P1"],
                "RefuseAssistant": "This response cannot be shown as it contains personal information."
              }
            }
            ```

            **Integration Steps:**
            1. Receive user message.
            2. Run guardrail check (user+history). If non-compliant or error, block and show refusal.
            3. If compliant, send to assistant.
            4. Run guardrail check (assistant+history). If non-compliant or error, block and show refusal.
            5. If compliant, show assistant response to user.

            **Minimal Integration Example:**

            ```python
            from guardrail.compliance_layer import guardrails_check, SafetyResult

            # 1. Check user message
            user_xml = make_conversation_xml(history, user_message)
            _, _, user_check = guardrails_check(user_xml)
            if not user_check.compliant:
                st.warning(user_check.response.RefuseUser or "User message blocked.")
                return

            # 2. Get assistant response
            assistant_response = call_llm_agent(history + [user_message])

            # 3. Check assistant response
            assistant_xml = make_conversation_xml(history + [user_message], assistant_response)
            _, _, assistant_check = guardrails_check(assistant_xml)
            if not assistant_check.compliant:
                st.warning(assistant_check.response.RefuseAssistant or "Assistant response blocked.")
                return

            # 4. Show assistant response
            st.write(assistant_response)
            ```

            - `guardrails_check` returns a structured result (`SafetyResult`).
            - If the result is non-compliant or the guardrail fails, a refusal message is shown and the flow stops.
            - This ensures **robust, explicit, and fail-safe compliance enforcement** at every step.
            """
        )


def render_open_dataset() -> None:
    """Render all Open Dataset information, applications, and download in a single expander (no repetition)."""
    with st.expander("Open Dataset", expanded=False):
        st.markdown(
            """
            All interactions processed through the **Chat** page—including user inputs, agent responses, and guardrails check results—are logged to a publicly accessible Supabase database. This dataset is intended to facilitate research and development in LLM safety and guardrailing.

            **Database Table Definition:**

            ```sql
            create table public.guardrail_interactions (
              conversation_id text not null,
              created_at timestamp with time zone not null default now(),
              check_type public.guardrail_check_type not null,
              input_list jsonb null,
              response_object jsonb null,
              compliant boolean null,
              action_taken text null,
              rules_violated text[] null,
              is_flagged boolean null default false,
              user_comment text null,
              feedback_type text null,
              schema_validation_error boolean null default false,
              constraint guardrail_interactions_unique_check unique (conversation_id, check_type)
            ) TABLESPACE pg_default;
            ```

            **Applications:**
            - Train custom compliance models or fine-tune LLMs to identify harmful content, prompt injections, or policy violations.
            - Analyze prompts and responses flagged as non-compliant to understand attack vectors and improve guardrails.
            - Benchmark safety approaches or models against real-world interactions.
            - Identify and address scenarios where agents generate non-compliant responses.
            - Seed or reference for building more diverse compliance evaluation datasets.

            """
        )

        supabase = get_supabase_client()
        # Efficient stats: single queries for counts
        try:
            total_count = (
                supabase.table("guardrail_interactions")
                .select("conversation_id", count="exact")
                .execute()
                .count
            )
            compliant_count = (
                supabase.table("guardrail_interactions")
                .select("conversation_id", count="exact")
                .eq("compliant", True)
                .execute()
                .count
            )
            noncompliant_count = (
                supabase.table("guardrail_interactions")
                .select("conversation_id", count="exact")
                .eq("compliant", False)
                .execute()
                .count
            )
            flagged_count = (
                supabase.table("guardrail_interactions")
                .select("conversation_id", count="exact")
                .eq("is_flagged", True)
                .execute()
                .count
            )
            # Total Interactions: total number of rows in the table
            # Distinct Conversations: number of unique conversation_id values
            distinct_convos = (
                supabase.table("guardrail_interactions")
                .select("conversation_id")
                .execute()
            )
            unique_convos = len({row["conversation_id"] for row in distinct_convos.data}) if distinct_convos.data else 0

            stats_data = {
                "Total Interactions": total_count,  # total rows in table
                "Compliant": compliant_count,
                "Non-Compliant": noncompliant_count,
                "Flagged": flagged_count,
                "Distinct Conversations": unique_convos,  # unique conversation_id values
            }
            st.markdown("**Dataset Statistics:**")
            st.table(stats_data)
        except Exception as e:
            st.error(f"Error fetching dataset statistics: {e}")

        st.markdown("---")
        st.markdown("**Download Full Dataset**")
        if st.button("Prepare Dataset for Download"):
            with st.spinner("Fetching and preparing dataset... This may take a moment for large datasets."):
                try:
                    # Fetch all rows
                    query = (
                        supabase.table("guardrail_interactions")
                        .select("*")
                        .order("created_at", desc=True)
                    )
                    page_size = 1000
                    all_data = []
                    page = 0
                    while True:
                        page_result = query.range(page * page_size, (page + 1) * page_size - 1).execute()
                        if not page_result.data:
                            break
                        all_data.extend(page_result.data)
                        page += 1
                        if len(page_result.data) < page_size:
                            break

                    if all_data:
                        import json

                        # Flatten rules_violated if needed
                        flat_data = []
                        for record in all_data:
                            flat_record = dict(record)
                            # Convert rules_violated (list) to comma-separated string for easier viewing
                            if "rules_violated" in flat_record and isinstance(flat_record["rules_violated"], list):
                                flat_record["rules_violated"] = ", ".join(flat_record["rules_violated"])
                            flat_data.append(flat_record)

                        jsonl_str = "\n".join(json.dumps(item) for item in flat_data)
                        st.session_state.download_data = jsonl_str
                        st.session_state.download_ready = True
                    else:
                        st.info("No data available in the dataset to download.")
                        st.session_state.download_ready = False

                except Exception as e:
                    st.error(f"Error fetching or processing dataset for download: {e}")
                    st.session_state.download_ready = False

        if st.session_state.get("download_ready", False) and "download_data" in st.session_state:
            st.download_button(
                label="Download Dataset (JSONL)",
                data=st.session_state.download_data,
                file_name="guardrail_interactions_dataset.jsonl",
                mime="application/jsonl",
                key="download_jsonl_button",
                on_click=lambda: st.session_state.update({"download_ready": False}),
            )
            st.success("Dataset ready for download.")


def findings_and_flaws() -> None:
    """Render findings and known limitations."""
    with st.expander("Current Findings & Known Flaws", expanded=False):
        st.markdown(
            """
            **Findings:**
            - The double-check mechanism demonstrably increases resistance to many basic and intermediate prompt injection techniques compared to relying solely on a single LLM's internal guardrails.
            - Explicit rule definition allows for targeted enforcement of specific policies (e.g., preventing discussion of illegal acts, blocking PII).
            - Using an LLM for the check provides better contextual understanding than simple filter lists.

            **Known Flaws & Trade-offs:**
            - **Latency:** Each turn requires *two* additional LLM calls (one for user check, one for agent check), significantly increasing response time compared to a direct agent interaction. This is the most significant drawback.
            - **Cost:** Increased LLM calls lead to higher operational costs.
            - **Complexity:** Implementing and managing the rule definitions, the checking logic, and the JSON parsing adds complexity to the application.
            - **Still Vulnerable:** Sophisticated adversarial attacks (e.g., complex multi-turn attacks, attacks targeting the *checking* LLM itself, unknown vulnerabilities) may still succeed.
            - **Rule Design:** Crafting effective, comprehensive, and unambiguous rules is challenging and requires ongoing refinement. The effectiveness heavily depends on the quality of the rules and the capability of the checking LLM.
            - **Potential for Over-Blocking:** Poorly defined rules or an overly cautious checking LLM could lead to false positives, blocking legitimate and safe interactions.
            """
        )


def render_mit_license() -> None:
    """Render the MIT license for the project."""
    with st.expander("MIT License", expanded=False):
        st.markdown(
            """
            Copyright (c) 2024 Strengthening Guardrails Contributors

            Permission is hereby granted, free of charge, to any person obtaining a copy
            of this software and associated documentation files (the "Software"), to deal
            in the Software without restriction, including without limitation the rights
            to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
            copies of the Software, and to permit persons to whom the Software is
            furnished to do so, subject to the following conditions:

            The above copyright notice and this permission notice shall be included in
            all copies or substantial portions of the Software.

            THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
            IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
            FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
            AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
            LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
            OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
            THE SOFTWARE.
            """
        )


def conclusion() -> None:
    """Render the concluding note."""
    st.markdown(
        """
        > The future of AI security doesn't just depend on big labs. It requires a community of researchers, developers, and users working together to identify risks and build better solutions.

        `Humanity can not afford AI Security Debt.`
        """
    )


def main() -> None:
    """Initialize and render the Home page."""
    st.set_page_config(page_title="Strengthening Guardrails", page_icon="🛡️", layout="wide")

    st.title("🛡️ Strengthening Guardrails")
    st.caption("An Exploration in Enhancing LLM Conversational Compliance")

    tab1, tab2, tab3, tab4 = st.tabs(
        ["Introduction & Concept", "Technical Details", "Open Dataset", "License & Support"]
    )

    with tab1:
        introduction()
        core_concepts()
        findings_and_flaws()
        conclusion()

    with tab2:
        system_prompt_details()
        technical_details()

    with tab3:
        render_open_dataset()

    with tab4:
        render_mit_license()



if __name__ == "__main__":
    main()
