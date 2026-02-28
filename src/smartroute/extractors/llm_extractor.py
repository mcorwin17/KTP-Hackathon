"""LLM-based extraction for ambiguous fields."""

import json
import os
from abc import ABC, abstractmethod
from typing import Any, Optional


class LLMClient(ABC):
    """Abstract interface for LLM providers."""

    @abstractmethod
    def extract_json(self, prompt: str, schema: dict) -> dict:
        """
        Send prompt to LLM and get structured JSON response.

        Args:
            prompt: The extraction prompt with text to analyze
            schema: JSON schema the response should conform to

        Returns:
            Parsed JSON dictionary from LLM response
        """
        pass


class OpenAIClient(LLMClient):
    """OpenAI API implementation of LLMClient."""

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini"):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.model = model
        self._client = None

    @property
    def client(self):
        if self._client is None:
            try:
                from openai import OpenAI
                self._client = OpenAI(api_key=self.api_key)
            except ImportError:
                raise ImportError("openai package required. Install with: pip install openai")
        return self._client

    def extract_json(self, prompt: str, schema: dict) -> dict:
        """Extract structured JSON using OpenAI API."""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a data extraction assistant. Extract information from the provided text and return ONLY valid JSON matching the specified schema. Do not include any explanation or markdown formatting."
                },
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
        )

        content = response.choices[0].message.content
        return json.loads(content)


class AnthropicClient(LLMClient):
    """Anthropic Claude API implementation of LLMClient."""

    def __init__(self, api_key: Optional[str] = None, model: str = "claude-3-haiku-20240307"):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.model = model
        self._client = None

    @property
    def client(self):
        if self._client is None:
            try:
                from anthropic import Anthropic
                self._client = Anthropic(api_key=self.api_key)
            except ImportError:
                raise ImportError("anthropic package required. Install with: pip install anthropic")
        return self._client

    def extract_json(self, prompt: str, schema: dict) -> dict:
        """Extract structured JSON using Anthropic API."""
        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            messages=[
                {"role": "user", "content": prompt}
            ],
            system="You are a data extraction assistant. Extract information from the provided text and return ONLY valid JSON matching the specified schema. Do not include any explanation or markdown formatting.",
        )

        content = response.content[0].text
        # Try to extract JSON from response
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # Try to find JSON in response
            import re
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                return json.loads(json_match.group())
            raise


class MockLLMClient(LLMClient):
    """Mock LLM client for testing without API calls."""

    def __init__(self, responses: Optional[dict] = None):
        self.responses = responses or {}
        self.call_count = 0
        self.last_prompt = None

    def extract_json(self, prompt: str, schema: dict) -> dict:
        """Return mock response."""
        self.call_count += 1
        self.last_prompt = prompt

        # Return configured response or empty dict
        return self.responses.get("default", {})


class LLMExtractor:
    """Extract fields using LLM for ambiguous cases."""

    EXTRACTION_PROMPT_TEMPLATE = '''Extract information from the following inspector communication text.

TEXT TO ANALYZE:
{text}

{hints_section}

FIELD DEFINITIONS:
- permit_number: The permit or application number
- permit_type: Type of permit (electrical, plumbing, building, etc.)
- inspection_type: Type of inspection performed
- inspection_date: Date inspection occurred (YYYY-MM-DD format)
- scheduled_date: Date inspection is scheduled (YYYY-MM-DD format)
- status: Inspection status - must be one of: pass, fail, partial, unknown
- release_type: Type of release (e.g., Electrical Power Release)
- release_date: Date of release (YYYY-MM-DD format)
- structure_type: Type of structure (residential, commercial, etc.)
- reason_for_release: Reason the release was granted
- address_full: Complete address
- street_number: House/building number
- street_name: Street name
- city: City name
- state: State (default SC)
- zip: ZIP code
- subdivision: Subdivision name
- lot_unit: Lot or unit number
- inspector_name: Name of inspector
- inspector_email: Inspector email
- inspector_phone: Inspector phone
- jurisdiction_name: Name of jurisdiction/municipality
- county: County name

OUTPUT REQUIREMENTS:
- Return ONLY valid JSON
- Use null for fields that cannot be determined
- Use the exact field names shown above
- Dates must be in YYYY-MM-DD format
- Status must be one of: pass, fail, partial, unknown

Return the extracted data as JSON:'''

    def __init__(self, client: LLMClient):
        """
        Initialize LLM extractor.

        Args:
            client: An LLMClient implementation (OpenAI, Anthropic, Mock, etc.)
        """
        self.client = client

    def extract(
        self,
        clean_text: str,
        attachment_text: Optional[str] = None,
        hints: Optional[dict] = None
    ) -> dict:
        """
        Extract fields using LLM.

        Args:
            clean_text: Cleaned text to analyze
            attachment_text: Optional attachment text
            hints: Optional dict of regex-extracted hints to guide LLM

        Returns:
            Dictionary of extracted fields
        """
        # Combine text
        text = clean_text
        if attachment_text:
            text += "\n\n--- ATTACHMENT TEXT ---\n" + attachment_text

        # Build hints section
        hints_section = ""
        if hints:
            hints_section = "ALREADY EXTRACTED (use as hints, override only with strong evidence):\n"
            hints_section += json.dumps(hints, indent=2)

        prompt = self.EXTRACTION_PROMPT_TEMPLATE.format(
            text=text,
            hints_section=hints_section
        )

        # Get extraction schema (simplified for LLM)
        schema = self._get_extraction_schema()

        try:
            result = self.client.extract_json(prompt, schema)
            return result
        except Exception as e:
            # Return empty dict on error, let pipeline handle gracefully
            return {"_error": str(e)}

    def _get_extraction_schema(self) -> dict:
        """Get simplified schema for LLM extraction."""
        return {
            "type": "object",
            "properties": {
                "permit_number": {"type": ["string", "null"]},
                "permit_type": {"type": ["string", "null"]},
                "inspection_type": {"type": ["string", "null"]},
                "inspection_date": {"type": ["string", "null"]},
                "scheduled_date": {"type": ["string", "null"]},
                "status": {"type": ["string", "null"], "enum": ["pass", "fail", "partial", "unknown", None]},
                "release_type": {"type": ["string", "null"]},
                "release_date": {"type": ["string", "null"]},
                "structure_type": {"type": ["string", "null"]},
                "reason_for_release": {"type": ["string", "null"]},
                "address_full": {"type": ["string", "null"]},
                "street_number": {"type": ["string", "null"]},
                "street_name": {"type": ["string", "null"]},
                "city": {"type": ["string", "null"]},
                "state": {"type": ["string", "null"]},
                "zip": {"type": ["string", "null"]},
                "subdivision": {"type": ["string", "null"]},
                "lot_unit": {"type": ["string", "null"]},
                "inspector_name": {"type": ["string", "null"]},
                "inspector_email": {"type": ["string", "null"]},
                "inspector_phone": {"type": ["string", "null"]},
                "jurisdiction_name": {"type": ["string", "null"]},
                "county": {"type": ["string", "null"]},
            }
        }
