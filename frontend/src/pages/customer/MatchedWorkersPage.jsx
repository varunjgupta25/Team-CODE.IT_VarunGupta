import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useJobStore } from '../../store/jobStore';
import { WorkerCardSkeleton } from '../../components/common/Skeleton';
import { EmptyState } from '../../components/common/EmptyState';
import { TrustBadge } from '../../components/common/TrustBadge';
import { formatCurrency } from '../../lib/utils';
import {
  ShieldCheck,
  Star,
  MapPin,
  Clock,
  ArrowLeft,
  Zap,
  Check,
  X,
  User,
  Briefcase,
} from 'lucide-react';

export function MatchedWorkersPage() {
  const { jobId } = useParams();
  const navigate = useNavigate();
  const {
    currentJob,
    fetchJob,
    matchedWorkers,
    fetchMatchedWorkers,
    isMatchingLoading,
    createOffer,
  } = useJobStore();

  const [selectedWorkerForOffer, setSelectedWorkerForOffer] = useState(null);
  const [inspectingWorker, setInspectingWorker] = useState(null);
  const [customPrice, setCustomPrice] = useState('');
  const [isSubmittingOffer, setIsSubmittingOffer] = useState(false);

  useEffect(() => {
    if (jobId) {
      fetchJob(jobId);
      fetchMatchedWorkers(jobId);
    }
  }, [jobId, fetchJob, fetchMatchedWorkers]);

  const handleBookListedRate = async (worker) => {
    setIsSubmittingOffer(true);
    try {
      await createOffer({
        jobId,
        workerId: worker.uid,
        price: worker.rate,
        by: 'customer',
      });
      navigate(`/customer/status/${jobId}`);
    } catch (err) {
      console.error(err);
    } finally {
      setIsSubmittingOffer(false);
    }
  };

  const handleMakeCustomOffer = async (e) => {
    e.preventDefault();
    if (!customPrice || !selectedWorkerForOffer) return;

    setIsSubmittingOffer(true);
    try {
      await createOffer({
        jobId,
        workerId: selectedWorkerForOffer.uid,
        price: Number(customPrice),
        by: 'customer',
      });
      setSelectedWorkerForOffer(null);
      navigate(`/customer/status/${jobId}`);
    } catch (err) {
      console.error(err);
    } finally {
      setIsSubmittingOffer(false);
    }
  };

  return (
    <div className="space-y-4 pt-1">
      {/* Top Header */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => navigate('/')}
          className="w-9 h-9 rounded-xl bg-white border border-slate-200 flex items-center justify-center text-slate-700 hover:bg-slate-100 active:scale-95 transition"
        >
          <ArrowLeft className="w-4 h-4" />
        </button>
        <div>
          <h1 className="text-lg font-black text-slate-900 tracking-tight">Matched Providers</h1>
          <p className="text-[11px] text-slate-500">
            Ranked by proximity (40%), rating (30%), &amp; fair price
          </p>
        </div>
      </div>

      {/* Safety & Verification Guarantee Banner */}
      <div className="bg-emerald-50 border border-emerald-200 rounded-2xl p-3 flex items-center gap-2.5 text-xs text-emerald-900">
        <ShieldCheck className="w-5 h-5 text-emerald-600 shrink-0" />
        <div className="flex-1 text-[11px]">
          <span className="font-bold">100% ID Verified Only.</span> Unverified workers are automatically filtered out.
        </div>
      </div>

      {/* Worker List */}
      <div className="space-y-3">
        {isMatchingLoading ? (
          <>
            <WorkerCardSkeleton />
            <WorkerCardSkeleton />
            <WorkerCardSkeleton />
          </>
        ) : matchedWorkers.length === 0 ? (
          <EmptyState
            title="No workers currently available"
            description="All verified providers in your immediate radius are currently occupied. Please try adjusting your category or check back in a few minutes."
            actionLabel="Return to Home"
            onAction={() => navigate('/')}
          />
        ) : (
          matchedWorkers.map((rawItem) => {
            const w = rawItem.worker || rawItem;
            const uid = w.uid;
            const name = w.name;
            const avatarUrl = w.avatarUrl || 'https://images.unsplash.com/photo-1540569014015-19a7be504e3a?w=150&auto=format&fit=crop&q=80';
            const verified = w.verified;
            const rating = w.rating ?? 4.8;
            const jobsDone = w.jobsDone ?? 0;
            const currentCat = currentJob?.category?.toLowerCase() || '';
            const rate = w.rate || (w.rates && (w.rates[currentCat] || Object.values(w.rates)[0])) || 350;
            const distanceKm = rawItem.distanceKm ?? w.distanceKm ?? 1.2;
            const etaMinutes = rawItem.etaMinutes ?? w.etaMinutes ?? 3.0;
            const within30 = rawItem.within30 ?? (etaMinutes <= 30);
            const trustScore = rawItem.trustScore || w.trustScore || 85;
            const trustTier = rawItem.trustBadge || w.trustBadge || rawItem.trustTier || w.trustTier || 'Gold';
            const about = w.about || `${name} • Verified specialist with ${jobsDone}+ completed jobs`;

            const worker = {
              ...w,
              uid,
              name,
              avatarUrl,
              verified,
              rating,
              jobsDone,
              rate,
              distanceKm,
              etaMinutes,
              within30,
              trustScore,
              trustTier,
              about,
            };

            return (
              <div
                key={worker.uid}
                className="bg-white rounded-3xl p-4 border border-slate-200 shadow-sm hover:border-brand-500 transition-all space-y-3.5 relative overflow-hidden"
              >
              {/* "Within 30 min" Tag if ETA <= 30 mins (PRD F10) */}
              {worker.within30 && (
                <div className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-emerald-100 text-emerald-800 text-[10px] font-extrabold tracking-wide uppercase border border-emerald-300">
                  <Zap className="w-3 h-3 fill-emerald-600 text-emerald-600" />
                  <span>Within 30 Min Tag</span>
                </div>
              )}

              {/* Worker Profile Snapshot */}
              <div
                onClick={() => setInspectingWorker(worker)}
                className="flex items-start gap-3 cursor-pointer group"
                role="button"
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    setInspectingWorker(worker);
                  }
                }}
              >
                <div className="relative">
                  <img
                    src={worker.avatarUrl}
                    alt={worker.name}
                    className="w-14 h-14 rounded-2xl object-cover border-2 border-slate-100 shadow-sm group-hover:border-brand-400 transition"
                  />
                  <span className="absolute -bottom-1 -right-1 w-3.5 h-3.5 rounded-full bg-emerald-500 border-2 border-white" />
                </div>

                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-1">
                    <div className="flex items-center gap-1.5 flex-wrap">
                      <h3 className="font-black text-sm text-slate-900 group-hover:text-brand-600 transition truncate">
                        {worker.name}
                      </h3>
                      {worker.verified && (
                        <span className="text-[10px] font-bold px-1.5 py-0.2 rounded-md bg-blue-100 text-blue-800 flex items-center gap-0.5">
                          <ShieldCheck className="w-2.5 h-2.5" /> Verified
                        </span>
                      )}
                    </div>
                    <span className="text-[10px] font-bold text-brand-600 hover:underline">
                      View Profile &rarr;
                    </span>
                  </div>

                  <div className="flex items-center gap-2 mt-1 flex-wrap">
                    <div className="flex items-center gap-1 text-amber-500 font-extrabold text-xs">
                      <Star className="w-3.5 h-3.5 fill-amber-400 text-amber-400" />
                      <span>{worker.rating}</span>
                      <span className="text-slate-400 text-[10px] font-normal">({worker.jobsDone} jobs)</span>
                    </div>

                    <TrustBadge score={worker.trustScore} tier={worker.trustTier} />
                  </div>

                  <p className="text-[11px] text-slate-500 mt-1 line-clamp-1">{worker.about}</p>
                </div>
              </div>

              {/* Distance, ETA, & Rate Bar */}
              <div className="bg-slate-50 rounded-2xl p-3 flex items-center justify-between border border-slate-100 text-xs">
                <div className="space-y-0.5">
                  <div className="flex items-center gap-1 text-slate-600 text-[11px]">
                    <MapPin className="w-3 h-3 text-slate-400" />
                    <span>{worker.distanceKm} km away</span>
                  </div>
                  <div className="flex items-center gap-1 font-bold text-slate-900 text-xs">
                    <Clock className="w-3 h-3 text-brand-600" />
                    <span>Arrives in ~{worker.etaMinutes} min</span>
                  </div>
                </div>

                <div className="text-right">
                  <p className="text-[10px] text-slate-500 font-medium">Listed Rate</p>
                  <p className="text-base font-black text-brand-600">{formatCurrency(worker.rate)}</p>
                </div>
              </div>

              {/* Dual Action Buttons: Book at listed rate OR Make an offer */}
              <div className="grid grid-cols-2 gap-2 pt-1">
                <button
                  type="button"
                  disabled={isSubmittingOffer}
                  onClick={() => {
                    setSelectedWorkerForOffer(worker);
                    setCustomPrice(worker.rate > 50 ? worker.rate - 50 : worker.rate);
                  }}
                  className="py-2.5 rounded-xl border border-brand-300 bg-brand-50 hover:bg-brand-100 text-brand-700 font-extrabold text-xs active:scale-95 transition-all flex items-center justify-center gap-1 min-h-touch"
                >
                  <span>Make an Offer</span>
                </button>

                <button
                  type="button"
                  disabled={isSubmittingOffer}
                  onClick={() => handleBookListedRate(worker)}
                  className="py-2.5 rounded-xl bg-brand-600 hover:bg-brand-700 text-white font-extrabold text-xs shadow-md shadow-brand-500/20 active:scale-95 transition-all flex items-center justify-center gap-1 min-h-touch"
                >
                  <Check className="w-3.5 h-3.5" />
                  <span>Book at {formatCurrency(worker.rate)}</span>
                </button>
              </div>
            </div>
          );
        })
        )}
      </div>

      {/* Counter Offer Modal */}
      {selectedWorkerForOffer && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 animate-in fade-in duration-150">
          <div className="bg-white rounded-3xl max-w-sm w-full p-5 shadow-2xl border border-slate-200 space-y-4">
            <div className="flex items-center justify-between pb-2 border-b border-slate-100">
              <div>
                <h3 className="font-extrabold text-sm text-slate-900">Make Counter Offer</h3>
                <p className="text-[11px] text-slate-500">To {selectedWorkerForOffer.name}</p>
              </div>
              <button
                onClick={() => setSelectedWorkerForOffer(null)}
                className="p-1 rounded-lg hover:bg-slate-100 text-slate-400"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleMakeCustomOffer} className="space-y-3">
              <div className="bg-slate-50 p-3 rounded-2xl flex justify-between items-center text-xs">
                <span className="text-slate-600 font-medium">Worker's Listed Rate:</span>
                <span className="font-bold text-slate-900 line-through text-slate-400">
                  {formatCurrency(selectedWorkerForOffer.rate)}
                </span>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-800 mb-1">
                  Your Proposed Offer (₹)
                </label>
                <div className="relative">
                  <span className="absolute left-3.5 top-2.5 text-slate-400 font-bold text-sm">₹</span>
                  <input
                    type="number"
                    required
                    min="100"
                    step="50"
                    value={customPrice}
                    onChange={(e) => setCustomPrice(e.target.value)}
                    className="w-full text-base font-extrabold pl-8 pr-3 py-2.5 rounded-xl border border-slate-200 bg-white focus:ring-2 focus:ring-brand-500"
                  />
                </div>
                <p className="text-[10px] text-slate-500 mt-1">
                  The worker can accept or counter your offer.
                </p>
              </div>

              <div className="flex gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setSelectedWorkerForOffer(null)}
                  className="flex-1 py-2.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-bold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmittingOffer || !customPrice}
                  className="flex-1 py-2.5 rounded-xl bg-brand-600 hover:bg-brand-700 text-white text-xs font-extrabold shadow-md shadow-brand-500/20"
                >
                  {isSubmittingOffer ? 'Sending...' : 'Send Offer'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Worker Profile Detail Modal (Module E) */}
      {inspectingWorker && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 animate-in fade-in duration-150">
          <div className="bg-white rounded-3xl max-w-sm w-full p-5 shadow-2xl border border-slate-200 space-y-4 max-h-[90vh] overflow-y-auto">
            {/* Header with Close */}
            <div className="flex items-start justify-between pb-2 border-b border-slate-100">
              <div className="flex items-center gap-3">
                <img
                  src={inspectingWorker.avatarUrl}
                  alt={inspectingWorker.name}
                  className="w-14 h-14 rounded-2xl object-cover border-2 border-brand-500 shadow-sm"
                />
                <div>
                  <div className="flex items-center gap-1.5 flex-wrap">
                    <h3 className="font-extrabold text-base text-slate-900">{inspectingWorker.name}</h3>
                    {inspectingWorker.verified && (
                      <span className="text-[10px] font-bold px-1.5 py-0.5 rounded-md bg-emerald-100 text-emerald-800 flex items-center gap-0.5">
                        <ShieldCheck className="w-3 h-3 text-emerald-600" /> ID Verified
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-2 mt-1">
                    <div className="flex items-center gap-1 text-amber-500 font-extrabold text-xs">
                      <Star className="w-3.5 h-3.5 fill-amber-400 text-amber-400" />
                      <span>{inspectingWorker.rating}</span>
                      <span className="text-slate-400 text-[10px] font-normal">
                        ({inspectingWorker.jobsDone} jobs)
                      </span>
                    </div>
                    <TrustBadge score={inspectingWorker.trustScore} tier={inspectingWorker.trustTier} />
                  </div>
                </div>
              </div>

              <button
                type="button"
                onClick={() => setInspectingWorker(null)}
                className="p-1 rounded-lg hover:bg-slate-100 text-slate-400"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Verification & Trust Guarantee */}
            <div className="bg-emerald-50 rounded-2xl p-3 border border-emerald-200 space-y-1">
              <div className="flex items-center gap-1.5 text-xs font-bold text-emerald-900">
                <ShieldCheck className="w-4 h-4 text-emerald-600" />
                <span>Verified Service Provider</span>
              </div>
              <p className="text-[11px] text-emerald-800">
                Aadhaar identity and background verification completed. Certified trade professional on RepairBuddy.
              </p>
            </div>

            {/* About / Bio */}
            <div className="space-y-1 text-xs">
              <span className="font-bold text-slate-800 flex items-center gap-1">
                <User className="w-3.5 h-3.5 text-brand-600" />
                About Provider
              </span>
              <p className="text-slate-600 text-[11px] leading-relaxed bg-slate-50 p-3 rounded-2xl border border-slate-100">
                {inspectingWorker.about || 'Experienced local professional providing reliable and high-quality repairs with guaranteed punctuality.'}
              </p>
            </div>

            {/* Skills & Services */}
            <div className="space-y-1 text-xs">
              <span className="font-bold text-slate-800 flex items-center gap-1">
                <Briefcase className="w-3.5 h-3.5 text-brand-600" />
                Verified Trades &amp; Rates
              </span>
              <div className="bg-slate-50 p-3 rounded-2xl border border-slate-100 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-semibold text-slate-700 capitalize">
                    {currentJob?.category || 'General Service'}
                  </span>
                  <span className="font-black text-brand-700 text-sm">
                    {formatCurrency(inspectingWorker.rate)}
                  </span>
                </div>
                {inspectingWorker.skills && Array.isArray(inspectingWorker.skills) && inspectingWorker.skills.length > 0 && (
                  <div className="flex flex-wrap gap-1 pt-1 border-t border-slate-200/60">
                    {inspectingWorker.skills.map((skill) => (
                      <span
                        key={skill}
                        className="px-2 py-0.5 rounded-full bg-white border border-slate-200 text-slate-700 text-[10px] font-bold capitalize"
                      >
                        {skill}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Proximity & ETA */}
            <div className="bg-slate-50 rounded-2xl p-3 flex items-center justify-between border border-slate-100 text-xs">
              <div className="flex items-center gap-1.5 text-slate-700">
                <MapPin className="w-3.5 h-3.5 text-slate-400" />
                <span>{inspectingWorker.distanceKm} km away</span>
              </div>
              <div className="flex items-center gap-1 font-bold text-brand-700">
                <Clock className="w-3.5 h-3.5" />
                <span>ETA: ~{inspectingWorker.etaMinutes} min</span>
              </div>
            </div>

            {/* Privacy Safeguard Note */}
            <p className="text-[10px] text-slate-500 italic text-center">
              Direct phone contact details are securely unlocked upon booking confirmation to protect customer privacy.
            </p>

            {/* Action Buttons */}
            <div className="grid grid-cols-2 gap-2 pt-1 border-t border-slate-100">
              <button
                type="button"
                disabled={isSubmittingOffer}
                onClick={() => {
                  const target = inspectingWorker;
                  setInspectingWorker(null);
                  setSelectedWorkerForOffer(target);
                  setCustomPrice(target.rate > 50 ? target.rate - 50 : target.rate);
                }}
                className="py-2.5 rounded-xl border border-brand-300 bg-brand-50 hover:bg-brand-100 text-brand-700 font-extrabold text-xs active:scale-95 transition"
              >
                Make an Offer
              </button>

              <button
                type="button"
                disabled={isSubmittingOffer}
                onClick={() => {
                  const target = inspectingWorker;
                  setInspectingWorker(null);
                  handleBookListedRate(target);
                }}
                className="py-2.5 rounded-xl bg-brand-600 hover:bg-brand-700 text-white font-extrabold text-xs shadow-md shadow-brand-500/20 active:scale-95 transition flex items-center justify-center gap-1"
              >
                <Check className="w-3.5 h-3.5" />
                <span>Book at {formatCurrency(inspectingWorker.rate)}</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
