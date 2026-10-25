import React from 'react';
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { MobileLayout } from './components/layout/MobileLayout';
import { CustomerHome } from './pages/customer/CustomerHome';
import { CreateJobPage } from './pages/customer/CreateJobPage';
import { MatchedWorkersPage } from './pages/customer/MatchedWorkersPage';
import { JobStatusPage } from './pages/customer/JobStatusPage';
import { ReviewPage } from './pages/customer/ReviewPage';
import { WorkerDashboard } from './pages/worker/WorkerDashboard';
import { WorkerJobDetailsPage } from './pages/worker/WorkerJobDetailsPage';
import { WorkerEarningsPage } from './pages/worker/WorkerEarningsPage';
import { AuthPage } from './pages/AuthPage';
import { ProfilePage } from './pages/ProfilePage';
import { AdminPage } from './pages/admin/AdminPage';
import { useAuthStore } from './store/authStore';
import { ROLES } from './types';

// ─── Redirect already-logged-in users away from /login ───────────────────────
function LoginRoute() {
  const { user, role } = useAuthStore();
  if (user) {
    if (role === ROLES.ADMIN) return <Navigate to="/admin" replace />;
    return <Navigate to={role === ROLES.WORKER ? '/worker' : '/'} replace />;
  }
  return <AuthPage />;
}

// ─── Protect any route by required role ──────────────────────────────────────
function RequireRole({ role: requiredRole, children }) {
  const { user, role } = useAuthStore();
  const location = useLocation();

  if (!user) {
    // Not logged in → send to /login, save where they were
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (requiredRole && role !== requiredRole) {
    // Wrong role → send to their home
    if (role === ROLES.ADMIN) return <Navigate to="/admin" replace />;
    return <Navigate to={role === ROLES.WORKER ? '/worker' : '/'} replace />;
  }

  return children;
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<MobileLayout />}>

          {/* ── Public ──────────────────────────────────────── */}
          <Route path="/login" element={<LoginRoute />} />
          <Route path="/auth"  element={<Navigate to="/login" replace />} />

          {/* ── Customer-only ────────────────────────────────── */}
          <Route
            path="/"
            element={
              <RequireRole role={ROLES.CUSTOMER}>
                <CustomerHome />
              </RequireRole>
            }
          />
          <Route
            path="/customer/create-job"
            element={
              <RequireRole role={ROLES.CUSTOMER}>
                <CreateJobPage />
              </RequireRole>
            }
          />
          <Route
            path="/customer/match/:jobId"
            element={
              <RequireRole role={ROLES.CUSTOMER}>
                <MatchedWorkersPage />
              </RequireRole>
            }
          />
          <Route
            path="/customer/status"
            element={
              <RequireRole role={ROLES.CUSTOMER}>
                <JobStatusPage />
              </RequireRole>
            }
          />
          <Route
            path="/customer/status/:jobId"
            element={
              <RequireRole role={ROLES.CUSTOMER}>
                <JobStatusPage />
              </RequireRole>
            }
          />
          <Route
            path="/customer/review/:jobId"
            element={
              <RequireRole role={ROLES.CUSTOMER}>
                <ReviewPage />
              </RequireRole>
            }
          />

          {/* ── Worker-only ──────────────────────────────────── */}
          <Route
            path="/worker"
            element={
              <RequireRole role={ROLES.WORKER}>
                <WorkerDashboard />
              </RequireRole>
            }
          />
          <Route
            path="/worker/job/:jobId"
            element={
              <RequireRole role={ROLES.WORKER}>
                <WorkerJobDetailsPage />
              </RequireRole>
            }
          />
          <Route
            path="/worker/earnings"
            element={
              <RequireRole role={ROLES.WORKER}>
                <WorkerEarningsPage />
              </RequireRole>
            }
          />

          {/* ── Admin-only ───────────────────────────────────── */}
          <Route
            path="/admin"
            element={
              <RequireRole role={ROLES.ADMIN}>
                <AdminPage />
              </RequireRole>
            }
          />

          {/* ── Shared (any logged-in user) ───────────────────── */}
          <Route
            path="/profile"
            element={
              <RequireRole>
                <ProfilePage />
              </RequireRole>
            }
          />

          {/* ── Catch-all ─────────────────────────────────────── */}
          <Route path="*" element={<Navigate to="/login" replace />} />

        </Route>
      </Routes>
    </BrowserRouter>
  );
}
