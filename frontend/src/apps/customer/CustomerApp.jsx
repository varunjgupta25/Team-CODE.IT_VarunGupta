import React, { useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useLocation, Outlet } from 'react-router-dom';
import { CustomerHeader } from './CustomerHeader';
import { CustomerBottomNav } from './CustomerBottomNav';
import { CustomerAuthPage } from './CustomerAuthPage';
import { ToastContainer } from '../../components/common/ToastContainer';
import { CustomerHome } from '../../pages/customer/CustomerHome';
import { CreateJobPage } from '../../pages/customer/CreateJobPage';
import { MatchedWorkersPage } from '../../pages/customer/MatchedWorkersPage';
import { JobStatusPage } from '../../pages/customer/JobStatusPage';
import { ReviewPage } from '../../pages/customer/ReviewPage';
import { ProfilePage } from '../../pages/ProfilePage';
import { useAuthStore } from '../../store/authStore';
import { ROLES } from '../../types';
import { ShieldAlert, LogOut } from 'lucide-react';

// ─── Customer Layout Shell ───────────────────────────────────────────────────
function CustomerLayout() {
  const { user } = useAuthStore();
  const location = useLocation();
  const isPublicPage = location.pathname.startsWith('/login') || location.pathname.startsWith('/auth');

  return (
    <div className="min-h-screen bg-slate-200/60 flex justify-center selection:bg-brand-500 selection:text-white">
      <div className="w-full max-w-md min-w-[360px] min-h-screen bg-slate-50 flex flex-col shadow-2xl relative border-x border-slate-200 overflow-x-hidden">
        <CustomerHeader />
        <main className="flex-1 p-4 pb-24 overflow-y-auto overflow-x-hidden">
          <Outlet />
        </main>
        {user && !isPublicPage && <CustomerBottomNav />}
        <ToastContainer />
      </div>
    </div>
  );
}

// ─── Customer Route Guard ────────────────────────────────────────────────────
function RequireCustomer({ children }) {
  const { user, role, isInitialized, logout } = useAuthStore();

  if (!isInitialized) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[50vh] text-slate-500 text-xs font-semibold gap-2">
        <div className="w-6 h-6 border-2 border-brand-500 border-t-transparent rounded-full animate-spin" />
        <span>Verifying authentication session...</span>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  // Cross-App Portal Guard: If logged in as worker or admin in Customer App
  if (role !== ROLES.CUSTOMER) {
    return (
      <div className="p-6 text-center space-y-4 bg-white rounded-3xl border border-red-200 shadow-sm mt-8">
        <div className="w-12 h-12 rounded-2xl bg-red-100 text-red-600 flex items-center justify-center mx-auto">
          <ShieldAlert className="w-6 h-6" />
        </div>
        <div>
          <h2 className="text-base font-extrabold text-slate-900">Partner Account Detected</h2>
          <p className="text-xs text-slate-500 mt-1">
            You are signed in as a <span className="font-bold text-slate-800 uppercase">{role}</span>.
            The Customer App is reserved for household service bookings.
          </p>
          <p className="text-[11px] text-slate-400 mt-2">
            Please switch to the RepairBuddy Partner App or sign out to continue.
          </p>
        </div>
        <button
          onClick={() => logout()}
          className="w-full py-2.5 rounded-xl bg-red-600 hover:bg-red-700 text-white font-bold text-xs flex items-center justify-center gap-2 shadow-sm transition"
        >
          <LogOut className="w-4 h-4" />
          <span>Sign Out</span>
        </button>
      </div>
    );
  }

  return children;
}

// ─── Public Login Redirect ───────────────────────────────────────────────────
function CustomerLoginRoute() {
  const { user, role } = useAuthStore();
  if (user && role === ROLES.CUSTOMER) {
    return <Navigate to="/" replace />;
  }
  return <CustomerAuthPage />;
}

// ─── Main Customer App Component ─────────────────────────────────────────────
export default function CustomerApp() {
  const initAuth = useAuthStore((state) => state.initAuth);

  useEffect(() => {
    const unsubscribe = initAuth();
    return () => {
      if (typeof unsubscribe === 'function') unsubscribe();
    };
  }, [initAuth]);

  return (
    <BrowserRouter>
      <Routes>
        <Route element={<CustomerLayout />}>
          {/* Public */}
          <Route path="/login" element={<CustomerLoginRoute />} />
          <Route path="/auth" element={<Navigate to="/login" replace />} />

          {/* Customer Core Workflows */}
          <Route
            path="/"
            element={
              <RequireCustomer>
                <CustomerHome />
              </RequireCustomer>
            }
          />
          <Route
            path="/customer/create-job"
            element={
              <RequireCustomer>
                <CreateJobPage />
              </RequireCustomer>
            }
          />
          <Route
            path="/customer/match/:jobId"
            element={
              <RequireCustomer>
                <MatchedWorkersPage />
              </RequireCustomer>
            }
          />
          <Route
            path="/customer/status"
            element={
              <RequireCustomer>
                <JobStatusPage />
              </RequireCustomer>
            }
          />
          <Route
            path="/customer/status/:jobId"
            element={
              <RequireCustomer>
                <JobStatusPage />
              </RequireCustomer>
            }
          />
          <Route
            path="/customer/review/:jobId"
            element={
              <RequireCustomer>
                <ReviewPage />
              </RequireCustomer>
            }
          />

          {/* Profile */}
          <Route
            path="/profile"
            element={
              <RequireCustomer>
                <ProfilePage />
              </RequireCustomer>
            }
          />

          {/* Catch-all */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

