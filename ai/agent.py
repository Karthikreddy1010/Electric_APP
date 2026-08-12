"""
GroundedAgent executable entry point orchestrating LangGraph state machine.
"""
import time
import logging
from typing import Dict, Any, List, Optional, AsyncGenerator
from ai.graph import grounded_graph_app
from ai.schemas import GroundedResponse

logger = logging.getLogger(__name__)


class GroundedAgent:
    """
    High-level agent interface wrapping the LangGraph state machine for all task types.
    """

    async def execute(
        self,
        user_query: str,
        history: Optional[List[Dict[str, Any]]] = None,
        current_tab: Optional[str] = None,
        context_data: Optional[Dict[str, Any]] = None,
        user_tier: str = "free"
    ) -> Dict[str, Any]:
        """
        Executes full Grounded AI pipeline and returns legacy-compatible response dictionary:
        {
            "success": True,
            "answer": "...",
            "text": "...",
            "explanation": "...",
            "metadata": { ... groundedness metadata ... }
        }
        """
        start_time = time.time()
        initial_state = {
            "user_query": user_query,
            "history": history or [],
            "current_tab": current_tab,
            "context_data": context_data or {},
            "user_tier": user_tier,
            "messages": []
        }

        try:
            final_state = await grounded_graph_app.ainvoke(initial_state)
            val_resp = final_state.get("validated_response", {})
            elapsed = round(time.time() - start_time, 3)

            answer = val_resp.get("answer", "Information processed.")
            evidence = val_resp.get("evidence", {})
            sources = val_resp.get("sources", [])
            tools_used = val_resp.get("tools_used", [])
            calcs = val_resp.get("calculations", [])
            grounded = val_resp.get("grounded", True)
            blocked = val_resp.get("unverified_claims_blocked", 0)

            return {
                "success": True,
                "answer": answer,
                "text": answer,
                "explanation": answer,
                "metadata": {
                    "latency_sec": elapsed,
                    "grounded": grounded,
                    "unverified_claims_blocked": blocked,
                    "tools_used": tools_used,
                    "sources": sources,
                    "calculations": calcs,
                    "evidence_claims_count": len(evidence.get("claims", [])),
                    "conflicting_sources_resolved": len(evidence.get("conflicting_sources", []))
                }
            }
        except Exception as e:
            logger.error(f"GroundedAgent execution failed: {e}", exc_info=True)
            return {
                "success": False,
                "answer": "I could not process your request due to an internal error.",
                "text": "I could not process your request due to an internal error.",
                "explanation": str(e),
                "metadata": {
                    "error": str(e),
                    "grounded": False
                }
            }

    async def stream(
        self,
        user_query: str,
        user_tier: str = "free",
        **kwargs: Any
    ) -> AsyncGenerator[str, None]:
        """
        Token streaming wrapper over GroundedAgent execution.
        """
        res = await self.execute(user_query=user_query, user_tier=user_tier, **kwargs)
        text = res.get("text", "")
        # Yield words in chunks to simulate token streaming
        words = text.split(" ")
        for w in words:
            yield w + " "
            import asyncio
            await asyncio.sleep(0.02)


# Global singleton instance
grounded_agent = GroundedAgent()
