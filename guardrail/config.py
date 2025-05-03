import streamlit as st
from pydantic import BaseModel, Field

secrets = st.secrets


class Settings(BaseModel):
    openai_api_key: str = secrets.OPENAI_API_KEY
    supabase_url: str = secrets.supabase.SUPABASE_URL
    supabase_key: str = secrets.supabase.SUPABASE_KEY
    service_role: str = secrets.supabase.SERVICE_ROLE
    agent_model: str = secrets.models.AGENT_MODEL
    safety_model: str = secrets.models.SAFETY_MODEL


settings = Settings()
