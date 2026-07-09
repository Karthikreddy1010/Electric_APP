import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useUserDashboard, USER_DASHBOARD_KEY } from '../hooks/useUserDashboard.ts';
import { USER_BILLS_KEY } from '../hooks/useUserBills.ts';
import apiClient from '../lib/apiClient.ts';

// ─── Typed Interfaces ─────────────────────────────────────────────────────────

export interface OcrRun {
  field_name: string;
  ground_truth_value: string;
  extracted_value: string;
  confidence: number;
  ocr_error_flag: boolean;
  bbox: string;
}

export interface BreakdownItem {
  name: string;
  value: number;
  pct: number;
  controllable: string;
  source: string;
}

export interface SensitivityItem {
  label: string;
  base_value: number;
  increase_10_diff: number;
  increase_10_pct: number;
  decrease_10_diff: number;
  decrease_10_pct: number;
}

export interface RankingItem {
  label: string;
  value: number;
  share_pct: number;
}

export interface DriversData {
  highest_contributor: string;
  highest_pct: number;
  fixed_cost: number;
  fixed_pct: number;
  variable_cost: number;
  variable_pct: number;
  tax_cost: number;
  market_controlled: string;
  policy_regulatory: string;
}

export interface BillData {
  customer_id: string;
  utility: string;
  zip_code: string;
  rate_schedule: string;
  meter_number: string;
  bill_date: string;
  billing_period: string;
  days: number;
  previous_reading: number;
  current_reading: number;
  usage_kwh: number;
  monthly_service_charge: number;
  delivery_charge: number;
  supply_charge: number;
  tax: number;
  total_bill: number;
  average_daily_usage: number;
  average_daily_cost: number;
  effective_rate: number;
  analysis_results?: { breakdown: BreakdownItem[] };
  sensitivity?: SensitivityItem[];
  ranking?: RankingItem[];
  drivers?: DriversData;
  insights?: string[];
  contribution?: Record<string, number>;
}

// ─── Context Interface ────────────────────────────────────────────────────────

interface BillContextType {
  uploadedBill: BillData | null;
  ocrRuns: OcrRun[] | null;
  billExplanation: string | null;
  hasBill: boolean;
  /** For authenticated users, the database ID of the active bill */
  activeBillId: string | null;
  /** True if the current bill is from the database (authenticated user) */
  isPersistedBill: boolean;
  setBillData: (bill: BillData | null, ocr: OcrRun[] | null, explanation: string | null) => void;
  clearBillData: () => void;
  /** Switch the active bill to a different DB record (authenticated users only) */
  setActiveBillById: (id: string) => Promise<void>;
}

const BillContext = createContext<BillContextType | null>(null);

// ─── Helper: read session auth flag ──────────────────────────────────────────
// We detect auth status by whether the dashboard query has data or a cookie is
// present, rather than importing AuthContext (avoids circular dependency).
function isGuestOrDemo(): boolean {
  return sessionStorage.getItem('is_demo_mode') === 'true';
}

// ─── Provider ─────────────────────────────────────────────────────────────────

export const BillContextProvider = ({ children }: { children: React.ReactNode }) => {
  // ── Guest / Demo state (sessionStorage-backed, unchanged) ──────────────────
  const [guestBill, setGuestBill] = useState<BillData | null>(null);
  const [guestOcr, setGuestOcr] = useState<OcrRun[] | null>(null);
  const [guestExplanation, setGuestExplanation] = useState<string | null>(null);

  // Restore guest state from sessionStorage on mount
  useEffect(() => {
    try {
      const cachedBill = sessionStorage.getItem('bill_data');
      const cachedOcr = sessionStorage.getItem('ocr_data');
      const cachedExplanation = sessionStorage.getItem('explain_data');
      setGuestBill(cachedBill ? JSON.parse(cachedBill) : null);
      setGuestOcr(cachedOcr ? JSON.parse(cachedOcr) : null);
      setGuestExplanation(cachedExplanation ?? null);
    } catch (e) {
      console.error('Failed to restore cached bill state:', e);
    }
  }, []);

  // ── Authenticated state (TanStack Query / DB-backed) ──────────────────────
  const { data: dashboardData } = useUserDashboard();
  const queryClient = useQueryClient();

  // Derive whether this is an authenticated session with a real DB bill
  const hasDbBill = !!(dashboardData?.has_active_bill && dashboardData?.bill_data);

  // Build a BillData-shaped object from the DB record
  const dbBill: BillData | null = hasDbBill
    ? {
        ...(dashboardData!.bill_data as unknown as BillData),
        analysis_results: dashboardData!.analysis_results as BillData['analysis_results'],
        sensitivity: (dashboardData!.analysis_results as Record<string, unknown>)?.sensitivity as SensitivityItem[] ?? undefined,
        ranking: (dashboardData!.analysis_results as Record<string, unknown>)?.ranking as RankingItem[] ?? undefined,
        drivers: (dashboardData!.analysis_results as Record<string, unknown>)?.drivers as DriversData ?? undefined,
        insights: dashboardData!.insights as string[] ?? undefined,
        contribution: undefined,
      }
    : null;

  const dbOcr = dashboardData?.ocr_runs as OcrRun[] | null ?? null;
  const dbExplanation = dashboardData?.explanation ?? null;

  // ── Unified surface ───────────────────────────────────────────────────────
  // Precedence: DB bill (if authenticated) > guest bill (demo/anonymous)
  // The guest override is kept for the WelcomeWizard mock-upload path which
  // should still show the freshly scanned bill before the DB refreshes.
  const [guestOverride, setGuestOverride] = useState(false);

  const uploadedBill = (hasDbBill && !guestOverride) ? dbBill : guestBill;
  const ocrRuns      = (hasDbBill && !guestOverride) ? dbOcr  : guestOcr;
  const billExplanation = (hasDbBill && !guestOverride) ? dbExplanation : guestExplanation;
  const hasBill = !!(uploadedBill);
  const activeBillId = dashboardData?.active_bill_id ?? null;
  const isPersistedBill = hasDbBill && !guestOverride;

  // ── Actions ───────────────────────────────────────────────────────────────

  const setBillData = useCallback((
    bill: BillData | null,
    ocr: OcrRun[] | null,
    explanation: string | null,
  ) => {
    // Always update the guest/local state (used by WelcomeWizard, demo mode)
    setGuestBill(bill);
    setGuestOcr(ocr);
    setGuestExplanation(explanation);

    // Persist to sessionStorage for guests only
    if (isGuestOrDemo() || !hasDbBill) {
      try {
        if (bill) sessionStorage.setItem('bill_data', JSON.stringify(bill));
        else sessionStorage.removeItem('bill_data');
        if (ocr) sessionStorage.setItem('ocr_data', JSON.stringify(ocr));
        else sessionStorage.removeItem('ocr_data');
        if (explanation) sessionStorage.setItem('explain_data', explanation);
        else sessionStorage.removeItem('explain_data');
      } catch (e) {
        console.error('Failed to cache bill state:', e);
      }
    }

    // If there is a DB bill, show the new local one temporarily while the
    // dashboard query refreshes in the background
    if (hasDbBill && bill) {
      setGuestOverride(true);
    }
  }, [hasDbBill]);

  // When the dashboard query refreshes with fresh DB data, clear the local override
  useEffect(() => {
    if (hasDbBill && guestOverride) {
      setGuestOverride(false);
    }
  }, [dashboardData?.active_bill_id]);

  const clearBillData = useCallback(() => {
    setGuestBill(null);
    setGuestOcr(null);
    setGuestExplanation(null);
    setGuestOverride(false);
    try {
      sessionStorage.removeItem('bill_data');
      sessionStorage.removeItem('ocr_data');
      sessionStorage.removeItem('explain_data');
    } catch { /* ignore */ }
  }, []);

  const setActiveBillById = useCallback(async (id: string) => {
    await apiClient.post('/users/me/active-bill', { bill_id: id });
    setGuestOverride(false); // Show DB bill for the new active
    queryClient.invalidateQueries({ queryKey: USER_DASHBOARD_KEY });
    queryClient.invalidateQueries({ queryKey: USER_BILLS_KEY });
  }, [queryClient]);

  return (
    <BillContext.Provider value={{
      uploadedBill,
      ocrRuns,
      billExplanation,
      hasBill,
      activeBillId,
      isPersistedBill,
      setBillData,
      clearBillData,
      setActiveBillById,
    }}>
      {children}
    </BillContext.Provider>
  );
};

// ─── Hook ─────────────────────────────────────────────────────────────────────

export const useBill = () => {
  const context = useContext(BillContext);
  if (!context) throw new Error('useBill must be used within a BillContextProvider');
  return context;
};
