"""
Generic LLM Provider - Supports Multiple LLMs

Supports:
- OpenAI (GPT-4, GPT-3.5, GPT-4o-mini)
- Azure OpenAI (GPT-4, GPT-3.5, GPT-4o-mini on Azure)
- Anthropic Claude (Claude 3 Opus, Sonnet, Haiku)
- Google Gemini (Gemini 2.5 Pro, 1.5 Pro, 1.5 Flash)
- Ollama (Local models: qwen3, llama3, mistral, , etc.)
"""

from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI, AzureChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.chat_models import ChatOllama
from pydantic import SecretStr
import os
from enum import Enum


# ============================================================================
# LLM PROVIDER ENUM
# ============================================================================

class LLMProvider(str, Enum):
    """Supported LLM providers"""
    OPENAI = "openai"
    AZURE_OPENAI = "azure"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"
    OLLAMA = "ollama"

# ============================================================================
# LLM FACTORY
# ============================================================================

class LLMFactory:
    """
    Factory class to create LLM instances based on provider
    """

    @staticmethod
    def create_llm(
        provider: str = None,
        model: str = None,
        temperature: float = 0.3,
        max_tokens: int = 1000,
        api_key: str = None,
        base_url: str = None,
        **kwargs
    ) -> BaseChatModel:
        """
        Create an LLM instance based on provider

        Args:
            provider: LLM provider (openai, azure, anthropic, gemini, ollama)
            model: Model name
            temperature: Temperature setting (0-1)
            max_tokens: Maximum tokens in response
            api_key: API key for the provider
            base_url: Base URL for API (for Ollama or custom endpoints)
            **kwargs: Additional provider-specific parameters

        Returns:
            Configured LLM instance
        """
        # Get provider from environment if not specified
        if provider is None:
            provider = os.getenv("LLM_PROVIDER", "openai").lower()

        provider = provider.lower()

        # Create LLM based on provider
        if provider == LLMProvider.OPENAI:
            return LLMFactory._create_openai(model, temperature, max_tokens, api_key, **kwargs)

        elif provider == LLMProvider.AZURE_OPENAI:
            return LLMFactory._create_azure_openai(model, temperature, max_tokens, api_key, **kwargs)

        elif provider == LLMProvider.ANTHROPIC:
            return LLMFactory._create_anthropic(model, temperature, max_tokens, api_key, **kwargs)

        elif provider == LLMProvider.GEMINI:
            return LLMFactory._create_gemini(model, temperature, max_tokens, api_key, **kwargs)

        elif provider == LLMProvider.OLLAMA:
            return LLMFactory._create_ollama(model, temperature, max_tokens, base_url, **kwargs)

        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")

    @staticmethod
    def _create_openai(
        model: str = None,
        temperature: float = 0.3,
        max_tokens: int = 1000,
        api_key: str = None,
        **kwargs
    ) -> ChatOpenAI:
        """Create OpenAI LLM instance"""
        model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        api_key = api_key or os.getenv("OPENAI_API_KEY")

        llm_kwargs = {
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if api_key:
            llm_kwargs["api_key"] = SecretStr(api_key)

        # Add any additional kwargs
        llm_kwargs.update(kwargs)

        return ChatOpenAI(**llm_kwargs)

    @staticmethod
    def _create_azure_openai(
        model: str = None,
        temperature: float = 0.3,
        max_tokens: int = 1000,
        api_key: str = None,
        **kwargs
    ) -> AzureChatOpenAI:
        """Create Azure OpenAI LLM instance"""
        # Azure OpenAI requires specific configuration
        model = model or os.getenv("AZURE_OPENAI_MODEL", "gpt-4o-mini")
        api_key = api_key or os.getenv("AZURE_OPENAI_API_KEY")

        # Required Azure parameters
        azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        azure_deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", model)
        api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")

        if not azure_endpoint:
            raise ValueError(
                "AZURE_OPENAI_ENDPOINT is required for Azure OpenAI. "
                "Example: https://your-resource.openai.azure.com/"
            )

        llm_kwargs = {
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "azure_endpoint": azure_endpoint,
            "azure_deployment": azure_deployment,
            "api_version": api_version,
        }

        if api_key:
            llm_kwargs["api_key"] = SecretStr(api_key)

        # Add any additional kwargs
        llm_kwargs.update(kwargs)

        return AzureChatOpenAI(**llm_kwargs)

    @staticmethod
    def _create_anthropic(
        model: str = None,
        temperature: float = 0.3,
        max_tokens: int = 1000,
        api_key: str = None,
        **kwargs
    ) -> ChatAnthropic:
        """Create Anthropic Claude LLM instance"""
        model = model or os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")
        api_key = api_key or os.getenv("ANTHROPIC_API_KEY")

        llm_kwargs = {
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if api_key:
            llm_kwargs["api_key"] = SecretStr(api_key)

        # Add any additional kwargs
        llm_kwargs.update(kwargs)

        return ChatAnthropic(**llm_kwargs)

    @staticmethod
    def _create_gemini(
        model: str = None,
        temperature: float = 0.3,
        max_tokens: int = 1000,
        api_key: str = None,
        **kwargs
    ) -> ChatGoogleGenerativeAI:
        """Create Google Gemini LLM instance"""
        model = model or os.getenv("GEMINI_MODEL", "gemini-2.5-pro")
        api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

        llm_kwargs = {
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if api_key:
            llm_kwargs["google_api_key"] = api_key

        # Add any additional kwargs
        llm_kwargs.update(kwargs)

        return ChatGoogleGenerativeAI(**llm_kwargs)

    @staticmethod
    def _create_ollama(
        model: str = None,
        temperature: float = 0.3,
        max_tokens: int = 1000,
        base_url: str = None,
        **kwargs
    ) -> ChatOllama:
        """Create Ollama (local) LLM instance"""
        model = model or os.getenv("OLLAMA_MODEL", "qwen3:8b")
        base_url = base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

        llm_kwargs = {
            "model": model,
            "temperature": temperature,
            "base_url": base_url,
        }

        # Add any additional kwargs
        llm_kwargs.update(kwargs)

        return ChatOllama(**llm_kwargs)


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def create_extraction_llm(
    provider: str = None,
    model: str = None,
    api_key: str = None
) -> BaseChatModel:
    """
    Create LLM optimized for data extraction

    Args:
        provider: LLM provider (openai, anthropic, ollama, mock)
        model: Specific model name (optional)
        api_key: API key (optional, uses env var if not provided)
    """
    return LLMFactory.create_llm(
        provider=provider,
        model=model,
        temperature=0.2,
        max_tokens=500,
        api_key=api_key
    )


def create_job_skills_llm(
    provider: str = None,
    model: str = None,
    api_key: str = None
) -> BaseChatModel:
    """
    Create LLM optimized for job skills extraction

    Args:
        provider: LLM provider (openai, anthropic, ollama, mock)
        model: Specific model name (optional)
        api_key: API key (optional, uses env var if not provided)
    """
    return LLMFactory.create_llm(
        provider=provider,
        model=model,
        temperature=0.0,
        max_tokens=600,
        api_key=api_key
    )


def create_summary_llm(
    provider: str = None,
    model: str = None,
    api_key: str = None
) -> BaseChatModel:
    """
    Create LLM optimized for summarization

    Args:
        provider: LLM provider (openai, anthropic, ollama, mock)
        model: Specific model name (optional)
        api_key: API key (optional, uses env var if not provided)
    """
    return LLMFactory.create_llm(
        provider=provider,
        model=model,
        temperature=0.5,
        max_tokens=300,
        api_key=api_key
    )


def create_evaluation_llm(
    provider: str = None,
    model: str = None,
    api_key: str = None
) -> BaseChatModel:
    """
    Create LLM optimized for evaluation

    Args:
        provider: LLM provider (openai, anthropic, ollama, mock)
        model: Specific model name (optional)
        api_key: API key (optional, uses env var if not provided)
    """
    return LLMFactory.create_llm(
        provider=provider,
        model=model,
        temperature=0.4,
        max_tokens=600,
        api_key=api_key
    )


# ============================================================================
# USAGE EXAMPLES
# ============================================================================

"""
Example 1: Using OpenAI (Default)
----------------------------------
llm = create_summary_llm()
# or
llm = create_summary_llm(provider="openai", model="gpt-4")


Example 2: Using Azure OpenAI
------------------------------
llm = create_summary_llm(
    provider="azure",
    model="gpt-4o-mini"
)

# Environment variables required:
# AZURE_OPENAI_API_KEY=your-azure-api-key
# AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
# AZURE_OPENAI_DEPLOYMENT=gpt-4o-mini-deployment
# AZURE_OPENAI_API_VERSION=2024-02-15-preview


Example 3: Using Anthropic Claude
----------------------------------
llm = create_summary_llm(
    provider="anthropic",
    model="claude-3-5-sonnet-20241022",
    api_key="your-anthropic-key"
)


Example 4: Using Google Gemini
-------------------------------
llm = create_summary_llm(
    provider="gemini",
    model="gemini-2.5-pro",
    api_key="your-google-api-key"
)


Example 5: Using Ollama (Local, Free)
--------------------------------------
llm = create_summary_llm(
    provider="ollama",
    model="qwen3:8b"
)


Example 6: Using Environment Variables
---------------------------------------
# For Azure OpenAI, set in .env:
# LLM_PROVIDER=azure
# AZURE_OPENAI_API_KEY=your-key
# AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
# AZURE_OPENAI_DEPLOYMENT=your-deployment-name
# AZURE_OPENAI_MODEL=gpt-4o-mini

llm = create_summary_llm()  # Automatically uses env vars


Example 7: Custom Configuration
--------------------------------
llm = LLMFactory.create_llm(
    provider="azure",
    model="gpt-4",
    temperature=0.7,
    max_tokens=2000
)
"""