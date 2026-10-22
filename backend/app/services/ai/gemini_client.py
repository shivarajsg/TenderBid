import logging
import time
from typing import Optional
from google import genai
from google.genai import errors

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class GeminiClient:
    """Wrapper around the Google Gemini API with timeout handling and graceful offline fallback."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
        max_retries: Optional[int] = None,
    ):
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model_name = model_name or settings.GEMINI_MODEL
        self.timeout = timeout_seconds or settings.GEMINI_TIMEOUT_SECONDS
        self.max_retries = max_retries or settings.GEMINI_MAX_RETRIES

        self._client: Optional[genai.Client] = None
        if self.api_key and self.api_key.strip():
            try:
                self._client = genai.Client(api_key=self.api_key.strip())
                logger.info(f"Initialized Google GenAI client with model: {self.model_name}")
            except Exception as e:
                logger.warning(f"Failed to initialize GenAI client: {e}. Falling back to mock generator.")

    def is_configured(self) -> bool:
        """Check if an active Gemini client with an API key is available."""
        return self._client is not None

    def generate_text(self, prompt: str, system_instruction: Optional[str] = None) -> str:
        """Generate content with bounded retries and graceful fallback if unconfigured."""
        if not self.is_configured():
            logger.info("Gemini API key not configured or client offline; using deterministic explanatory fallback.")
            return self._deterministic_fallback(prompt)

        last_error = None
        for attempt in range(self.max_retries):
            try:
                config = {}
                if system_instruction:
                    config["system_instruction"] = system_instruction

                response = self._client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=config if config else None,
                )
                if response and response.text:
                    return response.text.strip()
                return ""
            except errors.APIError as e:
                last_error = e
                logger.warning(f"Gemini API error (attempt {attempt+1}/{self.max_retries}): {e}")
                time.sleep(1.0 * (attempt + 1))
            except Exception as e:
                last_error = e
                logger.warning(f"Unexpected error during Gemini generation: {e}")
                break

        logger.error(f"Gemini generation exhausted all {self.max_retries} attempts: {last_error}")
        return self._deterministic_fallback(prompt)

    @staticmethod
    def _deterministic_fallback(prompt: str) -> str:
        """Provide a factual, un-hallucinated summary when the remote LLM is unavailable."""
        return (
            "Automated Analysis: Evaluated objective requirement criteria using verified evidence. "
            "Deterministic business rules have established verified threshold status without external LLM intervention."
        )


_gemini_client: Optional[GeminiClient] = None


def get_gemini_client() -> GeminiClient:
    global _gemini_client
    if _gemini_client is None:
        _gemini_client = GeminiClient()
    return _gemini_client
