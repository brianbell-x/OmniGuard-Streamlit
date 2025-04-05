"""
Module: api_client.py
Description:
    Provides utility functions for OpenAI client interactions, including API key retrieval and model parameter configuration.
"""

import streamlit as st
import logging
from groq import Groq
from openai import OpenAI
from typing import Optional
import httpx
logger = logging.getLogger(__name__)

def get_api_key() -> str:
    """
    Retrieve the API key from Streamlit secrets.

    Raises:
        ValueError: If the API key is not available.
    Returns:
        str: The retrieved API key.
    """
    api_key = st.secrets.get("API_KEY")
    if not api_key:
        st.error("API key not configured. Notify Brian")
        raise ValueError("API key not available")
    return api_key

def get_openai_client() -> OpenAI: # Not Used
    """Initialize and return an OpenAI client with the configured API key."""
    return OpenAI(api_key=get_api_key(), http_client = httpx.Client(verify=False))

def get_groq_client() -> Groq:
    """Initialize and return a Groq client with the configured API key."""
    return Groq(api_key=get_api_key(), http_client = httpx.Client(verify=False))
