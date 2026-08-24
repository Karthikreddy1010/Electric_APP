"""
Evidence Validation Engine for Grounded AI Assistant.
Extracts, structures, validates, and resolves conflicting evidence from executed tool outputs.
Enforces: NO EVIDENCE = NO FACTUAL CLAIM.
"""
import logging
from typing import Dict, Any, List, Optional
from ai.schemas import (
    EvidenceObject, ClaimItem, CalculationItem, SourceMetadata,
    SourceAuthorityRating, ClaimConfidence, ConflictingSourceItem
)

logger = logging.getLogger(__name__)


class EvidenceValidationEngine:
    """
    Constructs an immutable EvidenceObject from executed tool responses.
    Validates claim provenance against specific tool names and raw output keys.
    """

    @staticmethod
    def build_evidence(question: str, tool_outputs: List[Dict[str, Any]]) -> EvidenceObject:
        claims: List[ClaimItem] = []
        calculations: List[CalculationItem] = []
        sources: List[SourceMetadata] = []
        conflicting_sources: List[ConflictingSourceItem] = []
        missing_info: List[str] = []
        claim_counter = 1

        state_price_records: List[Dict[str, Any]] = []

        for out in tool_outputs:
            if not isinstance(out, dict):
                continue

            success = out.get("success", False)
            t_name = out.get("tool_name", "unknown_tool")
            data = out.get("data")
            error = out.get("error")

            if not success or data is None:
                missing_info.append(f"Tool '{t_name}' returned error: {error or 'Data unavailable'}")
                continue

            # Process Source Metadata
            source_info = out.get("source") or data.get("source") or data.get("source_title")
            src_meta = SourceMetadata(
                source_id=f"src_{t_name}",
                title=str(data.get("source_title") or source_info or t_name),
                url=data.get("url"),
                publication_date=data.get("publication_date"),
                authority=SourceAuthorityRating.HIGH if "EIA" in str(source_info) or "NOAA" in str(source_info) or "BPU" in str(source_info) else SourceAuthorityRating.MEDIUM,
                geography=data.get("state") or data.get("location"),
                temporal_coverage=str(data.get("year") or data.get("period") or "")
            )
            sources.append(src_meta)

            # 1. Process get_bill_details / components
            if t_name in ["get_bill_details", "get_bill_components"]:
                for k, v in data.items():
                    if isinstance(v, (int, float)) and not isinstance(v, bool):
                        claims.append(ClaimItem(
                            claim_id=f"claim_{claim_counter}",
                            claim_text=f"Bill metric {k} is {v}",
                            numeric_value=float(v),
                            unit="$" if "charge" in k or "bill" in k or "tax" in k or "cost" in k else ("kWh" if "kwh" in k else None),
                            tool_name=t_name,
                            raw_output_key=k,
                            source_provenance=src_meta
                        ))
                        claim_counter += 1
                if isinstance(data.get("components"), list):
                    for comp in data["components"]:
                        if isinstance(comp, dict):
                            for ck, cv in comp.items():
                                if isinstance(cv, (int, float)) and not isinstance(cv, bool):
                                    claims.append(ClaimItem(
                                        claim_id=f"claim_{claim_counter}",
                                        claim_text=f"Component {comp.get('name', 'item')} {ck} is {cv}",
                                        numeric_value=float(cv),
                                        unit="$" if "amount" in ck or "cost" in ck else None,
                                        tool_name=t_name,
                                        raw_output_key=f"component_{ck}",
                                        source_provenance=src_meta
                                    ))
                                    claim_counter += 1

            # 2. Process get_state_electricity_price, eia_api_tool, & authoritative_web_search_tool (if it contains price data)
            elif t_name in ["get_state_electricity_price", "eia_api_tool"] or (t_name == "authoritative_web_search_tool" and "price_cents_per_kwh" in data):
                st = data.get("state", "US")
                price = data.get("price_cents_per_kwh")
                yr = data.get("year", 2024)
                if price is not None:
                    claims.append(ClaimItem(
                        claim_id=f"claim_{claim_counter}",
                        claim_text=f"Average residential electricity price in {st} ({yr}) is {price} cents/kWh",
                        numeric_value=float(price),
                        unit="cents/kWh",
                        tool_name=t_name,
                        raw_output_key="price_cents_per_kwh",
                        source_provenance=src_meta
                    ))
                    claim_counter += 1
                    state_price_records.append({
                        "state": st,
                        "year": yr,
                        "price": float(price),
                        "source": src_meta
                    })

            # 3. Process calculate_kwh_scenario
            elif t_name == "calculate_kwh_scenario":
                savings = data.get("monthly_savings_dollars")
                kwh_red = data.get("kwh_reduction")
                pct_red = data.get("percentage_reduction")
                if savings is not None:
                    calculations.append(CalculationItem(
                        calculation_id=f"calc_{len(calculations)+1}",
                        formula=f"({data['baseline_kwh']} - {data['target_kwh']}) * ${data['rate_per_kwh']}/kWh",
                        inputs=data,
                        result=float(savings),
                        unit="$",
                        deterministic_engine=out.get("deterministic_engine", "calculate_kwh_scenario")
                    ))
                    for k, v in data.items():
                        if isinstance(v, (int, float)) and not isinstance(v, bool):
                            claims.append(ClaimItem(
                                claim_id=f"claim_{claim_counter}",
                                claim_text=f"Scenario {k} is {v}",
                                numeric_value=float(v),
                                unit="$" if "dollar" in k or "cost" in k or "savings" in k else ("%" if "pct" in k or "percentage" in k else ("kWh" if "kwh" in k else None)),
                                tool_name=t_name,
                                raw_output_key=k,
                                source_provenance=src_meta
                            ))
                            claim_counter += 1

            # 4. Process calculate_component_change
            elif t_name == "calculate_component_change":
                diff = data.get("bill_diff_dollars")
                pct = data.get("bill_pct_change")
                kwh_diff = data.get("usage_diff_kwh")
                if diff is not None:
                    calculations.append(CalculationItem(
                        calculation_id=f"calc_{len(calculations)+1}",
                        formula="current_total_bill - previous_total_bill",
                        inputs=data,
                        result=float(diff),
                        unit="$",
                        deterministic_engine="calculate_component_change"
                    ))
                    claims.append(ClaimItem(
                        claim_id=f"claim_{claim_counter}",
                        claim_text=f"Bill increased by ${diff} ({pct}%) due to +{kwh_diff} kWh additional usage",
                        numeric_value=float(diff),
                        unit="$",
                        tool_name=t_name,
                        raw_output_key="bill_diff_dollars",
                        source_provenance=src_meta
                    ))
                    claim_counter += 1

            # 5. Generic Claim Extraction for other tools
            else:
                for k, v in data.items():
                    if isinstance(v, (int, float)) and not isinstance(v, bool):
                        claims.append(ClaimItem(
                            claim_id=f"claim_{claim_counter}",
                            claim_text=f"{t_name} metric {k} is {v}",
                            numeric_value=float(v),
                            unit=None,
                            tool_name=t_name,
                            raw_output_key=k,
                            source_provenance=src_meta
                        ))
                        claim_counter += 1

        # Check for Conflicting Sources across state price records
        state_price_map: Dict[str, List[Dict[str, Any]]] = {}
        for rec in state_price_records:
            st_key = f"{rec['state']}_{rec['year']}"
            state_price_map.setdefault(st_key, []).append(rec)

        for st_key, recs in state_price_map.items():
            if len(recs) > 1:
                vals = [r["price"] for r in recs]
                if max(vals) - min(vals) > 0.01:
                    # Select most authoritative source: prefer HIGH authority, then EIA in source title
                    sorted_recs = sorted(recs, key=lambda r: (
                        0 if r["source"].authority == SourceAuthorityRating.HIGH else 1,
                        0 if "EIA" in (r["source"].title or "") else 1
                    ))
                    selected = sorted_recs[0]
                    conflicting_sources.append(ConflictingSourceItem(
                        metric="residential_electricity_price",
                        geography=recs[0]["state"],
                        year=recs[0]["year"],
                        sources_compared=[r["source"] for r in recs],
                        values_reported={r["source"].title: r["price"] for r in recs},
                        resolution_explanation=f"Reported values differ ({', '.join(str(v) for v in vals)} cents/kWh). Selected most authoritative source: {selected['source'].title}.",
                        selected_source=selected["source"]
                    ))

        # Semantic Gap Check: Question asks about "bill" (dollar amount) but evidence only has price data
        q_lower = question.lower()
        asks_about_bill = any(w in q_lower for w in ["average bill", "residential bill", "electricity bill", "total bill"])
        has_bill_amount = any(c.raw_output_key == "total_bill" or c.unit == "$" for c in claims)
        has_only_price = any(c.raw_output_key == "price_cents_per_kwh" for c in claims) and not has_bill_amount

        if asks_about_bill and has_only_price and not has_bill_amount:
            missing_info.append(
                "Average residential bill (total dollar amount) data is not available for this state/year. "
                "Only price-per-kWh data was found, which is insufficient to calculate an average bill without verified usage data."
            )
            # Downgrade confidence since we can't answer the actual question
            overall_conf = ClaimConfidence.UNVERIFIED
        else:
            overall_conf = ClaimConfidence.HIGH if claims else ClaimConfidence.UNVERIFIED

        return EvidenceObject(
            question=question,
            claims=claims,
            calculations=calculations,
            external_sources=sources,
            conflicting_sources=conflicting_sources,
            missing_information=missing_info,
            overall_confidence=overall_conf
        )
