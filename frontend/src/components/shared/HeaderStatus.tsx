import { useBill } from '../../context/BillContext.tsx';

/**
 * Persistent bill metadata strip — shown in Header whenever a bill is loaded.
 * Extracted from the inline block in Header.tsx so it stays focused on layout.
 */
const HeaderStatus = () => {
  const { uploadedBill, hasBill } = useBill();

  if (!hasBill || !uploadedBill) return null;

  return (
    <div className="hidden lg:flex items-center gap-4 border-l border-border-hairline pl-4 text-xs">
      <div className="flex flex-col">
        <span className="text-[9px] text-text-secondary uppercase">Current Utility</span>
        <span className="font-mono-numbers text-text-primary font-bold">{uploadedBill.utility}</span>
      </div>
      <div className="flex flex-col border-l border-border-hairline pl-4">
        <span className="text-[9px] text-text-secondary uppercase">Billing Cycle</span>
        <span className="font-mono-numbers text-text-primary">
          {uploadedBill.bill_date || uploadedBill.billing_period}
        </span>
      </div>
      <div className="flex flex-col border-l border-border-hairline pl-4">
        <span className="text-[9px] text-text-secondary uppercase">Effective Rate</span>
        <span className="font-mono-numbers text-primary-blue font-bold">
          ${uploadedBill.effective_rate?.toFixed(4)}/kWh
        </span>
      </div>
    </div>
  );
};

export default HeaderStatus;
