/**
 * DataStates — shared loading / error / empty primitives for data-backed panels.
 *
 * Every panel that renders server data should render one of these instead of a
 * blank box or invented placeholder numbers. All three use design tokens
 * (--bg-surface, --text-primary, …) so they render correctly in both themes.
 */
import type { ReactNode } from 'react';
import { AlertTriangle, Inbox, RefreshCw } from 'lucide-react';

interface StateProps {
  /** Matches the height of the panel being replaced, e.g. "h-64". */
  className?: string;
}

/** Shown while a query is in flight. */
export function LoadingState({
  label = 'Loading…',
  className = 'h-64',
}: StateProps & { label?: string }) {
  return (
    <div
      className={`flex flex-col items-center justify-center gap-3 ${className}`}
      role="status"
      aria-live="polite"
    >
      <div className="w-6 h-6 border-2 border-primary-blue border-t-transparent rounded-full animate-spin" />
      <span className="text-xs text-text-secondary font-mono">{label}</span>
    </div>
  );
}

/** Shown when a query fails. `onRetry` renders a retry affordance when provided. */
export function ErrorState({
  title = 'Could not load this data',
  message,
  onRetry,
  className = 'h-64',
}: StateProps & { title?: string; message?: string; onRetry?: () => void }) {
  return (
    <div
      className={`flex flex-col items-center justify-center gap-3 text-center px-6 ${className}`}
      role="alert"
    >
      <div className="w-10 h-10 rounded-full bg-alert-red/10 flex items-center justify-center">
        <AlertTriangle size={18} className="text-alert-red" aria-hidden="true" />
      </div>
      <div className="space-y-1">
        <p className="text-sm font-semibold text-text-primary">{title}</p>
        {message && <p className="text-xs text-text-secondary max-w-sm">{message}</p>}
      </div>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-primary-blue hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-blue rounded-[4px] px-2 py-1"
        >
          <RefreshCw size={12} aria-hidden="true" /> Try again
        </button>
      )}
    </div>
  );
}

/**
 * Shown when a query succeeds but there is genuinely nothing to display —
 * a new account with no bills, a meter with no readings yet.
 *
 * This is deliberately used in place of sample data: showing invented numbers
 * as if they were the user's own is worse than showing nothing.
 */
export function EmptyState({
  title,
  message,
  action,
  className = 'h-64',
}: StateProps & { title: string; message?: string; action?: ReactNode }) {
  return (
    <div className={`flex flex-col items-center justify-center gap-3 text-center px-6 ${className}`}>
      <div className="w-10 h-10 rounded-full bg-bg-secondary flex items-center justify-center">
        <Inbox size={18} className="text-text-secondary" aria-hidden="true" />
      </div>
      <div className="space-y-1">
        <p className="text-sm font-semibold text-text-primary">{title}</p>
        {message && <p className="text-xs text-text-secondary max-w-sm">{message}</p>}
      </div>
      {action}
    </div>
  );
}
