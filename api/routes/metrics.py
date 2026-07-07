from fastapi import APIRouter, Response
from api.middleware.metrics import get_metrics_page, CONTENT_TYPE_LATEST

router = APIRouter(tags=["monitoring"])


@router.get("/metrics")
def metrics():
    """Expose Prometheus metrics for scraping."""
    return Response(content=get_metrics_page(), media_type=CONTENT_TYPE_LATEST)
