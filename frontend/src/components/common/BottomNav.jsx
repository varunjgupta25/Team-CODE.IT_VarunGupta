import React from 'react';
import { NavLink } from 'react-router-dom';
import { useAuthStore } from '../../store/authStore';
import { useJobStore } from '../../store/jobStore';
import { ROLES, JOB_STATUS } from '../../types';
import { Home, Compass, Activity, Award, User } from 'lucide-react';

export function BottomNav() {
  const { role, user } = useAuthStore();
  const { currentJob } = useJobStore();

  if (!user || !role || role === ROLES.ADMIN) {
    return null; // Don't show navigation tabs if not logged in or admin
  }

  const isCustomer = role === ROLES.CUSTOMER;

  const hasActiveJob = currentJob && [
    JOB_STATUS.OPEN,
    JOB_STATUS.NEGOTIATING,
    JOB_STATUS.ACCEPTED,
    JOB_STATUS.IN_PROGRESS,
  ].includes(currentJob.status);

  return (
    <nav className="fixed bottom-0 left-0 right-0 z-40 bg-white/95 backdrop-blur-md border-t border-slate-200 shadow-lg safe-bottom">
      <div className="max-w-md mx-auto grid grid-cols-3 h-16">
        {isCustomer ? (
          <>
            <NavLink
              to="/"
              end
              className={({ isActive }) =>
                `flex flex-col items-center justify-center min-h-[48px] text-xs font-semibold transition-colors ${
                  isActive ? 'text-brand-600' : 'text-slate-500 hover:text-slate-900'
                }`
              }
            >
              <Home className="w-5 h-5 mb-1" />
              <span>Book</span>
            </NavLink>

            <NavLink
              to="/customer/status"
              className={({ isActive }) =>
                `relative flex flex-col items-center justify-center min-h-[48px] text-xs font-semibold transition-colors ${
                  isActive ? 'text-brand-600' : 'text-slate-500 hover:text-slate-900'
                }`
              }
            >
              <Activity className="w-5 h-5 mb-1" />
              <span>Active Job</span>
              {hasActiveJob && (
                <span className="absolute top-2.5 right-6 w-2 h-2 rounded-full bg-emerald-500 animate-ping" />
              )}
            </NavLink>

            <NavLink
              to="/profile"
              className={({ isActive }) =>
                `flex flex-col items-center justify-center min-h-[48px] text-xs font-semibold transition-colors ${
                  isActive ? 'text-brand-600' : 'text-slate-500 hover:text-slate-900'
                }`
              }
            >
              <User className="w-5 h-5 mb-1" />
              <span>Profile</span>
            </NavLink>
          </>
        ) : (
          <>
            <NavLink
              to="/worker"
              end
              className={({ isActive }) =>
                `flex flex-col items-center justify-center min-h-[48px] text-xs font-semibold transition-colors ${
                  isActive ? 'text-brand-600' : 'text-slate-500 hover:text-slate-900'
                }`
              }
            >
              <Compass className="w-5 h-5 mb-1" />
              <span>Jobs Feed</span>
            </NavLink>

            <NavLink
              to="/worker/earnings"
              className={({ isActive }) =>
                `flex flex-col items-center justify-center min-h-[48px] text-xs font-semibold transition-colors ${
                  isActive ? 'text-brand-600' : 'text-slate-500 hover:text-slate-900'
                }`
              }
            >
              <Award className="w-5 h-5 mb-1" />
              <span>Earnings</span>
            </NavLink>

            <NavLink
              to="/profile"
              className={({ isActive }) =>
                `flex flex-col items-center justify-center min-h-[48px] text-xs font-semibold transition-colors ${
                  isActive ? 'text-brand-600' : 'text-slate-500 hover:text-slate-900'
                }`
              }
            >
              <User className="w-5 h-5 mb-1" />
              <span>Profile</span>
            </NavLink>
          </>
        )}
      </div>
    </nav>
  );
}
