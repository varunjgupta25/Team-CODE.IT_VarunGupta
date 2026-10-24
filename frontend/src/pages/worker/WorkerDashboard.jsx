import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../../store/authStore';
import { useJobStore } from '../../store/jobStore';
import { TrustBadge } from '../../components/common/TrustBadge';
import { EmptyState } from '../../components/common/EmptyState';
import { formatCurrency, computeTrust } from '../../lib/utils';
import {
  Power,
  ShieldCheck,
  Star,
  MapPin,
  Clock,
  Sparkles,
  TrendingUp,
  Zap,
  ChevronRight,
  Briefcase,
  AlertCircle,
} from 'lucide-react';

export function WorkerDashboard() {
  const navigate = useNavigate();
  const { user, isAvailableNow, toggleAvailability } = useAuthStore();
  const { nearbyJobs, fetchNearbyJobs, isLoading } = useJobStore();

  const workerCoords = user?.location || { lat: 19.2812, lng: 72.8697 };
  const trust = user ? computeTrust(user) : { score: 85, tier: 'Silver' };

  useEffect(() => {
    fetchNearbyJobs(workerCoords);
    const interval = setInterval(() => {
      fetchNearbyJobs(workerCoords);
    }, 5000);
    return () => clearInterval(interval);
  }, [user]);

  return (
    <div className="space-y-4 pt-1">
      {/* Worker Profile & Availability Card */}
      <div className="bg-white rounded-3xl p-5 border border-slate-200 shadow-sm space-y-4">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className="relative">
              <img
                src={
                  user?.avatarUrl ||
                  'https://images.unsplash.com/photo-1540569014015-19a7be504e3a?w=150&auto=format&fit=crop&q=80'
                }
                alt={user?.name || 'Worker'}
                className="w-14 h-14 rounded-2xl object-cover border-2 border-brand-500 shadow-sm"
              />
              <span
                className={`absolute -bottom-1 -right-1 w-4 h-4 rounded-full border-2 border-white ${
                  isAvailableNow ? 'bg-emerald-500' : 'bg-slate-400'
                }`}
              />
            </div>

            <div>
              <div className="flex items-center gap-1.5 flex-wrap">
                <h1 className="font-extrabold text-base text-slate-900">{user?.name}</h1>
                {user?.verified && (
                  <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-emerald-100 text-emerald-800 flex items-center gap-0.5">
                    <ShieldCheck className="w-2.5 h-2.5" /> Verified
                  </span>
                )}
              </div>
              <div className="flex items-center gap-2 mt-1">
                <div className="flex items-center gap-1 text-amber-500 font-extrabold text-xs">
                  <Star className="w-3.5 h-3.5 fill-amber-400 text-amber-400" />
                  <span>{user?.rating || 4.8}</span>
                  <span className="text-slate-400 text-[10px] font-normal">
                    ({user?.jobsDone || 0} jobs)
                  </span>
                </div>
                <TrustBadge score={trust.score} tier={trust.tier} />
              </div>
            </div>
          </div>
        </div>

        {/* Available Now Toggle Switch (PRD requirement F2, Worker Flow) */}
        <div className="pt-2 border-t border-slate-100 flex items-center justify-between">
          <div>
            <p className="text-xs font-black text-slate-900 flex items-center gap-1.5">
              <Power className={`w-3.5 h-3.5 ${isAvailableNow ? 'text-emerald-600' : 'text-slate-400'}`} />
              <span>Available for Jobs</span>
            </p>
            <p className="text-[11px] text-slate-500">
              {isAvailableNow
                ? 'Online • Receiving nearby leads'
                : 'Offline • Hidden from customer search'}
            </p>
          </div>

          <button
            type="button"
            onClick={toggleAvailability}
            className={`w-14 h-8 rounded-full transition-colors relative p-1 cursor-pointer ${
              isAvailableNow ? 'bg-emerald-500' : 'bg-slate-300'
            }`}
          >
            <div
              className={`w-6 h-6 rounded-full bg-white shadow-md transform transition-transform ${
                isAvailableNow ? 'translate-x-6' : 'translate-x-0'
              }`}
            />
          </button>
        </div>
      </div>

      {/* Offline Alert Warning if worker turned off availability */}
      {!isAvailableNow && (
        <div className="bg-amber-50 border border-amber-200 rounded-2xl p-3 flex items-center gap-2.5 text-xs text-amber-900">
          <AlertCircle className="w-5 h-5 text-amber-600 shrink-0" />
          <p className="text-[11px]">
            You are currently <span className="font-bold">Offline</span>. Switch on &quot;Available for Jobs&quot; to receive requests within your 8 km radius in Mira Road.
          </p>
        </div>
      )}

      {/* Nearby Jobs Feed */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-base font-black text-slate-900 tracking-tight flex items-center gap-1.5">
              <Zap className="w-4 h-4 text-brand-600 fill-brand-600" />
              <span>Nearby Open Requests</span>
            </h2>
            <p className="text-[11px] text-slate-500">Sorted by distance from your current location</p>
          </div>
          <span className="text-[11px] font-extrabold px-2 py-0.5 rounded-full bg-brand-100 text-brand-800">
            {nearbyJobs.length} Live Leads
          </span>
        </div>

        {nearbyJobs.length === 0 ? (
          <EmptyState
            icon={Briefcase}
            title="No new job requests nearby"
            description="All nearby requests have been claimed or you are caught up! Check back soon or switch on your availability."
          />
        ) : (
          nearbyJobs.map((item) => {
            const job = item.job ? { ...item.job, distanceKm: item.distanceKm, etaMinutes: item.etaMinutes, within30: item.within30 } : item;
            const isNegotiating = job.status === 'negotiating';
            return (
              <div
                key={job.id}
                onClick={() => navigate(`/worker/job/${job.id}`)}
                className={`bg-white rounded-3xl p-4 border shadow-sm hover:border-brand-500 cursor-pointer active:scale-[0.98] transition-all space-y-3 group ${
                  isNegotiating ? 'border-amber-400 ring-2 ring-amber-400/20 bg-amber-50/20' : 'border-slate-200'
                }`}
              >
                {/* Category & Urgency Badges */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1.5">
                    <span className="text-[10px] font-black uppercase px-2.5 py-0.5 rounded-full bg-blue-100 text-blue-800">
                      {job.category}
                    </span>
                    {isNegotiating && (
                      <span className="text-[10px] font-black uppercase px-2 py-0.5 rounded-full bg-amber-100 text-amber-900 animate-pulse flex items-center gap-1">
                        🔥 Offer Received
                      </span>
                    )}
                  </div>

                  {job.within30 ? (
                    <span className="text-[10px] font-extrabold px-2.5 py-0.5 rounded-full bg-emerald-100 text-emerald-800 flex items-center gap-1">
                      <Clock className="w-3 h-3" /> Rush (&le;30 min)
                    </span>
                  ) : (
                    <span className="text-[10px] font-bold text-slate-500">
                      ETA ~{job.etaMinutes || 5} min
                    </span>
                  )}
                </div>

                {/* Description */}
                <div>
                  <p className="text-xs font-bold text-slate-900 line-clamp-2 leading-snug">
                    {job.description}
                  </p>
                  <div className="flex items-center gap-1 text-[11px] text-slate-500 mt-1">
                    <MapPin className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                    <span className="line-clamp-1">{job.location?.address}</span>
                    <span className="font-bold text-brand-600 shrink-0">({job.distanceKm ?? 0} km)</span>
                  </div>
                </div>

                {/* Budget & Action Bar */}
                <div className="bg-slate-50 rounded-2xl p-3 flex items-center justify-between border border-slate-100">
                  <div>
                    <span className="text-[10px] text-slate-500 font-medium block">
                      Customer Budget
                    </span>
                    <span className="text-sm font-black text-slate-900">
                      {job.budget ? formatCurrency(job.budget) : 'Open to offers'}
                    </span>
                  </div>

                  <div className="flex items-center gap-1 text-xs font-extrabold text-brand-600 group-hover:translate-x-0.5 transition-transform">
                    <span>{isNegotiating ? 'View & Accept Offer' : 'Send Offer'}</span>
                    <ChevronRight className="w-4 h-4" />
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
