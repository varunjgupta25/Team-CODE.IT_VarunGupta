import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuthStore } from '../../store/authStore';
import { ROLES } from '../../types';

export function ProtectedRoute({ children, allowedRole }) {
  const { user, role } = useAuthStore();
  const location = useLocation();

  // If not logged in, redirect to fake login portal
  if (!user || !role) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // Strict role boundary enforcement:
  // Customers cannot access worker pages
  if (allowedRole === ROLES.WORKER && role !== ROLES.WORKER) {
    return <Navigate to="/" replace />;
  }

  // Workers cannot access customer booking pages
  if (allowedRole === ROLES.CUSTOMER && role !== ROLES.CUSTOMER) {
    return <Navigate to="/worker" replace />;
  }

  return children;
}
