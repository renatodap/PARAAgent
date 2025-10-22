"""
LLM Provider Abstraction Layer
Handles routing LLM calls to appropriate providers (Groq, Anthropic) based on task type.
Optimized for cost: 67% savings by using Groq free tier where appropriate.
"""

from anthropic import Anthropic
from groq import Groq
from config import settings
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


class LLMProvider:
    """
    Unified interface for multiple LLM providers.
    Routes requests based on task type to optimize for cost and performance.
    """

    def __init__(self):
        # Initialize clients
        self.anthropic_client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)

        self.groq_client = None
        if settings.GROQ_API_KEY:
            self.groq_client = Groq(api_key=settings.GROQ_API_KEY)
        else:
            logger.warning("GROQ_API_KEY not set - falling back to Anthropic for all tasks")

        self.provider_map = settings.LLM_PROVIDER_MAP

    def get_completion(
        self,
        task_type: str,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = None,
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get completion from appropriate LLM provider based on task type.

        Args:
            task_type: Type of task (para_classification, reprioritization, etc.)
            prompt: User prompt
            max_tokens: Maximum tokens to generate
            temperature: Temperature for sampling (None = use provider default)
            system_prompt: Optional system prompt

        Returns:
            {
                "text": "completion text",
                "usage": {
                    "input_tokens": 100,
                    "output_tokens": 50,
                    "cost_usd": 0.00015
                },
                "provider": "groq|anthropic"
            }
        """

        provider = self.provider_map.get(task_type, 'anthropic')

        # Deterministic tasks should not reach here (handled in agents)
        if provider == 'deterministic':
            raise ValueError(f"Task type '{task_type}' should use deterministic code, not LLM")

        if provider == 'groq' and self.groq_client:
            return self._get_groq_completion(prompt, max_tokens, temperature, system_prompt)
        else:
            return self._get_anthropic_completion(prompt, max_tokens, temperature, system_prompt)

    def _get_groq_completion(
        self,
        prompt: str,
        max_tokens: int,
        temperature: Optional[float],
        system_prompt: Optional[str]
    ) -> Dict[str, Any]:
        """Get completion from Groq (Llama 3.3 70B)."""

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            response = self.groq_client.chat.completions.create(
                model=settings.GROQ_MODEL,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature if temperature is not None else settings.GROQ_TEMPERATURE
            )

            usage = response.usage
            input_cost = (usage.prompt_tokens / 1_000_000) * settings.GROQ_LLAMA_INPUT_COST
            output_cost = (usage.completion_tokens / 1_000_000) * settings.GROQ_LLAMA_OUTPUT_COST
            total_cost = round(input_cost + output_cost, 6)

            return {
                "text": response.choices[0].message.content,
                "usage": {
                    "input_tokens": usage.prompt_tokens,
                    "output_tokens": usage.completion_tokens,
                    "cost_usd": total_cost
                },
                "provider": "groq"
            }

        except Exception as e:
            logger.error(f"Groq API error: {str(e)}")
            # Fallback to Anthropic
            logger.info("Falling back to Anthropic due to Groq error")
            return self._get_anthropic_completion(prompt, max_tokens, temperature, system_prompt)

    def _get_anthropic_completion(
        self,
        prompt: str,
        max_tokens: int,
        temperature: Optional[float],
        system_prompt: Optional[str]
    ) -> Dict[str, Any]:
        """Get completion from Anthropic (Claude Haiku)."""

        try:
            kwargs = {
                "model": settings.CLAUDE_MODEL,
                "max_tokens": max_tokens,
                "temperature": temperature if temperature is not None else settings.CLAUDE_TEMPERATURE,
                "messages": [{"role": "user", "content": prompt}]
            }

            if system_prompt:
                kwargs["system"] = system_prompt

            response = self.anthropic_client.messages.create(**kwargs)

            usage = response.usage
            input_cost = (usage.input_tokens / 1_000_000) * settings.CLAUDE_HAIKU_INPUT_COST
            output_cost = (usage.output_tokens / 1_000_000) * settings.CLAUDE_HAIKU_OUTPUT_COST
            total_cost = round(input_cost + output_cost, 6)

            return {
                "text": response.content[0].text,
                "usage": {
                    "input_tokens": usage.input_tokens,
                    "output_tokens": usage.output_tokens,
                    "cost_usd": total_cost
                },
                "provider": "anthropic"
            }

        except Exception as e:
            logger.error(f"Anthropic API error: {str(e)}")
            raise

    def get_conversational_completion(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 2000,
        temperature: float = None,
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get completion for conversational interface.
        Always uses Anthropic for tool use capabilities.

        Args:
            messages: List of conversation messages [{role, content}, ...]
            max_tokens: Maximum tokens to generate
            temperature: Temperature for sampling
            system_prompt: Optional system prompt

        Returns:
            Same format as get_completion()
        """

        try:
            kwargs = {
                "model": settings.CLAUDE_MODEL,
                "max_tokens": max_tokens,
                "temperature": temperature if temperature is not None else settings.CLAUDE_TEMPERATURE,
                "messages": messages
            }

            if system_prompt:
                kwargs["system"] = system_prompt

            response = self.anthropic_client.messages.create(**kwargs)

            usage = response.usage
            input_cost = (usage.input_tokens / 1_000_000) * settings.CLAUDE_HAIKU_INPUT_COST
            output_cost = (usage.output_tokens / 1_000_000) * settings.CLAUDE_HAIKU_OUTPUT_COST
            total_cost = round(input_cost + output_cost, 6)

            return {
                "text": response.content[0].text,
                "usage": {
                    "input_tokens": usage.input_tokens,
                    "output_tokens": usage.output_tokens,
                    "cost_usd": total_cost
                },
                "provider": "anthropic",
                "response": response  # Include full response for tool use parsing
            }

        except Exception as e:
            logger.error(f"Anthropic conversation API error: {str(e)}")
            raise


# Global singleton instance
llm_provider = LLMProvider()
