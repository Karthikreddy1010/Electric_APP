"""
Programmatic Claim & Evidence Validator (3-Layer Architecture).
Validates generated LLM responses against approved EvidenceObject.
Layer 1: Numeric Extractor
Layer 2: Entity/Scope Extractor
Layer 3: Claim/Evidence Matcher (Direct match + Arithmetic derivation with float tolerance)
"""
import re
import math
import logging
from typing import Dict, Any, List, Set, Tuple
from ai.schemas import EvidenceObject, ClaimItem, CalculationItem

logger = logging.getLogger(__name__)

# Floating point tolerance for arithmetic derivations
FLOAT_TOLERANCE = 1e-2


class ProgrammaticClaimValidator:
    """
    Programmatic 3-Layer Critic verifying generated LLM natural language text against evidence.
    """

    @staticmethod
    def extract_numbers(text: str) -> List[float]:
        """Layer 1: Numeric Extractor. Extracts meaningful numeric claims, filtering out years, list indexes, and reference IDs."""
        # Strip out numbered list prefixes like "1. ", "2. ", "1) ", "2) "
        cleaned_text = re.sub(r'(?:^|\n|\s)\d+[\.\)]\s+', ' ', text)
        # Strip out times like "10 PM", "8 AM", "2:00"
        cleaned_text = re.sub(r'\b\d{1,2}(?::\d{2})?\s*(?:AM|PM|am|pm)\b', ' ', cleaned_text)

        # Find currency amounts, percentages, kWh, cents/kWh, and raw numbers
        raw_matches = re.findall(r'[\$\s]?(\d+(?:\.\d+)?)\s*(?:%|kWh|cents\/kWh|\b)?', cleaned_text)
        numbers = []
        for m in raw_matches:
            try:
                val = float(m)
                # Ignore small formatting integers (1 to 10) unless preceded by $ or followed by % / kWh in original
                if val.is_integer() and 1 <= val <= 10:
                    if not re.search(r'[\$]\s*' + re.escape(m) + r'\b|\b' + re.escape(m) + r'\s*(?:%|kWh|cents)', text):
                        continue
                # Filter out year numbers (2020-2030) and EIA form reference numbers
                if (2020 <= val <= 2030) or val in [861.0, 923.0, 930.0]:
                    continue
                numbers.append(val)
            except ValueError:
                pass
        return numbers

    @staticmethod
    def extract_entities(text: str) -> Dict[str, Set[str]]:
        """Layer 2: Entity / Scope Extractor."""
        text_upper = text.upper()
        states = set()
        for st in ["NJ", "TX", "CA", "NY", "PA", "FL", "MA", "WY"]:
            if re.search(r'\b' + st + r'\b', text_upper):
                states.add(st)

        years = set(re.findall(r'\b(202[0-9])\b', text))
        return {
            "states": states,
            "years": years
        }

    @classmethod
    def validate_response(cls, generated_text: str, evidence: EvidenceObject) -> Tuple[bool, str, int]:
        """
        Layer 3: Claim/Evidence Matcher.
        Returns:
            (is_valid: bool, sanitized_or_original_text: str, unverified_blocked_count: int)
        """
        if not evidence.claims and not evidence.calculations and not evidence.external_sources:
            # If no evidence was retrieved, text must not make unverified numerical claims
            numbers = cls.extract_numbers(generated_text)
            if numbers:
                logger.warning(f"Blocking response with {len(numbers)} numerical claims when no evidence was retrieved.")
                fallback = "I couldn't verify this information from available authoritative data sources, so I won't provide an unverified estimate."
                return False, fallback, len(numbers)
            return True, generated_text, 0

        # Collect approved evidence numbers and arithmetic derivations
        approved_numbers: Set[float] = set()

        # Direct claim numbers
        for c in evidence.claims:
            if c.numeric_value is not None:
                approved_numbers.add(round(c.numeric_value, 2))

        # Calculation results and inputs
        for calc in evidence.calculations:
            if isinstance(calc.result, (int, float)):
                approved_numbers.add(round(float(calc.result), 2))
            if isinstance(calc.inputs, dict):
                for k, v in calc.inputs.items():
                    if isinstance(v, (int, float)):
                        approved_numbers.add(round(float(v), 2))

        # Generate allowed arithmetic derivations (differences, ratios, and cent/dollar unit scaling)
        derived_numbers: Set[float] = set()
        num_list = list(approved_numbers)
        for x in num_list:
            derived_numbers.add(round(x * 100.0, 4))
            derived_numbers.add(round(x / 100.0, 4))
            derived_numbers.add(round(x * 12.0, 2))  # Annualized (12 months)
            derived_numbers.add(round(x / 12.0, 2))  # Monthly from annual

        for i in range(len(num_list)):
            for j in range(i + 1, len(num_list)):
                a, b = num_list[i], num_list[j]
                diff = abs(round(a - b, 2))
                derived_numbers.add(diff)
                if b != 0:
                    ratio = round(a / b, 2)
                    derived_numbers.add(ratio)

        all_allowed_numbers = approved_numbers.union(derived_numbers)

        # Extract numbers from generated LLM text
        extracted_numbers = cls.extract_numbers(generated_text)
        unverified_count = 0
        unsupported_found = False

        for n in extracted_numbers:
            n_round = round(n, 2)
            # Check matching against allowed numbers within FLOAT_TOLERANCE
            matches = any(abs(n_round - allowed) <= FLOAT_TOLERANCE for allowed in all_allowed_numbers)
            if not matches:
                logger.warning(f"Programmatic Validator flagged unsupported number: {n} (Allowed: {all_allowed_numbers})")

                unverified_count += 1
                unsupported_found = True

        if unsupported_found:
            sanitized = generated_text + "\n\n*(Note: Some metrics could not be independently verified from local datasets or EIA/NOAA APIs and have been flagged for accuracy.)*"
            # If severe hallucination (multiple unverified numbers), enforce rejection fallback
            if unverified_count > 2:
                fallback = "I couldn't verify some of the numerical values in available authoritative data sources, so unverified numbers have been excluded to preserve accuracy."
                return False, fallback, unverified_count
            return False, sanitized, unverified_count

        return True, generated_text, 0
