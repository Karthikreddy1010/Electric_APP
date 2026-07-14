from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from api.state import app_state
from api.cache import cached
from config.constants import COMPONENT_LABELS_MAP, COMPONENT_DESCRIPTIONS
import pandas as pd
import logging
import io
import re
import socket
import time
import asyncio
import ollama
from reportlab.lib.pagesizes import LETTER
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

logger = logging.getLogger(__name__)
router = APIRouter(tags=["dashboard"])


def compute_bill_analysis():
    """Single source of truth for UI, LLM, and PDF, backed by BillImpactModel."""
    from models.impact_model import BillImpactModel
    model = BillImpactModel()
    
    billing = app_state["billing_df"]
    latest_row = billing.iloc[-1].to_dict()
    prev_row = billing.iloc[-2].to_dict() if len(billing) > 1 else latest_row
    
    analysis = model.get_analysis(latest_row, prev_row)
    base_bill = analysis["total_bill"]
    
    # Map contributions to features
    all_features = []
    for short_key, data in analysis["contributions"].items():
        label, driver = COMPONENT_LABELS_MAP.get(short_key, (short_key.capitalize(), "External"))
        all_features.append({
            "label": label,
            "shap_value": data["value"],
            "share_pct": data["percent"],
            "category": driver
        })
        
    # Sort features by absolute contribution descending
    all_features = sorted(all_features, key=lambda x: abs(x["shap_value"]), reverse=True)
    
    # Map sensitivity dictionary to the UI format
    sensitivity = []
    for short_key, impacts in analysis["sensitivity"].items():
        label, driver = COMPONENT_LABELS_MAP.get(short_key, (short_key.capitalize(), "External"))
        elasticity = abs(impacts.get("+10%", 0)) / (base_bill * 0.10) if base_bill else 0.0
        
        sensitivity.append({
            "component": label,
            "elasticity": round(elasticity, 4),
            "impact_type": "high" if elasticity > 0.3 else ("medium" if elasticity > 0.1 else "low"),
            "driver": driver,
            "reasoning": COMPONENT_DESCRIPTIONS.get(label, "Variable billing component sensitivity.")
        })
        
    # Sort sensitivity by elasticity descending
    sensitivity = sorted(sensitivity, key=lambda x: x["elasticity"], reverse=True)
    
    # Format date cleanly
    current_m = billing["date"].iloc[-1]
    if hasattr(current_m, "strftime"):
        current_m = current_m.strftime("%Y-%m")
    else:
        current_m = str(current_m)[:7]
        
    return {
        "base_bill": base_bill,
        "all_features": all_features,
        "sensitivity": sensitivity,
        "current_month": current_m,
        "insights": analysis["insights"],
        "latest_row": {
            "usage_kwh": float(latest_row.get("usage_kwh", 750)),
            "base_bill": float(latest_row.get("total_bill", base_bill)),
            "bgs_rate": float(latest_row.get("bgs_rate", 0.11)),
            "distribution_rate": float(latest_row.get("distribution_rate", 0.04)),
            "transmission_rate": float(latest_row.get("transmission_rate", 0.02)),
            "sbc_rate": float(latest_row.get("sbc_rate", 0.008)),
            "nug_rate": float(latest_row.get("nug_rate", 0.002)),
            "customer_charge": 8.24,
            "cdd": float(analysis.get("weather_cdd", 0.0)),
            "hdd": float(analysis.get("weather_hdd", 0.0))
        },
        "alpha": analysis.get("alpha", 0.85),
        "beta": analysis.get("beta", 0.45),
        "base_usage": analysis.get("base_usage", 450.0),
        "confidence": analysis.get("confidence", "High")
    }


@router.get("/impact/top-features")
@cached(ttl=300)
async def get_top_features(n: int = Query(10, ge=1, le=50)):
    analysis = compute_bill_analysis()
    top_n = analysis["all_features"][:n]
    
    return {
        "features": [f["label"] for f in top_n],
        "shap_values": [f["shap_value"] for f in top_n],
        "percent_contribution": [f["share_pct"] for f in top_n]
    }


@router.get("/impact/full-analysis")
@cached(ttl=300)
async def get_full_analysis():
    return compute_bill_analysis()


def _get_report_data_and_prompt():
    analysis = compute_bill_analysis()
    
    # Deterministic High-Fidelity Fallback
    top_driver = analysis['all_features'][0]
    total_bill = analysis['base_bill']
    month = analysis['current_month']
    share = top_driver['share_pct']
    
    weather_insights = "\n".join(f"    - {ins}" for ins in analysis["insights"] if "demand" in ins.lower() or "cooling" in ins.lower() or "heating" in ins.lower() or "weather" in ins.lower() or "non-weather" in ins.lower())
    
    fallback_text = f"""
    Your electricity bill for {month} is mainly driven by {top_driver['label']} costs, which account for about {share:.1f}% of the total (${abs(top_driver['shap_value']):.2f}). These costs depend on market electricity prices and are not directly controllable.
    
    Other utility fees and delivery charges constitute the remaining portion of your cost structure.
    
    Seasonal Cost and Weather Drivers:
{weather_insights if weather_insights else "    - Standard baseline seasonal temperatures."}
    
    To reduce your overall bill:
    1. Focus on lowering overall usage (kWh), as all delivery charges directly scale with consumption.
    2. Reduce peak-time consumption when grid congestion is highest.
    3. Monitor and manage high-load appliances.
    """
    
    prompt = f"""
    You are an electricity billing expert.

    Explain the user's bill using:
    - total bill: ${total_bill:.2f}
    - component breakdown: {analysis}

    Focus on:
    - Which components contribute the most (such as {top_driver['label']} at {share:.1f}%)
    - What is controllable vs uncontrollable
    - Why the bill changed
    - What actions the user can take
    - Highlight seasonal weather demand (cooling/heating loads) vs behavioral usage

    Do NOT mention SHAP, models, or AI.
    Use simple, practical language.
    """
    return prompt, fallback_text, month, analysis


@router.post("/report/generate")
async def generate_report():
    prompt, fallback_text, _, _ = _get_report_data_and_prompt()
    
    async def generate_stream():
        try:
            # Step 1: Rapid socket check to see if Ollama is listening
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.1)
            res = sock.connect_ex(('127.0.0.1', 11434))
            sock.close()
            if res != 0:
                raise RuntimeError("Ollama daemon offline")

            client = ollama.AsyncClient(timeout=1.5)
            response = await client.chat(
                model="qwen3:4b",
                messages=[{"role": "user", "content": prompt}],
                options={
                    "temperature": 0.2,
                    "num_predict": 250
                },
                stream=True
            )
            
            start_time = time.time()
            # Step 2: Retrieve streamed tokens with a strict timeout to prevent hangs
            while True:
                try:
                    chunk = await asyncio.wait_for(response.__anext__(), timeout=1.0)
                    if 'message' in chunk and 'content' in chunk['message']:
                        yield chunk['message']['content']
                    if time.time() - start_time > 10.0:
                        yield "\n\n[Generation stopped: Time limit exceeded]"
                        break
                except StopAsyncIteration:
                    break
        except Exception as e:
            # Transparently return fallback if AI is offline, slow, or times out
            logger.warning(f"Ollama streaming report generation failed: {e or type(e).__name__}. Using deterministic fallback.")
            yield f"[AI Engine Offline - Deterministic Summary Generated]\n{fallback_text}"
            
    return StreamingResponse(generate_stream(), media_type="text/plain")


@router.post("/report/pdf")
async def generate_pdf():
    prompt, fallback_text, month, analysis = _get_report_data_and_prompt()
    
    try:
        # Step 1: Rapid socket check to see if Ollama is listening
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.1)
        res = sock.connect_ex(('127.0.0.1', 11434))
        sock.close()
        if res != 0:
            raise RuntimeError("Ollama daemon offline")

        # Non-streaming for PDF
        client = ollama.AsyncClient(timeout=1.5)
        
        async def fetch_chat():
            return await client.chat(
                model="qwen3:4b",
                messages=[{"role": "user", "content": prompt}],
                options={
                    "temperature": 0.2,
                    "num_predict": 250
                }
            )
        
        # Enforce 1.5s strict timeout
        response = await asyncio.wait_for(fetch_chat(), timeout=1.5)
        text = response['message']['content']
    except Exception as e:
        logger.warning(f"Ollama PDF report generation failed: {e or type(e).__name__}. Using deterministic fallback.")
        text = f"[AI Engine Offline - Deterministic Summary Generated]\n{fallback_text}"
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=LETTER)
    styles = getSampleStyleSheet()
    elements = []
    
    elements.append(Paragraph("Electricity Bill Analysis Report", styles['Title']))
    elements.append(Spacer(1, 12))
    
    # Split text by newlines and add as paragraphs
    for line in text.split('\n'):
        if line.strip():
            elements.append(Paragraph(line, styles['Normal']))
            elements.append(Spacer(1, 6))
            
    doc.build(elements)
    buffer.seek(0)
    
    return StreamingResponse(
        buffer, 
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=bill_report_{month}.pdf"}
    )
