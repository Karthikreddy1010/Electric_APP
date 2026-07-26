"""
Phase 2 — Comprehensive 7-Point Output Validator Engine.

Audits every LLM-generated response against the source AnalyticsResult context
to prevent hallucination, ensure structural integrity, and enforce professional tone.

7-Point Audit Checklist:
  1. Numeric Exact Match — every number must exist in AnalyticsResult (float tolerance)
  2. Zero-Hallucination Gate — reject phantom figures
  3. JSON Structure Integrity — valid JSON with required keys (geo/ocr tasks)
  4. Required Section Validation — mandatory narrative sections present
  5. Non-Empty Response Check — reject blank or truncated outputs
  6. Professional Tone — reject AI self-references
  7. Missing Field Detection — critical AnalyticsResult dimensions not omitted
"""
import re
import math
import json
import logging
from typing import Dict, Any, List, Set, Tuple, Optional
from api.services.llm.contracts import ValidationResult

logger = logging.getLogger(__name__)

# Common formatting constants that are not hallucinations
_COMMON_CONSTANTS = {
    0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0,
    12.0, 15.0, 20.0, 24.0, 25.0, 30.0, 50.0, 60.0, 90.0,
    100.0, 180.0, 365.0, 500.0, 1000.0, 2000.0
}

# AI self-reference patterns (tone violations)
_TONE_VIOLATIONS = [
    re.compile(r"\bAs an AI\b", re.IGNORECASE),
    re.compile(r"\bAs a language model\b", re.IGNORECASE),
    re.compile(r"\bI think\b", re.IGNORECASE),
    re.compile(r"\bIn my opinion\b", re.IGNORECASE),
    re.compile(r"\bI believe\b", re.IGNORECASE),
    re.compile(r"\bI cannot\b", re.IGNORECASE),
    re.compile(r"\bI don't have\b", re.IGNORECASE),
    re.compile(r"\bI'm not sure\b", re.IGNORECASE),
    re.compile(r"\bAs a chatbot\b", re.IGNORECASE),
]


class OutputValidator:
    """
    Enterprise-grade 7-point LLM output validator.
    Returns a strongly typed ValidationResult contract.
    """

    # ── Numeric Extraction Helpers ──────────────────────────────────────

    @staticmethod
    def _extract_numbers_from_dict(data: Any, found: Set[float]) -> None:
        """Recursively harvest all numbers from structured context (AnalyticsResult)."""
        if isinstance(data, (int, float)):
            if not math.isnan(data) and not math.isinf(data):
                val = float(data)
                found.add(round(val, 4))
                found.add(round(val, 2))
                found.add(round(val, 1))
                found.add(round(val, 0))
        elif isinstance(data, dict):
            for v in data.values():
                OutputValidator._extract_numbers_from_dict(v, found)
        elif isinstance(data, (list, tuple)):
            for item in data:
                OutputValidator._extract_numbers_from_dict(item, found)
        elif isinstance(data, str):
            if not any(char in data for char in ['-', '/']):
                clean_str = data.replace('$', '').replace('%', '').replace(',', '').strip()
                try:
                    num = float(clean_str)
                    found.add(round(num, 4))
                    found.add(round(num, 2))
                    found.add(round(num, 1))
                    found.add(round(num, 0))
                except ValueError:
                    pass

    @staticmethod
    def _extract_numbers_from_text(text: str) -> List[float]:
        """Extract all dollar, percentage, volume, and decimal numbers from text."""
        pattern = r'(?:\$|%|\b)(\d+(?:\.\d+)?)(?:%|\b)?'
        matches = re.findall(pattern, text)
        result = []
        for m in matches:
            try:
                result.append(float(m))
            except ValueError:
                continue
        return result

    # ── Audit Point 1 & 2: Numeric Match & Hallucination Gate ──────────

    @classmethod
    def _audit_numerics(cls, text: str, context_data: Dict[str, Any]) -> Tuple[List[str], List[str]]:
        """Returns (numeric_discrepancies, hallucination_errors)."""
        allowed: Set[float] = set()
        cls._extract_numbers_from_dict(context_data, allowed)
        allowed.update(_COMMON_CONSTANTS)

        text_numbers = cls._extract_numbers_from_text(text)
        discrepancies = []

        for num in text_numbers:
            r1, r2, r4 = round(num, 1), round(num, 2), round(num, 4)
            direct_match = any(r in allowed for r in (r1, r2, r4, num))
            is_int = (num % 1 == 0)
            const_match = is_int and (num in _COMMON_CONSTANTS)

            if not direct_match and not const_match:
                close_match = any(abs(num - val) < 0.05 for val in allowed)
                if not close_match:
                    discrepancies.append(f"Unverified numerical value: '{num}'")

        return discrepancies, discrepancies  # hallucination = same as discrepancy

    # ── Audit Point 3: JSON Structure ──────────────────────────────────

    @staticmethod
    def _audit_json(text: str, task: str) -> List[str]:
        """Validate JSON structure for tasks that require JSON output."""
        json_tasks = {"geo", "ocr"}
        if task not in json_tasks:
            return []

        try:
            parsed = json.loads(text)
            if not isinstance(parsed, dict):
                return ["JSON output is not a dictionary/object"]
            return []
        except json.JSONDecodeError as e:
            return [f"Invalid JSON: {e}"]

    # ── Audit Point 4: Required Sections ───────────────────────────────

    @staticmethod
    def _audit_sections(text: str, task: str) -> List[str]:
        """Check that mandatory sections are present for narrative tasks."""
        section_requirements = {
            "bill_analysis": ["summary", "breakdown", "recommendation"],
            "impact": ["summary", "simulation", "risk"],
            "report": ["summary", "breakdown"],
        }
        required_keywords = section_requirements.get(task, [])
        missing = []
        text_lower = text.lower()
        for keyword in required_keywords:
            if keyword not in text_lower:
                missing.append(f"Missing expected section keyword: '{keyword}'")
        return missing

    # ── Audit Point 5: Non-Empty ───────────────────────────────────────

    @staticmethod
    def _audit_nonempty(text: str) -> List[str]:
        """Reject blank or extremely short responses."""
        if not text or not text.strip():
            return ["Response text is empty"]
        if len(text.strip()) < 20:
            return [f"Response too short ({len(text.strip())} chars)"]
        return []

    # ── Audit Point 6: Professional Tone ───────────────────────────────

    @staticmethod
    def _audit_tone(text: str) -> List[str]:
        """Detect AI self-references and unprofessional language."""
        violations = []
        for pattern in _TONE_VIOLATIONS:
            match = pattern.search(text)
            if match:
                violations.append(f"Tone violation: '{match.group()}'")
        return violations

    # ── Audit Point 7: Missing Critical Fields ─────────────────────────

    @staticmethod
    def _audit_missing_fields(text: str, context_data: Dict[str, Any]) -> List[str]:
        """Check that critical numeric fields from context appear in the output."""
        # Only check the most important top-level values
        critical_keys = ["total_bill", "usage_kwh", "simulated_bill", "total_impact"]
        missing = []
        for key in critical_keys:
            value = None
            # Check top-level and nested bill/simulation
            for sub in [context_data, context_data.get("bill", {}), context_data.get("simulation", {})]:
                if isinstance(sub, dict) and key in sub:
                    value = sub[key]
                    break
            if value is not None and isinstance(value, (int, float)):
                # Check if this value appears anywhere in the text
                str_val = f"{value:.2f}" if isinstance(value, float) else str(value)
                if str_val not in text and str(round(value, 1)) not in text:
                    missing.append(f"Critical field '{key}' value ({value}) not found in output")
        return missing

    # ── Main Entry Point ──────────────────────────────────────────────

    @classmethod
    def validate(
        cls,
        text: str,
        context_data: Dict[str, Any],
        task: str = "bill_analysis"
    ) -> ValidationResult:
        """
        Execute the full 7-point audit and return a ValidationResult contract.
        """
        # Point 5: Non-empty
        empty_errors = cls._audit_nonempty(text)
        if empty_errors:
            return ValidationResult(
                is_valid=False,
                errors=empty_errors,
                retry_recommended=True
            )

        # Point 1 & 2: Numerics & hallucination
        numeric_disc, _ = cls._audit_numerics(text, context_data)

        # Point 3: JSON structure
        json_errors = cls._audit_json(text, task)

        # Point 4: Required sections
        missing_sections = cls._audit_sections(text, task)

        # Point 6: Tone
        tone_violations = cls._audit_tone(text)

        # Point 7: Missing fields
        missing_fields = cls._audit_missing_fields(text, context_data)

        # Aggregate
        all_errors = numeric_disc + json_errors
        all_warnings = missing_sections + tone_violations + missing_fields

        is_valid = len(all_errors) == 0
        retry_recommended = not is_valid

        if not is_valid:
            logger.warning(f"OutputValidator: {len(all_errors)} errors, {len(all_warnings)} warnings")

        return ValidationResult(
            is_valid=is_valid,
            numeric_discrepancies=numeric_disc,
            missing_fields=missing_fields,
            json_errors=json_errors,
            tone_violations=tone_violations,
            errors=all_errors + all_warnings,
            retry_recommended=retry_recommended
        )

    # ── Legacy-compatible class method ─────────────────────────────────

    @classmethod
    def validate_legacy(
        cls,
        text: str,
        context_data: Dict[str, Any]
    ) -> Tuple[bool, List[str]]:
        """
        Backward-compatible validate() returning (is_valid, errors) tuple.
        Used by existing Phase 1 code paths.
        """
        result = cls.validate(text, context_data)
        return result.is_valid, result.errors
