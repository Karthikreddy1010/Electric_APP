import { lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route, Navigate, Outlet } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BillContextProvider } from './context/BillContext.tsx';
import { NavigationProvider } from './context/NavigationContext.tsx';
import { AuthContextProvider, useAuth } from './context/AuthContext.tsx';

import LandingPage from './pages/LandingPage.tsx';
import LoginPage from './pages/LoginPage.tsx';
import SignupPage from './pages/SignupPage.tsx';
import ForgotPasswordPage from './pages/ForgotPasswordPage.tsx';
import DemoPage from './pages/DemoPage.tsx';
import VerifyEmailPage from './pages/VerifyEmailPage.tsx';
import ResetPasswordPage from './pages/ResetPasswordPage.tsx';

import OverviewPage from './pages/OverviewPage.tsx';
import BillPage from './pages/BillPage.tsx';
import ImpactPage from './pages/ImpactPage.tsx';
import AdvancedAnalysisPage from './pages/AdvancedAnalysisPage.tsx';
import SettingsPage from './pages/SettingsPage.tsx';

import WorkspaceShell from './components/layout/WorkspaceShell.tsx';


// Lazy-loaded heavy pages (D3, Leaflet, Monte Carlo charts)
const RegionalPage = lazy(() => import('./pages/RegionalPage.tsx'));
const ForecastPage = lazy(() => import('./pages/ForecastPage.tsx'));


function LazyFallback() {
  return (
    <div className="flex items-center justify-center py-32">
      <div className="w-6 h-6 border-2 border-primary-blue border-t-transparent rounded-full animate-spin" />
    </div>
  );
}

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: (failureCount, error: unknown) => {
      // Don't retry on 401
      const status = (error as { response?: { status?: number } })?.response?.status;
      if (status === 401 || status === 403) return false;
      return failureCount < 2;
    }},
  },
});

// Route Guard for Protected Dashboard Pages
function ProtectedRoute() {
  const { status } = useAuth();

  if (status === 'loading') {
    return (
      <div className="min-h-screen flex items-center justify-center bg-bg-primary">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-primary-blue border-t-transparent rounded-full animate-spin" />
          <span className="text-xs text-text-secondary font-mono">Restoring session...</span>
        </div>
      </div>
    );
  }

  if (status === 'unauthenticated' && sessionStorage.getItem('is_demo_mode') !== 'true') {
    return <Navigate to="/login" replace />;
  }

  // Unverified users get redirected to a pending verification page
  if (status === 'unverified') {
    return <Navigate to="/verify-pending" replace />;
  }

  return <WorkspaceShell />;
}

// Route Guard for Public Auth Pages (Redirect to dashboard if already logged in)
function PublicAuthRoute() {
  const { status } = useAuth();

  if (status === 'loading') {
    return (
      <div className="min-h-screen flex items-center justify-center bg-bg-primary">
        <div className="w-6 h-6 border-2 border-primary-blue border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (status === 'authenticated' || sessionStorage.getItem('is_demo_mode') === 'true') {
    return <Navigate to="/overview" replace />;
  }

  return <Outlet />;
}

// Email Verification Pending Page (inline — simple banner)
function VerifyPendingPage() {
  const { logout } = useAuth();
  return (
    <div className="min-h-screen flex items-center justify-center bg-bg-primary px-4">
      <div className="max-w-md w-full bg-bg-surface border border-border-hairline rounded-lg p-8 text-center space-y-4">
        <div className="w-14 h-14 bg-warning-amber/10 rounded-full flex items-center justify-center mx-auto">
          <span className="text-2xl">✉️</span>
        </div>
        <h2 className="text-xl font-bold text-text-primary">Check your inbox</h2>
        <p className="text-sm text-text-secondary">
          We sent a verification link to your email address. Click the link to activate your account and access the dashboard.
        </p>
        <p className="text-xs text-text-secondary">Didn't get the email? Check your spam folder.</p>
        <button
          onClick={async () => { await logout(); }}
          className="text-xs text-text-secondary hover:text-text-primary underline"
        >
          Back to Login
        </button>
      </div>
    </div>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter basename="/app">
        <AuthContextProvider>
          <BillContextProvider>
            <NavigationProvider>
              <Routes>
                {/* Public General Routes */}
                <Route path="/" element={<LandingPage />} />
                <Route path="/demo" element={<DemoPage />} />
                <Route path="/verify-email" element={<VerifyEmailPage />} />
                <Route path="/reset-password" element={<ResetPasswordPage />} />
                <Route path="/verify-pending" element={<VerifyPendingPage />} />

                {/* Public Auth Routes */}
                <Route element={<PublicAuthRoute />}>
                  <Route path="/login" element={<LoginPage />} />
                  <Route path="/signup" element={<SignupPage />} />
                  <Route path="/forgot-password" element={<ForgotPasswordPage />} />
                </Route>

                {/* Protected Dashboard Routes */}
                <Route element={<ProtectedRoute />}>
                  <Route path="/dashboard" element={<Navigate to="/overview" replace />} />
                  <Route path="/overview" element={<OverviewPage />} />
                  <Route path="/bill-analysis" element={<BillPage />} />
                  <Route path="/impact" element={<ImpactPage />} />
                  <Route path="/advanced-analysis" element={<AdvancedAnalysisPage />} />
                  <Route path="/regional-insights" element={<Suspense fallback={<LazyFallback />}><RegionalPage /></Suspense>} />
                  <Route path="/forecast" element={<Suspense fallback={<LazyFallback />}><ForecastPage /></Suspense>} />

                  <Route path="/settings" element={<SettingsPage />} />
                </Route>

                {/* Fallback */}
                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </NavigationProvider>
          </BillContextProvider>
        </AuthContextProvider>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
