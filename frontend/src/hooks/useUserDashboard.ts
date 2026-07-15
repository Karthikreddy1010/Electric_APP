/**
 * useUserDashboard — Single source of truth for the authenticated user's
 * active bill data and dashboard KPIs.
 *
 * Calls GET /users/me/dashboard which returns the parsed active bill,
 * forecast, insights, analysis results, and KPI summaries from the database.
 *
 * This replaces the legacy pattern of reading from BillContext sessionStorage.
 * All authenticated dashboard pages should derive bill data through this hook.
 */
import { useQuery, useQueryClient } from '@tanstack/react-query';
import apiClient from '../lib/apiClient.ts';
import { useAuth } from '../context/AuthContext.tsx';


export interface DashboardBill {
  id: string;
  filename: string;
  bill_date: string;
  total_bill: number;
  usage_kwh: number;
  is_active: boolean;
}

export interface DashboardKpis {
  current_bill: number;
  usage_kwh: number;
  effective_rate: number;
  forecast_next_month: number;
  bill_change_pct: number;
  usage_change_pct: number;
  rate_change_pct: number;
  state_rank: number;
}

export interface UserDashboardData {
  has_active_bill: boolean;
  active_bill_id: string | null;
  bills_count: number;
  bill_data: Record<string, unknown> | null;
  ocr_runs: unknown[] | null;
  analysis_results: Record<string, unknown> | null;
  insights: string[] | null;
  explanation: string | null;
  ai_status?: string;
  ai_explanation?: string;
  ai_recommendations?: string;
  ai_error_reason?: string;
  forecast_results: Record<string, unknown> | null;
  simulation_results: Record<string, unknown> | null;
  regional_comparison: Record<string, unknown> | null;
  recommendations: Record<string, unknown> | null;
  kpis: DashboardKpis | null;
  recent_bills: DashboardBill[];
}

export const USER_DASHBOARD_KEY = ['user', 'dashboard'] as const;

export function useUserDashboard() {
  const { status } = useAuth();
  return useQuery<UserDashboardData>({
    queryKey: USER_DASHBOARD_KEY,
    queryFn: async () => {
      const res = await apiClient.get('/users/me/dashboard');
      return res.data as UserDashboardData;
    },
    enabled: status === 'authenticated',
    staleTime: 2 * 60 * 1000,
    refetchInterval: (query) => {
      const data = query.state.data;
      if (data && data.ai_status === 'generating') {
        return 3000; // Poll every 3 seconds while background AI worker generates response
      }
      return false;
    },
    retry: (failureCount, error: unknown) => {
      const status = (error as { response?: { status?: number } })?.response?.status;
      if (status === 401 || status === 403) return false;
      return failureCount < 2;
    },
  });
}

/** Call this to force-refresh the dashboard after a new bill upload */
export function useInvalidateDashboard() {
  const queryClient = useQueryClient();
  return () => {
    queryClient.invalidateQueries({ queryKey: USER_DASHBOARD_KEY });
    queryClient.invalidateQueries({ queryKey: ['user', 'bills'] });
  };
}
