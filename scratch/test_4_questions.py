import asyncio
from api.services.llm.llm_service import llm_service
from api.services.llm.providers.mock_provider import MockLLMProvider

llm_service.orchestrator._default_provider = MockLLMProvider()

ctx = {
    'bill': {
        'total_bill': 143.22,
        'usage_kwh': 725.9,
        'utility': 'PSE&G',
        'supply_charge': 83.07,
        'delivery_charge': 42.95,
        'fixed_charge': 8.24,
        'tax': 8.96,
        'effective_rate': 0.1973,
        'billing_period': 'Jun 2026'
    }
}

questions = [
    "Why is my bill higher this month?",
    "What are the main drivers causing my supply charges to increase?",
    "How did temperature degree-days and market fuel prices affect my latest PSE&G bill?",
    "Break down the delivery charge versus supply charge on my bill."
]

async def main():
    for i, q in enumerate(questions, 1):
        res = await llm_service.generate_explanation(task='chat', context_data=ctx, user_message=q)
        print(f"=== Question {i}: {q} ===")
        text = res['text'].encode('ascii', errors='replace').decode('ascii')
        print(text[:300] + "\n")

if __name__ == '__main__':
    asyncio.run(main())
