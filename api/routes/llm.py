"""
Centralized LLM API Router — Phase 2 Upgrade.
Exposes endpoints:
  - POST /llm/explain  (Tier-routed natural language generation)
  - POST /llm/chat     (Interactive shared AI Copilot)
  - POST /llm/stream   (Plaintext & SSE token streaming)
  - GET  /llm/models   (List registered models & tier availability)
Reused across every tab in ElectricAI.
"""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse, JSONResponse

from api.schemas import (
    UniversalLLMExplainRequest,
    UniversalLLMExplainResponse,
    UniversalLLMChatRequest,
    UniversalLLMChatResponse
)
from api.services.llm.contracts import UserTier
from api.services.llm.llm_service import llm_service
from api.services.llm.context_builder import ContextBuilder
from api.services.llm.model_registry import model_registry

router = APIRouter(prefix="/llm", tags=["Centralized LLM Service"])


def _parse_tier(tier_str: str) -> UserTier:
    try:
        return UserTier(tier_str.lower())
    except ValueError:
        return UserTier.FREE


@router.post("/explain", response_model=UniversalLLMExplainResponse)
async def explain(req: UniversalLLMExplainRequest):
    """
    Generate natural language explanation for any tab task.
    Supports user subscription tier model routing (free, pro, enterprise).
    """
    try:
        tier = _parse_tier(req.user_tier)
        res = await llm_service.generate_explanation(
            task=req.task,
            context_data=req.context_data,
            bypass_cache=req.bypass_cache,
            user_tier=tier
        )
        return UniversalLLMExplainResponse(
            success=res["success"],
            text=res["text"],
            explanation=res["explanation"],
            metadata=res["metadata"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat", response_model=UniversalLLMChatResponse)
async def chat(req: UniversalLLMChatRequest):
    """
    Interactive shared AI Copilot assistant endpoint.
    Includes RAG knowledge base retrieval and conversation context.
    """
    try:
        tier = _parse_tier(req.user_tier)
        uploaded_bill = req.context_data.get("uploadedBill") or req.context_data.get("bill") or req.context_data
        ctx = ContextBuilder.build_chat_context(
            current_tab=req.current_tab,
            uploaded_bill=uploaded_bill if isinstance(uploaded_bill, dict) else None,
            conversation_history=[h.dict() for h in req.history]
        )
        ctx.update(req.context_data)

        res = await llm_service.generate_explanation(
            task="chat",
            context_data=ctx,
            user_message=req.message,
            user_tier=tier
        )
        return UniversalLLMChatResponse(
            success=res["success"],
            answer=res["answer"],
            text=res["text"],
            metadata=res["metadata"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stream")
async def stream_explain(req: UniversalLLMExplainRequest):
    """
    Streaming HTTP endpoint returning text tokens as plain text.
    """
    try:
        tier = _parse_tier(req.user_tier)
        generator = llm_service.stream_explanation(
            task=req.task,
            context_data=req.context_data,
            user_tier=tier
        )
        return StreamingResponse(generator, media_type="text/plain")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models")
async def list_models(tier: str = "free"):
    """
    List all registered LLM models in the catalog for a given user tier.
    """
    user_tier = _parse_tier(tier)
    models = model_registry.list_models(tier=user_tier)
    return {
        "tier": user_tier.value,
        "models": [
            {
                "model_id": m.model_id,
                "provider": m.provider_name,
                "tier": m.tier.value,
                "supports_streaming": m.supports_streaming,
                "context_window": m.context_window,
            }
            for m in models
        ]
    }


@router.get("/rag/health")
async def rag_health():
    """
    Check operational status and document count of the RAG engine.
    """
    from api.services.llm.rag import rag_service
    return rag_service.check_health()


