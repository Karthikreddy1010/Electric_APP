/**
 * useUserBills — Fetches the full list of bills for the authenticated user.
 *
 * Calls GET /users/me/bills which returns all uploaded bills from the database.
 * Shared across: Header, Overview, Settings, Bill Analysis history drawer.
 *
 * This replaces the legacy sessionStorage-backed single-bill pattern for
 * authenticated users. Guest/demo users still use BillContext directly.
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import apiClient from '../lib/apiClient.ts';
import { useAuth } from '../context/AuthContext.tsx';
import { USER_DASHBOARD_KEY } from './useUserDashboard.ts';

export interface UserBillListItem {
  id: string;
  filename: string;
  bill_date: string;
  billing_period: string | null;
  utility_provider: string | null;
  usage_kwh: number | null;
  total_bill: number | null;
  is_archived: boolean;
  created_at: string | null;
  is_active: boolean;
}

export const USER_BILLS_KEY = ['user', 'bills'] as const;

export function useUserBills(opts?: {
  search?: string;
  sort_by?: string;
  filter_by?: string;
}) {
  const { status } = useAuth();
  const { search, sort_by = 'date_desc', filter_by = 'all' } = opts ?? {};

  return useQuery<{ bills: UserBillListItem[] }>({
    queryKey: [...USER_BILLS_KEY, search, sort_by, filter_by],
    queryFn: async () => {
      const params: Record<string, string> = { sort_by, filter_by };
      if (search) params.search = search;
      const res = await apiClient.get('/users/me/bills', { params });
      return res.data as { bills: UserBillListItem[] };
    },
    enabled: status === 'authenticated',
    staleTime: 2 * 60 * 1000,
    retry: (failureCount, error: unknown) => {
      const status = (error as { response?: { status?: number } })?.response?.status;
      if (status === 401 || status === 403) return false;
      return failureCount < 2;
    },
  });
}

/** Mutation: set a different bill as the active bill */
export function useSetActiveBill() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (billId: string) => {
      await apiClient.post('/users/me/active-bill', { bill_id: billId });
    },
    onSuccess: () => {
      // Refresh both the dashboard (active bill data) and the bill list (is_active flags)
      queryClient.invalidateQueries({ queryKey: USER_DASHBOARD_KEY });
      queryClient.invalidateQueries({ queryKey: USER_BILLS_KEY });
    },
  });
}

/** Mutation: delete a bill from the user's history */
export function useDeleteBill() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (billId: string) => {
      await apiClient.delete(`/users/me/bills/${billId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: USER_DASHBOARD_KEY });
      queryClient.invalidateQueries({ queryKey: USER_BILLS_KEY });
    },
  });
}
