"""
Manual Request Validators
=========================
Flask lacks Pydantic-level validation. These helpers provide
consistent parameter extraction and range checking for GET query
params and POST JSON bodies.
"""
from flask import request, abort


def validate_int_param(
    name: str,
    default: int = 0,
    min_val: int | None = None,
    max_val: int | None = None,
    source: str = "args",
) -> int:
    """
    Extract and validate an integer parameter from the request.

    Parameters
    ----------
    name     : query-param or JSON key name
    default  : default if missing
    min_val  : inclusive lower bound (optional)
    max_val  : inclusive upper bound (optional)
    source   : "args" (GET) or "json" (POST)
    """
    if source == "json":
        body = request.get_json(silent=True) or {}
        raw = body.get(name, default)
    else:
        raw = request.args.get(name, default)

    try:
        value = int(raw)
    except (TypeError, ValueError):
        abort(422, description=f"Parameter '{name}' must be an integer")

    if min_val is not None and value < min_val:
        abort(422, description=f"Parameter '{name}' must be >= {min_val}")
    if max_val is not None and value > max_val:
        abort(422, description=f"Parameter '{name}' must be <= {max_val}")

    return value


def validate_float_param(
    name: str,
    default: float = 0.0,
    min_val: float | None = None,
    max_val: float | None = None,
    source: str = "args",
) -> float:
    """Extract and validate a float parameter from the request."""
    if source == "json":
        body = request.get_json(silent=True) or {}
        raw = body.get(name, default)
    else:
        raw = request.args.get(name, default)

    try:
        value = float(raw)
    except (TypeError, ValueError):
        abort(422, description=f"Parameter '{name}' must be a number")

    if min_val is not None and value < min_val:
        abort(422, description=f"Parameter '{name}' must be >= {min_val}")
    if max_val is not None and value > max_val:
        abort(422, description=f"Parameter '{name}' must be <= {max_val}")

    return value


def validate_str_param(
    name: str,
    default: str = "",
    min_length: int = 0,
    max_length: int = 255,
    source: str = "args",
) -> str:
    """Extract and validate a string parameter from the request."""
    if source == "json":
        body = request.get_json(silent=True) or {}
        raw = body.get(name, default)
    else:
        raw = request.args.get(name, default)

    value = str(raw).strip()

    if len(value) < min_length:
        abort(422, description=f"Parameter '{name}' must be at least {min_length} characters")
    if len(value) > max_length:
        abort(422, description=f"Parameter '{name}' must be at most {max_length} characters")

    return value
