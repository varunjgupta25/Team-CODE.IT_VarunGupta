import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useJobStore } from '../../store/jobStore';
import { useAuthStore } from '../../store/authStore';
import { CATEGORIES, JOB_STATUS } from '../../types';
import {
  Wrench,
  Zap,
  Paintbrush,
  Sparkles,
  Home as HomeIcon,
  Utensils,
  Hammer,
  Cpu,
  Clock,
  ShieldCheck,
  ChevronRight,
  MapPin,
} from 'lucide-react';
import { formatCurrency } from '../../lib/utils';

// Icon mapping helper
const ICON_MAP = {
  Wrench,
  Zap,
  Paintbrush,
  Sparkles,
  Home: HomeIcon,
  Utensils,
  Hammer,
  Cpu,
};

export function CustomerHome() {
  const navigate = useNavigate();
  const { currentJob } = useJobStore();
  const { user } = useAuthStore();

  const hasActiveJob =
    currentJob &&
    [
      JOB_STATUS.OPEN,
      JOB_STATUS.NEGOTIATING,
      JOB_STATUS.ACCEPTED,
      JOB_STATUS.IN_PROGRESS,
    ].includes(currentJob.status);

  return (
    <div className="space-y-5 pt-1">
      {/* User Greeting & Hyperlocal Location Header */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-1 text-[11px] font-bold text-slate-500 uppercase tracking-wide">
            <MapPin className="w-3.5 h-3.5 text-brand-600" />
            <span>Serving Mira Road, Mumbai</span>
          </div>
          <h1 className="text-xl font-black text-slate-900 tracking-tight mt-0.5">
            Hey, {user?.name?.split(' ')[0] || 'Neighbor'} 👋
          </h1>
        </div>
        <div className="w-10 h-10 rounded-full overflow-hidden border-2 border-brand-500 shadow-sm">
          <img
            src={
              user?.avatarUrl ||
              'https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=120&auto=format&fit=crop&q=80'
            }
            alt={user?.name || 'User'}
            className="w-full h-full object-cover"
          />
        </div>
      </div>

      {/* Active Job Floating Tracker Banner if there's an active job */}
      {hasActiveJob && (
        <div
          onClick={() => navigate(`/customer/status/${currentJob.id}`)}
          className="bg-gradient-to-r from-brand-600 to-indigo-700 rounded-2xl p-4 text-white shadow-lg shadow-brand-500/25 cursor-pointer active:scale-[0.98] transition-all flex items-center justify-between"
        >
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-ping" />
              <span className="text-[11px] font-extrabold uppercase tracking-wider text-emerald-200">
                Active Job Status
              </span>
            </div>
            <p className="font-extrabold text-sm capitalize">
              {currentJob.category} Service ({currentJob.status})
            </p>
            <p className="text-[11px] text-white/80 line-clamp-1">
              {currentJob.location?.address || 'Mira Road'}
            </p>
          </div>
          <div className="flex items-center gap-1 font-bold text-xs bg-white/20 px-3 py-1.5 rounded-xl backdrop-blur-sm">
            <span>Track</span>
            <ChevronRight className="w-4 h-4" />
          </div>
        </div>
      )}

      {/* Hero Banner: 30-Minute Guarantee */}
      <div className="bg-gradient-to-br from-slate-900 via-slate-800 to-slate-950 rounded-3xl p-5 text-white shadow-xl relative overflow-hidden">
        <div className="relative z-10 space-y-2">
          <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 text-[11px] font-extrabold">
            <Clock className="w-3.5 h-3.5" />
            <span>30-Minute Doorstep Arrival</span>
          </div>
          <h2 className="text-xl font-black tracking-tight leading-tight">
            Book local verified experts. <br />
            <span className="text-brand-400">Negotiate fair rates.</span>
          </h2>
          <p className="text-xs text-slate-300 max-w-[270px] leading-relaxed">
            Zero middlemen cuts. Drop a pin and match directly with nearby rated tradesmen.
          </p>
        </div>
        <div className="absolute -right-6 -bottom-6 w-32 h-32 rounded-full bg-brand-500/20 blur-2xl pointer-events-none" />
      </div>

      {/* Category Grid Section */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-black text-slate-900 tracking-tight">
            Choose a Service
          </h2>
          <span className="text-[11px] font-bold text-brand-600">8 Categories</span>
        </div>

        <div className="grid grid-cols-2 gap-3">
          {CATEGORIES.map((cat) => {
            const IconComponent = ICON_MAP[cat.icon] || Wrench;
            return (
              <div
                key={cat.id}
                onClick={() => navigate(`/customer/create-job?category=${cat.id}`)}
                className="bg-white rounded-2xl p-4 border border-slate-200 shadow-sm hover:border-brand-500 hover:shadow-md cursor-pointer active:scale-95 transition-all flex flex-col justify-between group min-h-[110px]"
              >
                <div className="flex items-start justify-between">
                  <div className="w-10 h-10 rounded-xl bg-brand-50 text-brand-600 flex items-center justify-center group-hover:bg-brand-600 group-hover:text-white transition-colors">
                    <IconComponent className="w-5 h-5" />
                  </div>
                  <span className="text-[10px] font-extrabold text-slate-500 bg-slate-100 px-2 py-0.5 rounded-full">
                    from {formatCurrency(cat.typicalRate)}
                  </span>
                </div>

                <div className="mt-3">
                  <h3 className="font-extrabold text-sm text-slate-900 group-hover:text-brand-600 transition-colors">
                    {cat.label}
                  </h3>
                  <p className="text-[10px] text-slate-500 line-clamp-1 mt-0.5">
                    {cat.description}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Trust & Safety Highlights Footer Card */}
      <div className="bg-white rounded-2xl p-4 border border-slate-200/90 shadow-sm space-y-2.5">
        <div className="flex items-center gap-2 text-xs font-bold text-slate-900">
          <ShieldCheck className="w-4 h-4 text-emerald-600" />
          <span>The RepairBuddy Safety Promise</span>
        </div>
        <div className="grid grid-cols-3 gap-2 text-center pt-1">
          <div className="p-2 rounded-xl bg-slate-50 border border-slate-100">
            <p className="text-base font-black text-slate-900">100%</p>
            <p className="text-[10px] text-slate-500 font-medium">Govt ID Verified</p>
          </div>
          <div className="p-2 rounded-xl bg-slate-50 border border-slate-100">
            <p className="text-base font-black text-slate-900">&lt;30m</p>
            <p className="text-[10px] text-slate-500 font-medium">Average Arrival</p>
          </div>
          <div className="p-2 rounded-xl bg-slate-50 border border-slate-100">
            <p className="text-base font-black text-slate-900">Fair</p>
            <p className="text-[10px] text-slate-500 font-medium">Direct Bidding</p>
          </div>
        </div>
      </div>
    </div>
  );
}
