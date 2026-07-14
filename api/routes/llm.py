"""
Centralized LLM API Router.
Exposes universal endpoints:
- POST /llm/explain
- POST /llm/chat
- POST /llm/stream
Reused across every tab in ElectricAI.
"""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse

from api.schemas import (
    UniversalLLMExplainRequest,
    UniversalLLMExplainResponse,
    UniversalLLMChatRequest,
    UniversalLLMChatResponse
)
from api.services.llm.llm_service import llm_service
from api.services.llm.context_builder import ContextBuilder

router = APIRouter(prefix="/llm", tags=["Centralized LLM Service"])

@router.post("/explain", response_model=UniversalLLMExplainResponse)
async def explain(req: UniversalLLMExplainRequest):
    """
    Generate natural language explanation for any tab task.
    """
    try:
        res = await llm_service.generate_explanation(
            task=req.task,
            context_data=req.context_data,
            bypass_cache=req.bypass_cache
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
    """
    try:
        # Construct chat context
        ctx = ContextBuilder.build_chat_context(
            current_tab=req.current_tab,
            conversation_history=[h.dict() for h in req.history]
        )
        # Merge extra user context data
        ctx.update(req.context_data)

        res = await llm_service.generate_explanation(
            task="chat",
            context_data=ctx,
            user_message=req.message
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
        generator = llm_service.stream_explanation(
            task=req.task,
            context_data=req.context_data
        )
        return StreamingResponse(generator, media_type="text/plain")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
