import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useBill } from '../context/BillContext.tsx';
import { RefreshCw } from 'lucide-react';

export default function DemoPage() {
  const { setBillData } = useBill();
  const navigate = useNavigate();

  useEffect(() => {
    // 1. Mark demo mode in session storage
    sessionStorage.setItem('is_demo_mode', 'true');

    // 2. Set standard mock bill data so the workspace is pre-populated
    const sampleBill = {
      customer_id: 'DEMO-BILL',
      utility: 'PSE&G',
      zip_code: '07102',
      rate_schedule: 'RS',
      meter_number: 'PSEG-9876543',
      bill_date: '2026-06-30',
      billing_period: '2026-06-01 to 2026-06-30',
      days: 30,
      previous_reading: 12450,
      current_reading: 13200,
      usage_kwh: 750.0,
      monthly_service_charge: 8.24,
      delivery_charge: 41.25,
      supply_charge: 81.00,
      tax: 8.41,
      total_bill: 138.90,
      average_daily_usage: 25.0,
      average_daily_cost: 4.63,
      effective_rate: 0.1852,
    };

    const sampleOcr = [
      { field_name: 'utility', ground_truth_value: 'PSE&G', extracted_value: 'PSE&G', confidence: 0.99, ocr_error_flag: false, bbox: '80,45,210,65' },
      { field_name: 'billing_period', ground_truth_value: '2026-06-01 to 2026-06-30', extracted_value: '2026-06-01 to 2026-06-30', confidence: 0.97, ocr_error_flag: false, bbox: '80,75,320,95' },
      { field_name: 'usage_kwh', ground_truth_value: '750.0', extracted_value: '750.0', confidence: 0.99, ocr_error_flag: false, bbox: '410,195,460,215' },
      { field_name: 'total_bill', ground_truth_value: '138.90', extracted_value: '138.90', confidence: 0.98, ocr_error_flag: false, bbox: '410,340,490,360' },
    ];

    const sampleExplanation = `### 📝 Bill Summary\nYour total bill from **PSE&G** for the billing period **2026-06-01 to 2026-06-30** is **$138.90** for **750.0 kWh** of electricity. This averages to about **$4.63 per day** at an effective rate of **$0.1852 per kWh**.\n\n---\n\n### 🔍 Charge Breakdown\n1. **Supply Charges (Generation): $81.00 (58.3%)** — *Controllable.*\n2. **Delivery Charges: $41.25 (29.7%)** — *Partially Controllable.*\n3. **State Taxes: $8.41 (6.1%)** — *Uncontrollable.*`;

    setBillData(sampleBill, sampleOcr, sampleExplanation);

    // 4. Redirect to overview
    navigate('/overview');
  }, [setBillData, navigate]);

  return (
    <div className="min-h-screen bg-bg-primary flex items-center justify-center p-4">
      <div className="text-center space-y-4">
        <RefreshCw size={24} className="animate-spin text-primary-blue mx-auto" />
        <p className="text-xs text-text-secondary font-semibold">Loading read-only demo workspace...</p>
      </div>
    </div>
  );
}
