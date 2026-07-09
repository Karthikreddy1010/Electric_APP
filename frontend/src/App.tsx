import { useState } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import Header from './components/Header.tsx';
import Dashboard from './components/Dashboard.tsx';

const queryClient = new QueryClient();

const defaultBill = {
  customer_id: "EXAMPLE-BILL",
  utility: "PSE&G",
  zip_code: "07102",
  rate_schedule: "RS",
  meter_number: "PSEG-9876543",
  bill_date: "2026-06-30",
  billing_period: "2026-06-01 to 2026-06-30",
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
  effective_rate: 0.1852
};

const defaultOcr = [
  {"field_name": "utility", "ground_truth_value": "PSE&G", "extracted_value": "PSE&G", "confidence": 0.99, "ocr_error_flag": false, "bbox": "80,45,210,65"},
  {"field_name": "billing_period", "ground_truth_value": "2026-06-01 to 2026-06-30", "extracted_value": "2026-06-01 to 2026-06-30", "confidence": 0.97, "ocr_error_flag": false, "bbox": "80,75,320,95"},
  {"field_name": "usage_kwh", "ground_truth_value": "750.0", "extracted_value": "750.0", "confidence": 0.99, "ocr_error_flag": false, "bbox": "410,195,460,215"},
  {"field_name": "total_bill", "ground_truth_value": "138.90", "extracted_value": "138.90", "confidence": 0.98, "ocr_error_flag": false, "bbox": "410,340,490,360"}
];

const defaultExplanation = `### 📝 Bill Summary
Your total bill from **PSE&G** for the billing period **2026-06-01 to 2026-06-30** is **$138.90** for **750.0 kWh** of electricity. This averages to about **$4.63 per day** at an effective rate of **$0.1852 per kWh**.

---

### 🔍 Charge Breakdown & Controllability
1. **Supply Charges (Generation): $81.00 (58.3%)** — *Controllable.* This pays for the actual electricity consumed. Lowering your overall consumption will directly reduce this amount.
2. **Delivery Charges (Distribution & Transmission): $41.25 (29.7%)** — *Partially Controllable.* This includes a fixed service charge of **$8.24** (5.9%) for connection maintenance and variable fees for local line infrastructure.
3. **State Taxes & Adjustments: $8.41 (6.1%)** — *Uncontrollable.* Mandatory state sales tax of 6.625%.

---

### 📈 Why Your Bill Changed
Based on seasonal heating and cooling trends:
- **Weather Impact**: Higher outdoor temperatures increase cooling loads, causing high air conditioning demand. Air conditioning accounts for approximately **18% to 25%** of summer usage spikes.
- **Wholesale Jitter**: Supply rates fluctuated slightly based on grid congestion, but the standard tariff rate remains stable at the fixed BGS rate schedule.

---

### 💡 Savings Opportunities & Recommendations
- **Peak Hours Shift**: High transmission costs occur during peak grid hours. Shift laundry, dishwasher loads, and EV charging to off-peak times (typically 10 PM to 8 AM) to mitigate grid strain.
- **Thermostat Adjustments**: Setting the cooling thermostat to 78°F instead of 72°F can reduce supply charges by **8-12%** during peak summer months.
- **Smart Thermostat Program**: Enrolling in the PSE&G smart energy program provides a one-time bill credit and automatic peak usage trimming.
`;

function App() {
  const [activeTab, setActiveTab] = useState('Bill Analysis');
  const [uploadedBill, setUploadedBill] = useState<any>(defaultBill);
  const [ocrRuns, setOcrRuns] = useState<any[] | null>(defaultOcr);
  const [billExplanation, setBillExplanation] = useState<string | null>(defaultExplanation);

  return (
    <QueryClientProvider client={queryClient}>
      <div className="min-h-screen bg-background flex flex-col">
        <Header 
          activeTab={activeTab} 
          setActiveTab={setActiveTab} 
        />
        <main className="flex-1 max-w-7xl mx-auto w-full px-4 py-8">
          <Dashboard 
            activeTab={activeTab} 
            setActiveTab={setActiveTab}
            uploadedBill={uploadedBill} 
            setUploadedBill={setUploadedBill}
            ocrRuns={ocrRuns}
            setOcrRuns={setOcrRuns}
            billExplanation={billExplanation}
            setBillExplanation={setBillExplanation}
          />
        </main>
      </div>
    </QueryClientProvider>
  );
}

export default App;
