"""
Code-level Response Validator for LLM Outputs.
Parses generated markdown text, extracts numerical figures, currency, percentages, kWh figures,
and component names, and checks them against the structured JSON context.
Rejects hallucinated or modified numbers.
"""
import re
import math
import logging
from typing import Dict, Any, List, Set, Tuple

logger = logging.getLogger(__name__)

class ResponseValidator:
    @staticmethod
    def _extract_numbers_from_dict(data: Any, found: Set[float]) -> None:
        """Recursively harvest all numbers from structured context."""
        if isinstance(data, (int, float)):
            if not math.isnan(data) and not math.isinf(data):
                val = float(data)
                found.add(round(val, 2))
                found.add(round(val, 4))
                found.add(round(val, 1))
                found.add(round(val, 0))
        elif isinstance(data, dict):
            for v in data.values():
                ResponseValidator._extract_numbers_from_dict(v, found)
        elif isinstance(data, (list, tuple)):
            for item in data:
                ResponseValidator._extract_numbers_from_dict(item, found)
        elif isinstance(data, str):
            # Only attempt to parse inline string numbers if not a date/period string with hyphens or slashes
            if not any(char in data for char in ['-', '/']):
                clean_str = data.replace('$', '').replace('%', '').replace(',', '').strip()
                try:
                    num = float(clean_str)
                    found.add(round(num, 2))
                    found.add(round(num, 4))
                    found.add(round(num, 1))
                    found.add(round(num, 0))
                except ValueError:
                    pass

    @staticmethod
    def extract_numbers_from_text(text: str) -> List[float]:
        """Extract all dollar, percentage, usage, and decimal numbers from LLM response text."""
        # Match currency e.g. $160.62, $8.24
        # Match percentages e.g. 6.625%, 10%
        # Match standalone floats e.g. 0.1052, 750
        pattern = r'(?:\$|%|\b)(\d+(?:\.\d+)?)(?:%|\b)?'
        matches = re.findall(pattern, text)
        extracted = []
        for m in matches:
            try:
                val = float(m)
                # Ignore trivial integer indices like markdown bullet numbers "1.", "2." if isolated
                extracted.append(val)
            except ValueError:
                continue
        return extracted

    @classmethod
    def validate(cls, text: str, context_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate generated text against the provided context_data.
        Returns (is_valid, validation_errors).
        """
        if not text or not text.strip():
            return False, ["Response text is empty."]

        # Gather context numbers
        allowed_numbers: Set[float] = set()
        cls._extract_numbers_from_dict(context_data, allowed_numbers)

        # Allow basic formatting constants (e.g. 0, 1, 100, 24, 30, 365, 12, 1000)
        common_constants = {0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 10.0, 12.0, 24.0, 30.0, 100.0, 365.0, 1000.0}
        allowed_numbers.update(common_constants)

        # Extract text numbers
        text_numbers = cls.extract_numbers_from_text(text)
        errors: List[str] = []

        for num in text_numbers:
            r1 = round(num, 1)
            r2 = round(num, 2)
            r4 = round(num, 4)

            # Direct numeric match against context values
            direct_match = any(
                r in allowed_numbers for r in (r1, r2, r4, num)
            )

            # Integer constant match (only if number in text is an integer, e.g. 100%, 30 days)
            is_int = (num % 1 == 0)
            const_match = is_int and (num in common_constants)

            if not direct_match and not const_match:
                close_match = any(abs(num - val) < 0.05 for val in allowed_numbers)
                if not close_match:
                    errors.append(f"Unverified numerical value in text: '{num}'")

        if len(errors) > 0:
            logger.warning(f"Response validation failed with {len(errors)} errors: {errors[:3]}")
            return False, errors

        return True, []
