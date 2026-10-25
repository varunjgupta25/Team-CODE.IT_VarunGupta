import React, { useState } from 'react';
import { useAuthStore } from '../../store/authStore';
import { ROLES } from '../../types';
import { Wrench, ShieldCheck, LogOut, User, ChevronDown } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export function Header() {
  const { user, role, logout } = useAuthStore();
  const navigate = useNavigate();
  const [dropdownOpen, setDropdownOpen] = useState(false);

  const isCustomer = role === ROLES.CUSTOMER;

  const handleLogout = () => {
    logout();
    setDropdownOpen(false);
    navigate('/login');
  };

  return (
    <header className="sticky top-0 z-40 bg-white/95 backdrop-blur-md border-b border-slate-200 px-4 py-2.5 shadow-sm">
      <div className="flex items-center justify-between max-w-md mx-auto">
        {/* Brand Logo & Tagline */}
        <div 
          onClick={() => {
            if (role === ROLES.ADMIN) navigate('/admin');
            else if (role === ROLES.WORKER) navigate('/worker');
            else if (role === ROLES.CUSTOMER) navigate('/');
            else navigate('/login');
          }}
          className="flex items-center gap-2 cursor-pointer select-none group"
        >
          <div className="w-9 h-9 rounded-xl bg-brand-600 text-white flex items-center justify-center shadow-md shadow-brand-500/20 group-hover:scale-105 transition-transform">
            <Wrench className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-1.5">
              <span className="font-extrabold text-base tracking-tight text-slate-900">RepairBuddy</span>
              <span className="text-[10px] font-bold px-1.5 py-0.5 rounded-full bg-emerald-100 text-emerald-800 flex items-center gap-0.5">
                <ShieldCheck className="w-2.5 h-2.5" /> 30m
              </span>
            </div>
            <p className="text-[11px] text-slate-500 -mt-0.5 font-medium">Hyperlocal Services</p>
          </div>
        </div>

        {/* User Account & Role Indicator (No switching allowed!) */}
        {user ? (
          <div className="relative">
            <button
              onClick={() => setDropdownOpen(!dropdownOpen)}
              className="flex items-center gap-2 p-1.5 pr-2 rounded-xl border border-slate-200 bg-slate-50 hover:bg-slate-100 transition-all shadow-sm active:scale-95"
            >
              <img
                src={user.avatarUrl || 'https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=100&auto=format&fit=crop&q=80'}
                alt={user.name}
                className="w-6 h-6 rounded-lg object-cover border border-slate-300"
              />
              <span className={`px-1.5 py-0.5 rounded text-[10px] font-black uppercase ${
                role === ROLES.ADMIN ? 'bg-purple-100 text-purple-800' : isCustomer ? 'bg-blue-100 text-blue-800' : 'bg-amber-100 text-amber-800'
              }`}>
                {role === ROLES.ADMIN ? 'Admin' : isCustomer ? 'Customer' : 'Worker'}
              </span>
              <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
            </button>

            {/* Dropdown Menu */}
            {dropdownOpen && (
              <div 
                onClick={(e) => e.stopPropagation()}
                className="absolute right-0 mt-2 w-48 bg-white rounded-2xl shadow-xl border border-slate-200 p-2 z-50 animate-in fade-in zoom-in-95 duration-100"
              >
                <div className="px-3 py-2 border-b border-slate-100">
                  <p className="font-black text-xs text-slate-900 truncate">{user.name}</p>
                  <p className="text-[10px] text-slate-500 truncate">{user.phone}</p>
                </div>

                <div className="py-1">
                  <button
                    onClick={() => {
                      setDropdownOpen(false);
                      navigate('/profile');
                    }}
                    className="w-full flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-semibold text-slate-700 hover:bg-slate-50 transition"
                  >
                    <User className="w-3.5 h-3.5 text-slate-500" />
                    <span>My Profile</span>
                  </button>

                  <button
                    onClick={handleLogout}
                    className="w-full flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-semibold text-red-600 hover:bg-red-50 transition"
                  >
                    <LogOut className="w-3.5 h-3.5" />
                    <span>Log Out</span>
                  </button>
                </div>
              </div>
            )}
          </div>
        ) : (
          <button
            onClick={() => navigate('/login')}
            className="px-3 py-1.5 rounded-xl bg-brand-600 text-white font-bold text-xs shadow-sm active:scale-95 transition"
          >
            Log In
          </button>
        )}
      </div>
    </header>
  );
}
