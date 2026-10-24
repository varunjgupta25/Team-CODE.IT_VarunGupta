import React from 'react';
import { useAuthStore } from '../store/authStore';
import { ROLES } from '../types';
import { computeTrust, formatCurrency } from '../lib/utils';
import { TrustBadge } from '../components/common/TrustBadge';
import {
  User,
  Phone,
  MapPin,
  ShieldCheck,
  Briefcase,
  LogOut,
  Star,
  Award,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useToastStore } from '../store/toastStore';

export function ProfilePage() {
  const { user, role, logout } = useAuthStore();
  const navigate = useNavigate();

  if (!user) {
    navigate('/login');
    return null;
  }

  const isCustomer = role === ROLES.CUSTOMER;
  const trust = role === ROLES.WORKER ? computeTrust(user) : null;

  const handleLogout = () => {
    logout();
    useToastStore.getState().info('You have logged out.');
    navigate('/login');
  };

  return (
    <div className="space-y-4 pt-1">
      <div>
        <h1 className="text-xl font-black text-slate-900 tracking-tight">Account Profile</h1>
        <p className="text-xs text-slate-500">Your registered details on RepairBuddy</p>
      </div>

      {/* Profile Card */}
      <div className="bg-white rounded-3xl p-5 border border-slate-200 shadow-sm space-y-4">
        <div className="flex items-center gap-3.5">
          <img
            src={
              user.avatarUrl ||
              'https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=150&auto=format&fit=crop&q=80'
            }
            alt={user.name}
            className="w-16 h-16 rounded-2xl object-cover border-2 border-brand-500 shadow-sm"
          />
          <div>
            <div className="flex items-center gap-1.5 flex-wrap">
              <h2 className="text-base font-extrabold text-slate-900">{user.name}</h2>
              <span
                className={`text-[10px] font-black px-2 py-0.5 rounded uppercase ${
                  isCustomer ? 'bg-blue-100 text-blue-800' : 'bg-amber-100 text-amber-800'
                }`}
              >
                {role}
              </span>
            </div>
            <p className="text-xs text-slate-500 mt-0.5 flex items-center gap-1">
              <Phone className="w-3 h-3 text-slate-400" />
              <span>{user.phone}</span>
            </p>
            {trust && (
              <div className="mt-1">
                <TrustBadge score={trust.score} tier={trust.tier} />
              </div>
            )}
          </div>
        </div>

        {/* Role Specific Details */}
        <div className="pt-3 border-t border-slate-100 space-y-2 text-xs">
          {isCustomer ? (
            <div className="flex items-start gap-2 bg-slate-50 p-3 rounded-2xl border border-slate-100">
              <MapPin className="w-4 h-4 text-brand-600 shrink-0 mt-0.5" />
              <div>
                <span className="font-bold text-slate-900 block">Default Service Address</span>
                <span className="text-slate-600 text-[11px]">{user.location?.address}</span>
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-2 text-center">
              <div className="p-3 bg-slate-50 rounded-2xl border border-slate-100">
                <span className="text-[10px] text-slate-500 block">Primary Trade</span>
                <span className="font-black text-slate-900 capitalize">
                  {user.skills?.join(', ') || 'Plumber'}
                </span>
              </div>
              <div className="p-3 bg-slate-50 rounded-2xl border border-slate-100">
                <span className="text-[10px] text-slate-500 block">Base Rate</span>
                <span className="font-black text-brand-700">
                  {formatCurrency(user.rates?.[user.skills?.[0]] || 350)}
                </span>
              </div>
            </div>
          )}
        </div>

        {/* Security & Verification status */}
        <div className="bg-emerald-50 border border-emerald-200 rounded-2xl p-3 flex items-center gap-2.5 text-xs text-emerald-900">
          <ShieldCheck className="w-4 h-4 text-emerald-600 shrink-0" />
          <span>Identity Verified • Government ID Approved</span>
        </div>

        {/* Log Out Button */}
        <button
          onClick={handleLogout}
          className="w-full py-3.5 rounded-2xl bg-red-50 hover:bg-red-100 text-red-600 font-extrabold text-xs border border-red-200 flex items-center justify-center gap-2 active:scale-95 transition"
        >
          <LogOut className="w-4 h-4" />
          <span>Log Out of Session</span>
        </button>
      </div>
    </div>
  );
}
