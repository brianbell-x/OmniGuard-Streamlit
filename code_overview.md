# Code Overview: Strengthening Guardrails Project

## A. Overall Project Structure & Purpose

*   **What it is:** A Streamlit application demonstrating a robust approach to LLM guardrailing by enforcing compliance checks on both user and assistant messages using a dedicated guardrail layer.
*   **Core Problem Solved:** Ensuring LLM interactions adhere to defined safety and compliance rules, preventing the generation of harmful or inappropriate content.
*   **High-Level Architecture:** Standalone Streamlit web application.
*   **Technology Stack:** Python, Streamlit, OpenAI API, Pydantic (for data validation), Supabase (for data logging/feedback).

## B. File-by-File Analysis

### Home.py

*   **File Path:** `Home.py`
*   **Purpose:** This is the main entry point for the Streamlit application. It defines the overall structure of the home page, including the introduction, core concepts, technical details, open dataset information, license, and support sections. It provides a high-level overview of the project's goals and functionality.
*   **Key Components:**
    *   `introduction()`: Renders the project's introduction and explanation.
    *   `core_concepts()`: Explains the key concepts and advantages of the guardrailing approach.
    *   `system_prompt_details()`: Displays details about the system prompt used for the guardrails check.
    *   `technical_details()`: Renders technical implementation details.
    *   `render_open_dataset()`: Renders information about the open dataset of interactions.
    *   `render_mit_license()`: Renders the MIT license for the project.
    *   `conclusion()`: Renders the concluding note.
    *   `main()`: Initializes and renders the Home page.
*   **Data Structures:** None explicitly defined in this file.
*   **Algorithmic Details:** None.
*   **Error Handling Strategy:** Uses `try...except` blocks to catch potential errors during dataset statistics fetching and displays error messages using `st.error()`.
*   **Input/Output Operations:**
    *   Reads data from the Supabase database to display dataset statistics.
    *   Provides a button to prepare and download the full dataset as a JSONL file.
*   **Dependencies:**
    *   *Internal:* `components.chat.session_management.get_supabase_client` (for accessing the Supabase client).
    *   *External:* `streamlit` (for building the UI).

### pages/2_Chat.py

*   **File Path:** `pages/2_Chat.py`
*   **Purpose:** This file defines the chat interface page of the Streamlit application. It handles user input, processes messages through the guardrail and agent, and displays the conversation. It also manages feedback collection and logging.
*   **Key Components:**
    *   `update_conversation_context()`: Updates the conversation context in the session state.
    *   `feedback_callback()`: Callback function for handling user feedback on guardrail interactions. Logs feedback to Supabase.
    *   `main()`: Initializes the chat session state, sets up the sidebar, displays messages, and processes user input.
*   **Data Structures:** None explicitly defined in this file.
*   **Algorithmic Details:**
    *   The `process_user_message()` function orchestrates the entire conversation turn, including user input processing, safety checks, agent calls, and response display.
*   **Error Handling Strategy:** Uses `try...except` blocks to catch potential errors during Supabase initialization, feedback submission, and agent calls. Displays error messages using `st.error()`.
*   **Input/Output Operations:**
    *   Reads user input from the chat interface.
    *   Writes messages to the chat interface.
    *   Interacts with the OpenAI API to fetch agent responses.
    *   Interacts with the Supabase database to log guardrail interactions and feedback.
*   **Dependencies:**
    *   *Internal:*
        *   `components.chat.chat_ui` (for UI elements).
        *   `components.chat.chat_logic` (for chat processing logic).
        *   `components.chat.session_management` (for session state management).
        *   `guardrail.config` (for settings).
    *   *External:*
        *   `streamlit` (for building the UI).
        *   `supabase` (for database interaction).

### components/api_client.py

*   **File Path:** `components/api_client.py`
*   **Purpose:** This file defines the `openai_responses_create` function, which is responsible for interacting with the OpenAI API to generate responses.
*   **Key Components:**
    *   `openai_responses_create()`: Creates a response using the OpenAI API.
*   **Data Structures:** None explicitly defined in this file.
*   **Algorithmic Details:** None.
*   **Error Handling Strategy:** None explicitly defined in this file.
*   **Input/Output Operations:**
    *   Sends requests to the OpenAI API.
    *   Receives responses from the OpenAI API.
*   **Dependencies:**
    *   *Internal:* `guardrail.config` (for settings).
    *   *External:* `openai` (for interacting with the OpenAI API).

### guardrail/compliance_layer.py

*   **File Path:** `guardrail/compliance_layer.py`
*   **Purpose:** This file defines the core guardrail logic, including the `guardrails_check` function, which evaluates conversation turns against defined safety rules.
*   **Key Components:**
    *   `ResponseObj`: Pydantic model for representing the guardrail's response.
    *   `SafetyResult`: Pydantic model for representing the overall safety check result.
    *   `guardrails_check()`: Performs the guardrail check by sending the conversation context to the safety LLM and parsing the response.
*   **Data Structures:**
    *   `ResponseObj`: Defines the structure of the guardrail's response, including the action to take (RefuseUser or RefuseAssistant) and the rules violated.
    *   `SafetyResult`: Defines the structure of the overall safety check result, including the conversation ID, analysis, compliance status, and response object.
*   **Algorithmic Details:**
    *   The `guardrails_check()` function sends the conversation context to the safety LLM, parses the JSON response, and validates it against the `SafetyResult` schema.
*   **Error Handling Strategy:** Uses `try...except` blocks to catch potential errors during schema validation and LLM interaction. Returns a `SafetyResult` object with an error message if an error occurs.
*   **Input/Output Operations:**
    *   Sends requests to the OpenAI API (via `components.api_client.openai_responses_create`).
    *   Receives responses from the OpenAI API.
*   **Dependencies:**
    *   *Internal:*
        *   `components.api_client` (for interacting with the OpenAI API).
        *   `guardrail.prompts` (for the guardrails system prompt).
        *   `guardrail.config` (for settings).
    *   *External:*
        *   `pydantic` (for data validation).
        *   `streamlit` (for accessing session state).

### guardrail/config.py

*   **File Path:** `guardrail/config.py`
*   **Purpose:** This file defines the `Settings` class, which loads configuration settings from Streamlit secrets.
*   **Key Components:**
    *   `Settings`: Pydantic model for storing application settings.
*   **Data Structures:**
    *   `Settings`: Defines the structure of the application settings, including API keys, model names, and Supabase credentials.
*   **Algorithmic Details:** None.
*   **Error Handling Strategy:** None explicitly defined in this file.
*   **Input/Output Operations:**
    *   Reads settings from Streamlit secrets.
*   **Dependencies:**
    *   *External:* `streamlit` (for accessing secrets).
    *   `pydantic` (for data validation).

### guardrail/prompts.py

*   **File Path:** `guardrail/prompts.py`
*   **Purpose:** This file defines the system prompts used for the guardrail and agent LLMs.
*   **Key Components:**
    *   `guardrails_system_prompt`: The system prompt for the guardrail LLM.
    *   `agent_system_prompt`: The system prompt for the agent LLM.
*   **Data Structures:** None.
*   **Algorithmic Details:** None.
*   **Error Handling Strategy:** None.
*   **Input/Output Operations:**
    *   Reads the guardrail system prompt from `guardrail/prompts/guardrail_instructions.md`.
*   **Dependencies:** None.

### guardrail/prompts/guardrail_instructions.md

*   **File Path:** `guardrail/prompts/guardrail_instructions.md`
*   **Purpose:** This file contains the detailed instructions for the guardrail LLM, including the rules, evaluation principles, and JSON output schema.
*   **Key Components:**
    *   The entire file serves as the system prompt for the guardrail LLM.
*   **Data Structures:**
    *   Defines the JSON output schema for the guardrail LLM's responses.
*   **Algorithmic Details:** None.
*   **Error Handling Strategy:** None.
*   **Input/Output Operations:** None.
*   **Dependencies:** None.

### components/chat/chat_logic.py

*   **File Path:** `components/chat/chat_logic.py`
*   **Purpose:** This file contains the business logic for the chat application, including processing user messages, performing safety checks, and fetching agent responses.
*   **Key Components:**
    *   `process_user_message()`: Processes user messages, including safety checks and agent calls.
    *   `fetch_agent_response()`: Fetches the agent's response from the OpenAI API.
    *   `log_guardrail_interaction()`: Logs guardrail interactions to the Supabase database.
*   **Data Structures:** None explicitly defined in this file.
*   **Algorithmic Details:**
    *   The `process_user_message()` function orchestrates the entire conversation turn, including user input processing, safety checks, agent calls, and response display.
*   **Error Handling Strategy:** Uses `try...except` blocks to catch potential errors during Supabase initialization, agent calls, and guardrail checks. Displays error messages using `st.error()`.
*   **Input/Output Operations:**
    *   Interacts with the OpenAI API to fetch agent responses.
    *   Interacts with the Supabase database to log guardrail interactions.
*   **Dependencies:**
    *   *Internal:*
        *   `guardrail.config` (for settings).
        *   `guardrail.compliance_layer` (for performing safety checks).
        *   `components.api_client` (for interacting with the OpenAI API).
        *   `components.chat.session_management` (for session state management).
    *   *External:*
        *   `streamlit` (for accessing session state).
        *   `supabase` (for database interaction).

### components/chat/chat_ui.py

*   **File Path:** `components/chat/chat_ui.py`
*   **Purpose:** This file defines the UI elements for the chat application, including message display, debug information, sidebar setup, and user input capture.
*   **Key Components:**
    *   `display_messages()`: Renders chat messages with role-based formatting.
    *   `display_debug_expanders()`: Displays debug information in expanders and popovers.
    *   `setup_sidebar()`: Sets up the sidebar with controls and help information.
    *   `get_user_input()`: Captures user input from the chat interface.
*   **Data Structures:** None explicitly defined in this file.
*   **Algorithmic Details:** None.
*   **Error Handling Strategy:** None explicitly defined in this file.
*   **Input/Output Operations:**
    *   Displays messages in the chat interface.
    *   Captures user input from the chat interface.
*   **Dependencies:**
    *   *External:* `streamlit` (for building the UI).

### components/chat/session_management.py

*   **File Path:** `components/chat/session_management.py`
*   **Purpose:** This file provides utilities for managing the Streamlit session state, including initializing the state, resetting the state, and generating conversation IDs.
*   **Key Components:**
    *   `SessionDefaults`: Dataclass defining default values for session state.
    *   `reset_chat_session_state()`: Resets the chat session state to its default values.
    *   `init_chat_session_state()`: Initializes the chat session state with default values if it is not already initialized.
    *   `build_conversation_json()`: Constructs a JSON representation of the conversation.
    *   `format_conversation_context()`: Formats the conversation context into an XML-like structure.
*   **Data Structures:**
    *   `SessionDefaults`: Defines the structure of the session state, including messages, conversation ID, guardrail context, and other relevant information.
*   **Algorithmic Details:** None.
*   **Error Handling Strategy:** None explicitly defined in this file.
*   **Input/Output Operations:** None.
*   **Dependencies:**
    *   *Internal:* `guardrail.prompts` (for agent system prompt).
    *   *External:*
        *   `streamlit` (for managing session state).
        *   `dataclasses` (for defining the `SessionDefaults` dataclass).

## C. Interdependency Summary

The application's core logic resides in `pages/2_Chat.py`, which orchestrates the interaction between the user, the guardrail, and the agent. User input is first processed by the guardrail (implemented in `guardrail/compliance_layer.py`) to ensure compliance with safety rules. The guardrail uses a system prompt defined in `guardrail/prompts/guardrail_instructions.md` and interacts with the OpenAI API via `components/api_client.py`. If the user input is deemed safe, it is passed to the agent (also interacting with the OpenAI API via `components/api_client.py`) to generate a response. The agent's response is then checked by the guardrail before being displayed to the user. Session state is managed by `components/chat/session_management.py`, and the UI is built using `streamlit` and defined in `components/chat/chat_ui.py`. The application also logs interactions and feedback to a Supabase database.
