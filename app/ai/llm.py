"""Pluggable LLM provider. Default = Anthropic Claude; OpenAI/Groq swap in via config.

Everything AI-related depends on `get_chat_model()`, never on a provider directly,
so switching providers is a one-line config change (LLM_PROVIDER env var).
"""
from app.core.config import settings


def get_chat_model(streaming: bool = False):
    """Return a LangChain chat model for the configured provider."""
    provider = settings.llm_provider.lower()

    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(
            model=settings.anthropic_model,   # e.g. claude-sonnet-5 / claude-opus-4-8
            api_key=settings.anthropic_api_key,
            streaming=streaming,
        )
    if provider == "openai":
        from langchain_openai import ChatOpenAI  # add langchain-openai to deps if used

        return ChatOpenAI(api_key=settings.openai_api_key, streaming=streaming)
    if provider == "groq":
        from langchain_groq import ChatGroq  # add langchain-groq to deps if used

        return ChatGroq(api_key=settings.groq_api_key, streaming=streaming)

    raise ValueError(f"Unsupported LLM_PROVIDER: {settings.llm_provider}")
