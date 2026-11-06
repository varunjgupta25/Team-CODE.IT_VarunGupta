import React, { useEffect, useState } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useLocation, Outlet } from 'react-router-dom';
import { PartnerHeader } from './PartnerHeader';
import { PartnerBottomNav } from './PartnerBottomNav';
import { PartnerAuthPage } from './PartnerAuthPage';
import { ToastContainer } from '../../components/common/ToastContainer';
import { WorkerDashboard } from '../../pages/worker/WorkerDashboard';
import { WorkerJobDetailsPage } from '../../pages/worker/WorkerJobDetailsPage';
import { WorkerEarningsPage } from '../../pages/worker/WorkerEarningsPage';
import { AdminPage } from '../../pages/admin/AdminPage';
import { ProfilePage } from '../../pages/ProfilePage';
import { useAuthStore } from '../../store/authStore';
import { ROLES, ADMIN_CLAIM_KEY } from '../../types';
import { isFirebaseConfigured, getFirebaseAuth } from '../../lib/firebase';
import { ShieldAlert, LogOut } from 'lucide-react';

// ─── Partner Layout Shell ───────────────────────────────────────────────────
function PartnerLayout() {
  const { user } = useAuthStore();
  const location = useLocation();
  const isPublicPage = location.pathname.startsWith('/login') || location.pathname.startsWith('/auth');

  return (
    <div className="min-h-screen bg-slate-200/60 flex justify-center selection:bg-amber-500 selection:text-white">
      <div className="w-full max-w-md min-w-[360px] min-h-screen bg-slate-50 flex flex-col shadow-2xl relative border-x border-slate-200 overflow-x-hidden">
        <PartnerHeader />
        <main className="flex-1 p-4 pb-24 overflow-y-auto overflow-x-hidden">
          <Outlet />
        </main>
        {user && !isPublicPage && <PartnerBottomNav />}
        <ToastContainer />
      </div>
    </div>
  );
}

// ─── Partner Any Role Guard (Worker or Admin for Profile) ───────────────────
function RequirePartner({ children }) {
  const { user, role, isInitialized, logout } = useAuthStore();

  if (!isInitialized) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[50vh] text-slate-500 text-xs font-semibold gap-2">
        <div className="w-6 h-6 border-2 border-amber-500 border-t-transparent rounded-full animate-spin" />
        <span>Verifying partner authentication...</span>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (role === ROLES.CUSTOMER) {
    return (
      <div className="p-6 text-center space-y-4 bg-white rounded-3xl border border-red-200 shadow-sm mt-8">
        <div className="w-12 h-12 rounded-2xl bg-red-100 text-red-600 flex items-center justify-center mx-auto">
          <ShieldAlert className="w-6 h-6" />
        </div>
        <div>
          <h2 className="text-base font-extrabold text-slate-900">Customer Account Detected</h2>
          <p className="text-xs text-slate-500 mt-1">
            You are signed in as a <span className="font-bold text-slate-800 uppercase">Customer</span>.
            The Partner App is reserved for Tradesmen and Operations Admins.
          </p>
          <p className="text-[11px] text-slate-400 mt-2">
            Please switch to the RepairBuddy Customer App or sign out to continue.
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

// ─── Worker Route Guard ─────────────────────────────────────────────────────
function RequireWorker({ children }) {
  const { user, role, isInitialized, logout } = useAuthStore();

  if (!isInitialized) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[50vh] text-slate-500 text-xs font-semibold gap-2">
        <div className="w-6 h-6 border-2 border-amber-500 border-t-transparent rounded-full animate-spin" />
        <span>Verifying partner authentication...</span>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  // Cross-App Portal Guard: If customer attempts to access Partner App
  if (role === ROLES.CUSTOMER) {
    return (
      <div className="p-6 text-center space-y-4 bg-white rounded-3xl border border-red-200 shadow-sm mt-8">
        <div className="w-12 h-12 rounded-2xl bg-red-100 text-red-600 flex items-center justify-center mx-auto">
          <ShieldAlert className="w-6 h-6" />
        </div>
        <div>
          <h2 className="text-base font-extrabold text-slate-900">Customer Account Detected</h2>
          <p className="text-xs text-slate-500 mt-1">
            You are signed in as a <span className="font-bold text-slate-800 uppercase">Customer</span>.
            The Partner App is reserved for Tradesmen and Operations Admins.
          </p>
          <p className="text-[11px] text-slate-400 mt-2">
            Please switch to the RepairBuddy Customer App or sign out to continue.
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

  if (role !== ROLES.WORKER) {
    return <Navigate to="/admin" replace />;
  }

  return children;
}

// ─── Admin Route Guard ──────────────────────────────────────────────────────
function RequireAdmin({ children }) {
  const { user, role, isInitialized, logout } = useAuthStore();
  const [isAdminVerifying, setIsAdminVerifying] = useState(isFirebaseConfigured());
  const [isAdminClaimValid, setIsAdminClaimValid] = useState(!isFirebaseConfigured());

  useEffect(() => {
    let isMounted = true;
    if (isInitialized && isFirebaseConfigured()) {
      Promise.resolve().then(async () => {
        const auth = getFirebaseAuth();
        const currentUser = auth?.currentUser;
        if (!currentUser) {
          if (isMounted) {
            setIsAdminClaimValid(false);
            setIsAdminVerifying(false);
          }
          return;
        }

        try {
          const result = await currentUser.getIdTokenResult(true);
          if (!isMounted) return;
          const hasAdminClaim =
            result.claims?.[ADMIN_CLAIM_KEY] === true || result.claims?.role === 'admin';
          setIsAdminClaimValid(Boolean(hasAdminClaim));
        } catch {
          if (!isMounted) return;
          setIsAdminClaimValid(false);
        } finally {
          if (isMounted) {
            setIsAdminVerifying(false);
          }
        }
      });
    }
    return () => {
      isMounted = false;
    };
  }, [user, isInitialized]);

  if (!isInitialized || isAdminVerifying) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[50vh] text-slate-500 text-xs font-semibold gap-2">
        <div className="w-6 h-6 border-2 border-purple-500 border-t-transparent rounded-full animate-spin" />
        <span>Verifying administrator permissions...</span>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (role !== ROLES.ADMIN || !isAdminClaimValid) {
    return (
      <div className="p-6 text-center space-y-4 bg-white rounded-3xl border border-red-200 shadow-sm mt-8">
        <div className="w-12 h-12 rounded-2xl bg-red-100 text-red-600 flex items-center justify-center mx-auto">
          <ShieldAlert className="w-6 h-6" />
        </div>
        <div>
          <h2 className="text-base font-extrabold text-slate-900">Administrator Access Denied</h2>
          <p className="text-xs text-slate-500 mt-1">
            Access to this console requires verified administrator privileges.
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

// ─── Partner Login Route ─────────────────────────────────────────────────────
function PartnerLoginRoute() {
  const { user, role } = useAuthStore();
  if (user) {
    if (role === ROLES.ADMIN) return <Navigate to="/admin" replace />;
    if (role === ROLES.WORKER) return <Navigate to="/worker" replace />;
  }
  return <PartnerAuthPage />;
}

// ─── Root Index Handler ──────────────────────────────────────────────────────
function PartnerIndexRedirect() {
  const { user, role } = useAuthStore();
  if (!user) return <Navigate to="/login" replace />;
  if (role === ROLES.ADMIN) return <Navigate to="/admin" replace />;
  return <Navigate to="/worker" replace />;
}

// ─── Main Partner App Component ──────────────────────────────────────────────
export default function PartnerApp() {
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
        <Route element={<PartnerLayout />}>
          {/* Public */}
          <Route path="/login" element={<PartnerLoginRoute />} />
          <Route path="/auth" element={<Navigate to="/login" replace />} />

          {/* Root Redirect */}
          <Route path="/" element={<PartnerIndexRedirect />} />

          {/* Worker Core Workflows */}
          <Route
            path="/worker"
            element={
              <RequireWorker>
                <WorkerDashboard />
              </RequireWorker>
            }
          />
          <Route
            path="/worker/job/:jobId"
            element={
              <RequireWorker>
                <WorkerJobDetailsPage />
              </RequireWorker>
            }
          />
          <Route
            path="/worker/earnings"
            element={
              <RequireWorker>
                <WorkerEarningsPage />
              </RequireWorker>
            }
          />

          {/* Admin Workflows */}
          <Route
            path="/admin"
            element={
              <RequireAdmin>
                <AdminPage />
              </RequireAdmin>
            }
          />

          {/* Shared Profile */}
          <Route
            path="/profile"
            element={
              <RequirePartner>
                <ProfilePage />
              </RequirePartner>
            }
          />

          {/* Catch-all */}
          <Route path="*" element={<PartnerIndexRedirect />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
