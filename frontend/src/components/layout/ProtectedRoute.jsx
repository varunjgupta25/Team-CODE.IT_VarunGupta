import React, { useEffect, useState } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuthStore } from '../../store/authStore';
import { ROLES, ADMIN_CLAIM_KEY } from '../../types';
import { isFirebaseConfigured, getFirebaseAuth } from '../../lib/firebase';
import { useToastStore } from '../../store/toastStore';

export function ProtectedRoute({ children, allowedRole }) {
  const { user, role, isInitialized } = useAuthStore();
  const location = useLocation();
  const [isAdminVerifying, setIsAdminVerifying] = useState(
    allowedRole === ROLES.ADMIN && isFirebaseConfigured()
  );
  const [isAdminClaimValid, setIsAdminClaimValid] = useState(
    allowedRole !== ROLES.ADMIN || !isFirebaseConfigured()
  );

  useEffect(() => {
    let isMounted = true;
    if (isInitialized && allowedRole === ROLES.ADMIN && isFirebaseConfigured()) {
      Promise.resolve().then(async () => {
        const auth = getFirebaseAuth();
        const currentUser = auth?.currentUser;
        if (!currentUser) {
          useToastStore.getState().error('Access denied. Administrator privileges required.');
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
          if (!hasAdminClaim) {
            useToastStore.getState().error('Access denied. Administrator privileges required.');
            setIsAdminClaimValid(false);
          } else {
            setIsAdminClaimValid(true);
          }
        } catch (err) {
          if (!isMounted) return;
          console.warn('[ProtectedRoute] Admin claim verification error:', err);
          useToastStore.getState().error('Failed to verify administrator privileges.');
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
  }, [allowedRole, user, isInitialized]);

  // Wait for initial auth state hydration before redirecting
  if (!isInitialized) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[50vh] text-slate-500 text-xs font-semibold gap-2">
        <div className="w-6 h-6 border-2 border-brand-500 border-t-transparent rounded-full animate-spin" />
        <span>Verifying authentication session...</span>
      </div>
    );
  }

  // If not logged in in authenticated state, redirect to /login with return location
  if (!user || !role) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // Admin route protection
  if (allowedRole === ROLES.ADMIN) {
    if (role !== ROLES.ADMIN) {
      useToastStore.getState().error('Access denied. Administrator privileges required.');
      return <Navigate to={role === ROLES.WORKER ? '/worker' : '/'} replace />;
    }

    if (isAdminVerifying) {
      return (
        <div className="flex flex-col items-center justify-center min-h-[50vh] text-slate-500 text-xs font-semibold gap-2">
          <div className="w-6 h-6 border-2 border-brand-500 border-t-transparent rounded-full animate-spin" />
          <span>Verifying administrator permissions...</span>
        </div>
      );
    }

    if (!isAdminClaimValid) {
      return <Navigate to={role === ROLES.WORKER ? '/worker' : '/'} replace />;
    }
  }

  // Strict role boundary enforcement:
  // Customers cannot access worker pages
  if (allowedRole === ROLES.WORKER && role !== ROLES.WORKER) {
    useToastStore.getState().error('Access denied. Worker portal access required.');
    return <Navigate to="/" replace />;
  }

  // Workers cannot access customer booking pages
  if (allowedRole === ROLES.CUSTOMER && role !== ROLES.CUSTOMER) {
    useToastStore.getState().error('Access denied. Customer portal access required.');
    return <Navigate to="/worker" replace />;
  }

  return children;
}
