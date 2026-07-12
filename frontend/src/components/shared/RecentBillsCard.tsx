import { useBill } from '../../context/BillContext.tsx';
import { useUserBills, useSetActiveBill, useDeleteBill } from '../../hooks/useUserBills.ts';
import { useAuth } from '../../context/AuthContext.tsx';
import { FileText, TrendingUp, TrendingDown, CheckCircle2, Trash2 } from 'lucide-react';

// ─── Mock history for guests / demo users ────────────────────────────────────
const MONTHS = [
  '2025-07', '2025-08', '2025-09', '2025-10', '2025-11', '2025-12',
  '2026-01', '2026-02', '2026-03', '2026-04', '2026-05', '2026-06',
];
const SEASONAL = [1.25, 1.30, 1.05, 0.85, 0.90, 1.00, 1.05, 1.02, 0.88, 0.82, 0.92, 1.00];

function buildMockHistory(uploadedBill: any) {
  return MONTHS.map((mo, i) => {
    const f = SEASONAL[i];
    const total = (uploadedBill.supply_charge + uploadedBill.delivery_charge + uploadedBill.tax) * f;
    return { id: `mock-${mo}`, month: mo, usage: uploadedBill.usage_kwh * f, total };
  });
}

interface RecentBillsCardProps {
  limit?: number;
  compact?: boolean;
}

const RecentBillsCard = ({ limit, compact = false }: RecentBillsCardProps) => {
  const { uploadedBill, hasBill, isPersistedBill, activeBillId } = useBill();
  const { user } = useAuth();

  // ── Authenticated: real DB bill list ──────────────────────────────────────
  const { data: billsData, isLoading } = useUserBills();
  const setActiveBill = useSetActiveBill();
  const deleteBill = useDeleteBill();

  if (!hasBill && !user) return null;

  // ── Authenticated user path: real DB records ───────────────────────────────
  if (isPersistedBill && user) {
    const bills = billsData?.bills ?? [];

    if (isLoading) {
      return (
        <div className="panel-operational space-y-2 animate-pulse">
          <div className="h-4 w-32 bg-bg-primary rounded" />
          <div className="h-3 w-full bg-bg-primary rounded" />
          <div className="h-3 w-full bg-bg-primary rounded" />
        </div>
      );
    }

    if (bills.length === 0) return null;

    const rows = limit ? [...bills].slice(0, limit) : bills;

    if (compact) {
      return (
        <div className="panel-operational space-y-2">
          <h3 className="text-xs font-bold text-text-secondary uppercase tracking-wider flex items-center gap-1.5 border-b border-border-hairline pb-3">
            <FileText size={14} className="text-primary-blue" /> Bill History
          </h3>
          <div className="space-y-1">
            {rows.map((bill) => {
              const isActive = bill.id === activeBillId;
              return (
                <div
                  key={bill.id}
                  className={`flex items-center justify-between py-1.5 border-b border-border-hairline last:border-0 gap-2 ${
                    isActive ? 'opacity-100' : 'opacity-75'
                  }`}
                >
                  <div className="flex items-center gap-1.5 min-w-0">
                    {isActive && <CheckCircle2 size={11} className="text-primary-blue shrink-0" />}
                    <span className="text-[11px] font-mono-numbers text-text-secondary truncate">
                      {bill.bill_date}
                    </span>
                  </div>
                  <span className="text-[11px] font-bold font-mono-numbers text-text-primary shrink-0">
                    ${(bill.total_bill ?? 0).toFixed(2)}
                  </span>
                  {!isActive && (
                    <button
                      onClick={() => setActiveBill.mutate(bill.id)}
                      disabled={setActiveBill.isPending}
                      className="text-[9px] text-primary-blue bg-primary-blue/10 hover:bg-primary-blue/20 border border-primary-blue/20 px-2 py-0.5 rounded-[4px] shrink-0 font-bold transition-colors"
                      title="Set as active bill"
                    >
                      Use
                    </button>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      );
    }

    // Full table view
    return (
      <div className="panel-operational space-y-4 overflow-hidden">
        <h3 className="text-xs font-bold text-text-secondary uppercase tracking-wider flex items-center gap-1.5 border-b border-border-hairline pb-3">
          <FileText size={14} className="text-primary-blue" /> Bill History
        </h3>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="text-[10px] uppercase text-text-secondary border-b border-border-hairline">
              <tr>
                <th className="py-2">Date</th>
                <th className="py-2">Utility</th>
                <th className="py-2 text-right">Usage (kWh)</th>
                <th className="py-2 text-right">Total Bill</th>
                <th className="py-2 text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((bill) => {
                const isActive = bill.id === activeBillId;
                return (
                  <tr
                    key={bill.id}
                    className={`border-b border-border-hairline hover:bg-bg-primary/30 transition-all ${
                      isActive ? 'bg-primary-blue/5' : ''
                    }`}
                  >
                    <td className="py-2 font-mono-numbers flex items-center gap-1.5">
                      {isActive && <CheckCircle2 size={11} className="text-primary-blue" />}
                      {bill.bill_date}
                    </td>
                    <td className="py-2 text-text-secondary">{bill.utility_provider ?? '—'}</td>
                    <td className="py-2 text-right font-mono-numbers">
                      {(bill.usage_kwh ?? 0).toFixed(0)} kWh
                    </td>
                    <td className="py-2 text-right font-mono-numbers font-bold text-text-primary">
                      ${(bill.total_bill ?? 0).toFixed(2)}
                    </td>
                    <td className="py-2 text-right">
                      <div className="flex items-center justify-end gap-2">
                        {!isActive && (
                          <button
                            onClick={() => setActiveBill.mutate(bill.id)}
                            disabled={setActiveBill.isPending}
                            className="text-[10px] text-text-primary bg-bg-surface border border-border-hairline hover:bg-bg-primary hover:border-text-secondary/50 px-2.5 py-1 rounded-[4px] font-bold transition-all shadow-sm disabled:opacity-50"
                          >
                            Set Active
                          </button>
                        )}
                        <button
                          onClick={() => {
                            if (confirm('Delete this bill?')) deleteBill.mutate(bill.id);
                          }}
                          disabled={deleteBill.isPending}
                          className="text-energy-red hover:text-energy-red/70 disabled:opacity-50"
                          title="Delete bill"
                        >
                          <Trash2 size={12} />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    );
  }

  // ── Guest / Demo path: synthetic mock history (unchanged) ──────────────────
  if (!hasBill || !uploadedBill) return null;
  const history = buildMockHistory(uploadedBill);
  const rows = limit ? history.slice(-limit).reverse() : [...history].reverse();

  if (compact) {
    return (
      <div className="panel-operational space-y-2">
        <h3 className="text-xs font-bold text-text-secondary uppercase tracking-wider flex items-center gap-1.5 border-b border-border-hairline pb-3">
          <FileText size={14} className="text-primary-blue" /> Recent Bills (Demo)
        </h3>
        <div className="space-y-1">
          {rows.map((row, i) => {
            const prev = rows[i + 1];
            const delta = prev ? ((row.total - prev.total) / prev.total) * 100 : 0;
            const up = delta > 0;
            return (
              <div key={row.month} className="flex items-center justify-between py-1.5 border-b border-border-hairline last:border-0">
                <span className="text-[11px] font-mono-numbers text-text-secondary">{row.month}</span>
                <span className="text-[11px] font-bold font-mono-numbers text-text-primary">
                  ${row.total.toFixed(2)}
                </span>
                {i < rows.length - 1 && (
                  <span className={`flex items-center gap-0.5 text-[10px] font-bold ${up ? 'text-alert-red' : 'text-savings-green'}`}>
                    {up ? <TrendingUp size={10} /> : <TrendingDown size={10} />}
                    {Math.abs(delta).toFixed(1)}%
                  </span>
                )}
              </div>
            );
          })}
        </div>
      </div>
    );
  }

  return (
    <div className="panel-operational space-y-4 overflow-hidden">
      <h3 className="text-xs font-bold text-text-secondary uppercase tracking-wider flex items-center gap-1.5 border-b border-border-hairline pb-3">
        <FileText size={14} className="text-primary-blue" /> 12-Month Billing History (Demo)
      </h3>
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead className="text-[10px] uppercase text-text-secondary border-b border-border-hairline">
            <tr>
              <th className="py-2">Month</th>
              <th className="py-2 text-right">Usage (kWh)</th>
              <th className="py-2 text-right">Total Bill</th>
              <th className="py-2 text-right">MoM</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => {
              const prev = rows[i + 1];
              const delta = prev ? ((row.total - prev.total) / prev.total) * 100 : 0;
              const up = delta > 0;
              return (
                <tr key={row.month} className="border-b border-border-hairline hover:bg-bg-primary/30 transition-all">
                  <td className="py-2 font-mono-numbers">{row.month}</td>
                  <td className="py-2 text-right font-mono-numbers">{row.usage.toFixed(0)} kWh</td>
                  <td className="py-2 text-right font-mono-numbers font-bold text-text-primary">${row.total.toFixed(2)}</td>
                  <td className={`py-2 text-right font-mono-numbers font-bold ${up ? 'text-alert-red' : 'text-savings-green'}`}>
                    {i < rows.length - 1 ? `${up ? '+' : ''}${delta.toFixed(1)}%` : '—'}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default RecentBillsCard;
