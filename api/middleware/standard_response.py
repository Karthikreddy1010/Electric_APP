import time
import json
import logging
from datetime import datetime
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

logger = logging.getLogger(__name__)


class StandardResponseMiddleware(BaseHTTPMiddleware):
    """
    FastAPI Middleware to standardize all API responses and errors.
    
    Format for success:
    {
        "success": true,
        "message": "Request completed successfully",
        "data": ...,
        "execution_time_ms": 12.34,
        "timestamp": "2026-07-07T09:44:00Z",
        "version": "1.0.0"
    }

    Format for error:
    {
        "success": false,
        "error_code": "BAD_REQUEST",
        "message": "Error details",
        "details": {}
    }
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Exclude system endpoints, static files, and metric scrapers from wrapping
        path = request.url.path
        if (
            path == "/health"
            or path == "/metrics"
            or path.startswith("/static")
            or path.startswith("/app")
        ):
            return await call_next(request)

        start_time = time.perf_counter()

        try:
            response = await call_next(request)
            
            # Skip wrapping for non-JSON responses (like streams, PDFs, octet-streams, etc.)
            content_type = response.headers.get("content-type", "")
            if "application/json" not in content_type:
                return response

            # Consume response body to wrap it
            response_body = b""
            async for chunk in response.body_iterator:
                response_body += chunk

            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            timestamp = datetime.utcnow().isoformat() + "Z"

            try:
                data = json.loads(response_body.decode("utf-8"))
            except Exception:
                data = response_body.decode("utf-8")

            # Check if it's already an error response structure
            is_error = response.status_code >= 400
            
            if is_error:
                # If it's already structured, return it
                if isinstance(data, dict) and "success" in data and not data["success"]:
                    wrapped_data = data
                else:
                    # Structure raw error payload
                    msg = "An error occurred"
                    details = {}
                    if isinstance(data, dict):
                        msg = data.get("detail", str(data))
                        details = data
                    else:
                        msg = str(data)
                    
                    wrapped_data = {
                        "success": False,
                        "error_code": self._get_error_code(response.status_code),
                        "message": msg,
                        "details": details
                    }
            else:
                # Wrap successful JSON response
                wrapped_data = {
                    "success": True,
                    "message": "Request completed successfully",
                    "data": data,
                    "execution_time_ms": elapsed_ms,
                    "timestamp": timestamp,
                    "version": "1.0.0"
                }

            # Re-create the JSONResponse with the wrapped content
            headers = dict(response.headers)
            headers.pop("content-length", None)
            
            client_ip = request.client.host if request.client else "unknown"
            logger.info(
                f"HTTP_SUCCESS | IP: {client_ip} | METHOD: {request.method} | PATH: {request.url.path} | "
                f"STATUS: {response.status_code} | TIME: {elapsed_ms:.2f}ms"
            )
            
            return JSONResponse(
                content=wrapped_data,
                status_code=response.status_code,
                headers=headers
            )

        except Exception as exc:
            logger.exception(f"Unhandled error in request middleware: {exc}")
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            timestamp = datetime.utcnow().isoformat() + "Z"
            
            client_ip = request.client.host if request.client else "unknown"
            logger.error(
                f"HTTP_ERROR | IP: {client_ip} | METHOD: {request.method} | PATH: {request.url.path} | "
                f"STATUS: 500 | TIME: {elapsed_ms:.2f}ms | ERR: {str(exc)}"
            )
            
            error_payload = {
                "success": False,
                "error_code": "INTERNAL_SERVER_ERROR",
                "message": str(exc),
                "details": {
                    "execution_time_ms": elapsed_ms,
                    "timestamp": timestamp
                }
            }
            return JSONResponse(
                content=error_payload,
                status_code=500
            )

    def _get_error_code(self, status_code: int) -> str:
        """Map HTTP status code to uppercase string code."""
        mapping = {
            400: "BAD_REQUEST",
            401: "UNAUTHORIZED",
            403: "FORBIDDEN",
            404: "NOT_FOUND",
            405: "METHOD_NOT_ALLOWED",
            422: "VALIDATION_ERROR",
            429: "TOO_MANY_REQUESTS",
            500: "INTERNAL_SERVER_ERROR",
            503: "SERVICE_UNAVAILABLE"
        }
        return mapping.get(status_code, "ERROR")
