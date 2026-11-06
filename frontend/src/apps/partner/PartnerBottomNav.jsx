import React from 'react';
import { NavLink } from 'react-router-dom';
import { useAuthStore } from '../../store/authStore';
import { ROLES } from '../../types';
import { Compass, Award, User, ShieldCheck } from 'lucide-react';

export function PartnerBottomNav() {
  const { role, user } = useAuthStore();

  if (!user || !role) {
    return null;
  }

  const isAdmin = role === ROLES.ADMIN;

  return (
    <nav className="fixed bottom-0 left-0 right-0 z-40 bg-white/95 backdrop-blur-md border-t border-slate-200 shadow-lg safe-bottom">
      <div className={`max-w-md mx-auto grid ${isAdmin ? 'grid-cols-2' : 'grid-cols-3'} h-16`}>
        {isAdmin ? (
          <>
            <NavLink
              to="/admin"
              end
              className={({ isActive }) =>
                `flex flex-col items-center justify-center min-h-[48px] text-xs font-semibold transition-colors ${
                  isActive ? 'text-purple-600' : 'text-slate-500 hover:text-slate-900'
                }`
              }
            >
              <ShieldCheck className="w-5 h-5 mb-1" />
              <span>Admin Console</span>
            </NavLink>

            <NavLink
              to="/profile"
              className={({ isActive }) =>
                `flex flex-col items-center justify-center min-h-[48px] text-xs font-semibold transition-colors ${
                  isActive ? 'text-purple-600' : 'text-slate-500 hover:text-slate-900'
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
                  isActive ? 'text-amber-600' : 'text-slate-500 hover:text-slate-900'
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
                  isActive ? 'text-amber-600' : 'text-slate-500 hover:text-slate-900'
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
                  isActive ? 'text-amber-600' : 'text-slate-500 hover:text-slate-900'
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

