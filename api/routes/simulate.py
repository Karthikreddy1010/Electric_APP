from fastapi import APIRouter
from api.schemas import SimulateRequest, SimulateResult
from api.services.bill_impact_engine import bill_impact_engine, COMPONENT_TYPES

router = APIRouter(tags=["dashboard"])


@router.post("/simulate", response_model=SimulateResult)
async def simulate_impact(req: SimulateRequest):
    sim = bill_impact_engine.what_if_simulation(req.modifications, req.kwh)
    
    # Formula construction
    comp_labels = []
    for k, v in req.modifications.items():
        key = k
        if key not in COMPONENT_TYPES:
            if f"{key}_rate" in COMPONENT_TYPES:
                key = f"{key}_rate"
            elif f"{key}_charge" in COMPONENT_TYPES:
                key = f"{key}_charge"
        label = COMPONENT_TYPES[key]['label'] if key in COMPONENT_TYPES else k.upper()
        comp_labels.append(f"{label} ({v}%)")
        
    formula = "New Bill = Base Bill × (1 + Σ(% Change_i × Weight_i) × Elasticity)"
    
    return SimulateResult(
        old_bill=sim['base_bill'],
        new_bill=sim['new_bill'],
        delta_abs=sim['total_impact'],
        delta_pct=round((sim['total_impact'] / sim['base_bill'] * 100), 2) if sim['base_bill'] > 0 else 0,
        formula=formula,
        explanation=f"If {', '.join(comp_labels)} change, your bill increases/decreases by approximately {sim['total_impact']} based on historical elasticity."
    )
