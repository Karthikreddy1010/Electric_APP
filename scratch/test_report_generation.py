import sys
import os
import asyncio
sys.path.append(os.getcwd())

async def main():
    from api.services.llm.llm_service import llm_service
    from api.services.llm.context_builder import ContextBuilder

    output_lines = []
    output_lines.append("=================================================================")
    output_lines.append("TESTING LLM SERVICE GENERATION QUALITY VIA OLLAMA (qwen3:4b)")
    output_lines.append("=================================================================\n")

    # Mock bill context data
    mock_bill = {
        "utility": "PSE&G",
        "customer_id": "TEST-12345",
        "rate_schedule": "RS",
        "billing_period": "Jun 2026",
        "usage_kwh": 780.0,
        "total_bill": 144.20,
        "effective_rate": 0.1849,
        "monthly_service_charge": 8.24,
        "delivery_charge": 42.50,
        "supply_charge": 85.00,
        "tax": 8.46
    }

    # 1. Test bill analysis generation
    output_lines.append("1. Generating Bill Analysis Audit Report...")
    ctx_bill = ContextBuilder.build_bill_analysis_context(mock_bill)
    res_bill = await llm_service.generate_explanation(task="bill_analysis", context_data=ctx_bill)
    output_lines.append(f"Validation Status: {res_bill.get('metadata', {}).get('validated')}")
    output_lines.append(f"Fallback Used: {res_bill.get('metadata', {}).get('fallback_used')}")
    output_lines.append("Generated Text:\n")
    output_lines.append(res_bill["explanation"])
    output_lines.append("\n-----------------------------------------------------------------\n")

    # 2. Test PDF report narrative generation
    output_lines.append("2. Generating PDF Report Narrative...")
    ctx_report = {
        "total_bill": 144.20,
        "current_month": "2026-06",
        "top_features": [
            {"label": "BGS Supply charges", "shap_value": 85.00, "share_pct": 58.9},
            {"label": "Delivery charges", "shap_value": 42.50, "share_pct": 29.5}
        ],
        "insights": [
            "BGS Supply charges represent 58.9% of your total bill.",
            "Higher summer temperatures increased cooling degree days (CDD) by 15%."
        ]
    }
    res_report = await llm_service.generate_explanation(task="report", context_data=ctx_report)
    output_lines.append(f"Validation Status: {res_report.get('metadata', {}).get('validated')}")
    output_lines.append(f"Fallback Used: {res_report.get('metadata', {}).get('fallback_used')}")
    output_lines.append("Generated Text:\n")
    output_lines.append(res_report["explanation"])
    output_lines.append("\n=================================================================")

    # Write output file
    os.makedirs("scratch", exist_ok=True)
    with open("scratch/report_quality_output.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(output_lines))
    print("Report quality output written to scratch/report_quality_output.txt")

if __name__ == "__main__":
    asyncio.run(main())
