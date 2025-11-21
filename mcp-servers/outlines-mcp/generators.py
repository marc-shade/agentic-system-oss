"""Constrained generation utilities using Outlines."""
import json
import re
from typing import Any, Dict, List, Optional, Type, Union
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)

# Outlines imports with graceful fallback
try:
    import outlines
    from outlines import models, generate
    OUTLINES_AVAILABLE = True
except ImportError:
    OUTLINES_AVAILABLE = False
    logger.warning("Outlines not installed, using fallback generators")


class ConstrainedGenerator:
    """Unified interface for constrained generation."""

    def __init__(self, model_name: str = "mistral", backend: str = "ollama"):
        self.model_name = model_name
        self.backend = backend
        self._model = None

    async def _get_model(self):
        """Lazy load model."""
        if self._model is None and OUTLINES_AVAILABLE:
            if self.backend == "ollama":
                # Outlines supports Ollama through transformers interface
                self._model = models.transformers(self.model_name)
            elif self.backend == "openai":
                self._model = models.openai(self.model_name)
        return self._model

    async def generate_json(
        self,
        prompt: str,
        schema: Union[Type[BaseModel], Dict[str, Any]],
        temperature: float = 0.3,
    ) -> Dict[str, Any]:
        """Generate guaranteed valid JSON matching schema."""
        if OUTLINES_AVAILABLE:
            model = await self._get_model()
            if isinstance(schema, type) and issubclass(schema, BaseModel):
                generator = generate.json(model, schema)
            else:
                generator = generate.json(model, schema)
            result = generator(prompt)
            if isinstance(result, BaseModel):
                return result.model_dump()
            return result
        else:
            # Fallback: use Ollama directly with JSON mode
            from .ollama_integration import get_ollama_client
            client = get_ollama_client()

            if isinstance(schema, type) and issubclass(schema, BaseModel):
                schema_dict = schema.model_json_schema()
            else:
                schema_dict = schema

            return await client.generate_with_schema(
                model=self.model_name,
                prompt=prompt,
                schema=schema_dict,
                temperature=temperature
            )

    async def generate_choice(
        self,
        prompt: str,
        choices: List[str],
    ) -> str:
        """Generate output constrained to specific choices."""
        if OUTLINES_AVAILABLE:
            model = await self._get_model()
            generator = generate.choice(model, choices)
            return generator(prompt)
        else:
            # Fallback: instruct model to choose
            from .ollama_integration import get_ollama_client
            client = get_ollama_client()

            choice_prompt = f"""{prompt}

You must respond with exactly one of these options: {', '.join(choices)}
Output only the chosen option, nothing else."""

            response = await client.generate(
                model=self.model_name,
                prompt=choice_prompt,
                temperature=0.1,
                max_tokens=50
            )

            # Find best match
            response = response.strip()
            for choice in choices:
                if choice.lower() in response.lower():
                    return choice
            return choices[0]  # Default to first choice

    async def generate_regex(
        self,
        prompt: str,
        pattern: str,
    ) -> str:
        """Generate output matching regex pattern."""
        if OUTLINES_AVAILABLE:
            model = await self._get_model()
            generator = generate.regex(model, pattern)
            return generator(prompt)
        else:
            # Fallback: generate and validate
            from .ollama_integration import get_ollama_client
            client = get_ollama_client()

            regex_prompt = f"""{prompt}

Your response must match this regex pattern: {pattern}
Output only the matching text, nothing else."""

            response = await client.generate(
                model=self.model_name,
                prompt=regex_prompt,
                temperature=0.3,
                max_tokens=256
            )

            # Try to extract matching portion
            match = re.search(pattern, response)
            if match:
                return match.group()
            return response.strip()

    async def generate_grammar(
        self,
        prompt: str,
        grammar: str,
    ) -> str:
        """Generate output conforming to context-free grammar."""
        if OUTLINES_AVAILABLE:
            model = await self._get_model()
            generator = generate.cfg(model, grammar)
            return generator(prompt)
        else:
            # Fallback: basic generation with grammar hint
            from .ollama_integration import get_ollama_client
            client = get_ollama_client()

            grammar_prompt = f"""{prompt}

Your response must follow this grammar:
{grammar}

Generate valid output according to the grammar."""

            return await client.generate(
                model=self.model_name,
                prompt=grammar_prompt,
                temperature=0.3
            )

    async def generate_code(
        self,
        prompt: str,
        language: str = "python",
    ) -> str:
        """Generate syntactically valid code."""
        # Use regex pattern for basic code structure
        code_patterns = {
            "python": r"(def |class |import |from |if |for |while |try |with |async |@|\w+ = )[\s\S]*",
            "javascript": r"(function |const |let |var |class |import |export |if |for |while |try |async )[\s\S]*",
            "typescript": r"(function |const |let |var |class |import |export |interface |type |if |for |while |try |async )[\s\S]*",
        }

        pattern = code_patterns.get(language, r"[\s\S]+")

        code_prompt = f"""Generate {language} code for the following:
{prompt}

Output only the code, no explanations or markdown."""

        if OUTLINES_AVAILABLE:
            return await self.generate_regex(code_prompt, pattern)
        else:
            from .ollama_integration import get_ollama_client
            client = get_ollama_client()

            response = await client.generate(
                model=self.model_name,
                prompt=code_prompt,
                temperature=0.3
            )

            # Clean up response
            response = response.strip()
            if response.startswith("```"):
                lines = response.split("\n")
                lines = lines[1:-1] if lines[-1] == "```" else lines[1:]
                response = "\n".join(lines)

            return response


# Common regex patterns
PATTERNS = {
    "email": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
    "phone": r"\+?[0-9]{1,3}[-.\s]?\(?[0-9]{1,4}\)?[-.\s]?[0-9]{1,4}[-.\s]?[0-9]{1,9}",
    "url": r"https?://[^\s]+",
    "date_iso": r"\d{4}-\d{2}-\d{2}",
    "time_24h": r"[0-2][0-9]:[0-5][0-9](:[0-5][0-9])?",
    "uuid": r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
    "semantic_version": r"\d+\.\d+\.\d+(-[a-zA-Z0-9]+)?",
    "ip_address": r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}",
}


# Common grammars
GRAMMARS = {
    "arithmetic": """
        ?start: expr
        ?expr: term (("+"|"-") term)*
        ?term: factor (("*"|"/") factor)*
        ?factor: NUMBER | "(" expr ")"
        NUMBER: /[0-9]+/
    """,
    "json_path": """
        ?start: path
        path: "$" segment*
        segment: "." NAME | "[" INDEX "]" | "['" NAME "']"
        NAME: /[a-zA-Z_][a-zA-Z0-9_]*/
        INDEX: /[0-9]+/
    """,
}


# Default generator instance
_default_generator: Optional[ConstrainedGenerator] = None


def get_generator(model_name: str = "mistral") -> ConstrainedGenerator:
    """Get or create default generator."""
    global _default_generator
    if _default_generator is None or _default_generator.model_name != model_name:
        _default_generator = ConstrainedGenerator(model_name=model_name)
    return _default_generator
