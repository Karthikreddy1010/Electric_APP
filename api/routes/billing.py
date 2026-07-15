"""
GET /bill-breakdown — component-level bill breakdown
GET /trends         — historical trend data
"""
import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from api.state import app_state
from api.schemas import BillBreakdownResponse, TrendResponse, UtilityLookupResponse
from api.services.billing_service import build_breakdown, build_trends

router = APIRouter(tags=["billing"])


@router.get("/bill-breakdown", response_model=list[BillBreakdownResponse])
async def bill_breakdown(months: int = Query(12, ge=1, le=84)):
    """Get detailed bill component breakdown for recent months."""
    billing = app_state["billing_df"]
    if billing is None:
        raise HTTPException(500, "Data not loaded")
    return build_breakdown(billing, months)


@router.get("/trends", response_model=TrendResponse)
async def get_trends(months: int = Query(36, ge=6, le=84)):
    """Get historical trend data."""
    billing = app_state["billing_df"]
    if billing is None:
        raise HTTPException(500, "Data not loaded")
    return build_trends(billing, months)


# ── Serve PSEG rate history ──────────────────────────────────────────────────
@router.get("/pseg-rate-history")
async def get_pseg_rate_history():
    """Get exact historical rate breakdown for PSE&G."""
    df = app_state.get("pseg_history_df")
    if df is None:
        raise HTTPException(404, "PSEG rate history data not available")
    
    # Replace NaN with None for JSON compliance
    records = df.replace({float('nan'): None}).to_dict(orient="records")
    return {"count": len(records), "data": records}


# ── Bill OCR Extraction & Analysis ───────────────────────────────────────────
from api.schemas import BillAnalysisRequest, BillAnalysisResponse
import re
import socket
import asyncio
import logging

logger = logging.getLogger(__name__)

def parse_deterministic_bill(text: str) -> dict:
    """Fallback parser using regexes when Ollama is offline or fails."""
    # 1. Utility Name
    utility_name = None
    for line in text.split("\n"):
        line_clean = line.strip()
        if any(kw in line_clean.upper() for kw in ["PSE&G", "PSEG", "JCP&L", "JERSEY CENTRAL", "ATLANTIC CITY ELECTRIC", "RECO", "ROCKLAND", "POWER CO", "ELECTRIC CO", "UTILITY", "EDC"]):
            utility_name = line_clean
            break
    
    # 2. Billing Period
    billing_period = None
    date_pair_match = re.search(r'(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})\s*(?:to|[-—–])\s*(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})', text, re.IGNORECASE)
    if date_pair_match:
        billing_period = f"{date_pair_match.group(1)} - {date_pair_match.group(2)}"
    else:
        mo_yr_match = re.search(r'(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{4}', text, re.IGNORECASE)
        if mo_yr_match:
            billing_period = mo_yr_match.group(0)

    # Helper to find numbers near keywords
    def find_dollar_value(keywords, text):
        for line in text.split("\n"):
            if any(kw in line.lower() for kw in keywords):
                match = re.search(r'\$?(\d+(?:\.\d{2})?)', line)
                if match:
                    try:
                        return float(match.group(1))
                    except ValueError:
                        pass
        return None

    # 3. Total Amount
    total_amount = find_dollar_value(["total amount", "amount due", "payment due", "total due", "net due", "bill total", "total charge"], text)
    if total_amount is None:
        total_amount = find_dollar_value(["total"], text)

    # 4. kWh Used
    kwh_used = None
    kwh_match = re.search(r'(\d+(?:,\d+)?(?:\.\d+)?)\s*(?:kwh|kilowatt)', text, re.IGNORECASE)
    if kwh_match:
        try:
            kwh_used = float(kwh_match.group(1).replace(",", ""))
        except ValueError:
            pass
    if kwh_used is None:
        for line in text.split("\n"):
            if "kwh" in line.lower() or "usage" in line.lower() or "used" in line.lower():
                match = re.search(r'(\d+(?:,\d+)?(?:\.\d+)?)', line)
                if match:
                    try:
                        kwh_used = float(match.group(1).replace(",", ""))
                        break
                    except ValueError:
                        pass

    # 5. Charges
    supply = find_dollar_value(["supply", "generation", "energy charge", "commodity"], text)
    delivery = find_dollar_value(["delivery", "distribution", "transmission"], text)
    fixed = find_dollar_value(["customer charge", "service charge", "service fee", "fixed charge", "monthly fee", "meter charge"], text)
    tax = find_dollar_value(["tax", "taxes", "sales tax", "state tax"], text)

    supply = supply or 0.0
    delivery = delivery or 0.0
    fixed = fixed or 0.0
    tax = tax or 0.0
    
    if total_amount is None or total_amount == 0.0:
        total_amount = supply + delivery + fixed + tax

    # Percentages
    supply_pct = round((supply / total_amount * 100), 1) if total_amount > 0 else 0.0
    delivery_pct = round((delivery / total_amount * 100), 1) if total_amount > 0 else 0.0
    fixed_pct = round((fixed / total_amount * 100), 1) if total_amount > 0 else 0.0
    tax_pct = round((tax / total_amount * 100), 1) if total_amount > 0 else 0.0

    # 6. Bill Driver
    driver = "usage"
    if fixed_pct > 20.0:
        driver = "fixed"
    elif kwh_used and kwh_used > 0:
        rate = (supply + delivery) / kwh_used
        if rate > 0.25:
            driver = "rate"
        elif kwh_used > 1000:
            driver = "usage"
    
    # 7. Insight explanation
    insight = ""
    components = {"supply": supply, "delivery": delivery, "fixed": fixed, "taxes": tax}
    max_comp = max(components, key=components.get)
    max_val = components[max_comp]
    
    if max_val > 0:
        insight = f"The primary driver of your bill is {max_comp} charges, contributing ${max_val:.2f}."
    else:
        insight = "We analyzed your bill but could not identify a single dominant cost component."

    if driver == "usage":
        insight += f" Your usage of {kwh_used or 0:.0f} kWh is the key factor driving costs this billing cycle."
    elif driver == "rate":
        insight += " High unit rates (cents/kWh) are inflating your bill. Consider comparing retail rates."
    else:
        insight += f" Fixed customer service charges make up a significant portion ({fixed_pct:.1f}%) of your bill."

    return {
        "utility_name": utility_name,
        "billing_period": billing_period,
        "kwh_used": kwh_used,
        "total_amount": total_amount,
        "charges": {
            "supply": supply,
            "delivery": delivery,
            "fixed": fixed,
            "tax": tax
        },
        "percentages": {
            "supply_pct": supply_pct,
            "delivery_pct": delivery_pct,
            "fixed_pct": fixed_pct,
            "tax_pct": tax_pct
        },
        "driver": driver,
        "insight": insight
    }


@router.post("/analyze-ocr", response_model=BillAnalysisResponse)
async def analyze_ocr(req: BillAnalysisRequest):
    """
    Parse raw OCR bill text using the centralized LLM service.
    Falls back to deterministic regex parsing if LLM is offline or fails.
    """
    import json
    from api.services.llm.llm_service import llm_service

    try:
        # Request OCR parse from centralized LLM service
        res = await llm_service.generate_explanation(
            task="ocr",
            context_data={"bill_text": req.bill_text},
            format="json"
        )
        
        # Check if fallback was used
        if res.get("metadata", {}).get("fallback_used", False):
            logger.warning("Centralized LLM service used fallback. Running deterministic fallback.")
            return parse_deterministic_bill(req.bill_text)

        parsed = json.loads(res["text"])
        
        # Ensure all required structure exists
        output = {
            "utility_name": parsed.get("utility_name"),
            "billing_period": parsed.get("billing_period"),
            "kwh_used": parsed.get("kwh_used"),
            "total_amount": parsed.get("total_amount"),
            "charges": {
                "supply": parsed.get("charges", {}).get("supply"),
                "delivery": parsed.get("charges", {}).get("delivery"),
                "fixed": parsed.get("charges", {}).get("fixed"),
                "tax": parsed.get("charges", {}).get("tax")
            },
            "percentages": {
                "supply_pct": parsed.get("percentages", {}).get("supply_pct"),
                "delivery_pct": parsed.get("percentages", {}).get("delivery_pct"),
                "fixed_pct": parsed.get("percentages", {}).get("fixed_pct"),
                "tax_pct": parsed.get("percentages", {}).get("tax_pct")
            },
            "driver": parsed.get("driver", "usage"),
            "insight": parsed.get("insight")
        }
        return output
    except Exception as e:
        logger.warning(f"Ollama parsing failed: {e or type(e).__name__}. Running deterministic fallback.")
        return parse_deterministic_bill(req.bill_text)


# ── ZIP Auto-Detection for Utility and Tariff ────────────────────────────────
@router.get("/bill-analysis/auto-detect", response_model=list[UtilityLookupResponse])
async def auto_detect_utility_by_zip(
    zip: str = Query(..., description="5-digit ZIP code"),
):
    """Auto-detect utility and average rate information by ZIP code."""
    from sqlalchemy import text
    from database.connection import get_sync_engine
    from api.schemas import UtilityLookupResponse
    
    zip_code = zip.strip().zfill(5)
    engine = get_sync_engine()

    query = text("""
        SELECT 
            m.eia_utility_id,
            m.utility_name,
            m.state,
            m.ownership_type,
            z.zip_code,
            z.service_type,
            r.residential_rate,
            r.commercial_rate,
            r.industrial_rate
        FROM utility_zip_lookup z
        JOIN utility_master m ON z.eia_utility_id = m.eia_utility_id AND z.state = m.state
        LEFT JOIN utility_rates r ON m.eia_utility_id = r.eia_utility_id AND m.state = r.state
        WHERE z.zip_code = :zip_code
    """)

    try:
        df = pd.read_sql(query, con=engine, params={"zip_code": zip_code})
    except Exception as e:
        logger.error(f"Error auto-detecting utility by ZIP: {e}")
        raise HTTPException(500, "Database query error")

    if df.empty:
        raise HTTPException(404, f"No utilities found for ZIP code {zip_code}")

    results = []
    for _, row in df.iterrows():
        results.append(UtilityLookupResponse(
            eia_utility_id=int(row["eia_utility_id"]),
            utility_name=str(row["utility_name"]),
            state=str(row["state"]),
            ownership_type=str(row["ownership_type"]) if pd.notna(row.get("ownership_type")) else None,
            zip_code=str(row["zip_code"]),
            service_type=str(row["service_type"]) if pd.notna(row.get("service_type")) else None,
            residential_rate=float(row["residential_rate"]) if pd.notna(row.get("residential_rate")) else None,
            commercial_rate=float(row["commercial_rate"]) if pd.notna(row.get("commercial_rate")) else None,
            industrial_rate=float(row["industrial_rate"]) if pd.notna(row.get("industrial_rate")) else None,
        ))

    return results

