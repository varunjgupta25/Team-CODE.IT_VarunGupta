import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useJobStore } from '../../store/jobStore';
import { JOB_STATUS, OFFER_STATUS } from '../../types';
import { formatCurrency, formatTimeAgo } from '../../lib/utils';
import { SosButton } from '../../components/common/SosButton';
import { ReportModal } from '../../components/common/ReportModal';
import { EmptyState } from '../../components/common/EmptyState';
import { RouteMap } from '../../components/map/RouteMap';
import {
  Clock,
  CheckCircle2,
  Phone,
  Flag,
  TrendingUp,
  MapPin,
  RefreshCw,
  Star,
  Zap,
} from 'lucide-react';
import { storage } from '../../lib/storage';
import { api } from '../../api';

const STATUS_STEPS = [
  { key: JOB_STATUS.OPEN, label: 'Matching' },
  { key: JOB_STATUS.NEGOTIATING, label: 'Offers' },
  { key: JOB_STATUS.ACCEPTED, label: 'En Route' },
  { key: JOB_STATUS.IN_PROGRESS, label: 'In Progress' },
  { key: JOB_STATUS.COMPLETED, label: 'Done' },
];

export function JobStatusPage() {
  const { jobId: routeJobId } = useParams();
  const navigate = useNavigate();
  const {
    currentJob,
    offers,
    acceptOffer,
    counterOffer,
    rejectOffer,
    startPolling,
    stopPolling,
  } = useJobStore();

  const [counterInputPrice, setCounterInputPrice] = useState('');
  const [activeCounterOfferId, setActiveCounterOfferId] = useState(null);
  const [showReportModal, setShowReportModal] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [workerDetails, setWorkerDetails] = useState(null);

  const activeJobId = routeJobId || currentJob?.id;

  // 5-second polling loop as requested in PRD & constraints
  useEffect(() => {
    if (activeJobId) {
      startPolling(activeJobId);
    }
    return () => {
      stopPolling();
    };
  }, [activeJobId, startPolling, stopPolling]);

  const job = currentJob || { id: activeJobId, status: JOB_STATUS.OPEN, category: 'Service' };
  const assignedWorkerId =
    job.acceptedWorkerId ||
    (offers.length > 0 ? offers[offers.length - 1]?.workerId : null);

  useEffect(() => {
    if (assignedWorkerId) {
      api.getWorker(assignedWorkerId)
        .then((res) => {
          if (res) setWorkerDetails(res);
        })
        .catch(() => {});
    }
  }, [assignedWorkerId]);

  if (!currentJob && !activeJobId) {
    return (
      <EmptyState
        title="No active job found"
        description="You don't have any ongoing job requests. Pick a service to get started."
        actionLabel="Book a Service"
        onAction={() => navigate('/')}
      />
    );
  }

  const allWorkers = storage.get('rb_mock_workers_v1', []) || [];
  const matchedWorkerObj = workerDetails || allWorkers.find((w) => w.uid === assignedWorkerId);
  const assignedWorker = matchedWorkerObj || (assignedWorkerId ? {
    uid: assignedWorkerId,
    name: 'Assigned Worker',
    phone: '',
    rating: 5.0,
    jobsDone: 0,
    avatarUrl: 'https://images.unsplash.com/photo-1540569014015-19a7be504e3a?w=150&auto=format&fit=crop&q=80',
    location: { lat: 19.2812, lng: 72.8697 },
  } : null);

  const currentStepIdx = STATUS_STEPS.findIndex((s) => s.key === job.status);
  const latestOffer = offers.length > 0 ? offers[offers.length - 1] : null;
  const isPendingCustomerOffer = latestOffer && latestOffer.status === OFFER_STATUS.PENDING && latestOffer.by === 'customer';

  // Handle Accept
  const handleAccept = async (offerId) => {
    setIsProcessing(true);
    try {
      await acceptOffer(offerId);
    } catch (err) {
      console.error(err);
    } finally {
      setIsProcessing(false);
    }
  };

  // Handle Counter
  const handleCounter = async (e) => {
    e.preventDefault();
    if (!counterInputPrice || !activeCounterOfferId) return;
    setIsProcessing(true);
    try {
      await counterOffer(activeCounterOfferId, {
        price: Number(counterInputPrice),
        by: 'customer',
      });
      setActiveCounterOfferId(null);
      setCounterInputPrice('');
    } catch (err) {
      console.error(err);
    } finally {
      setIsProcessing(false);
    }
  };

  // Handle Decline
  const handleReject = async (offerId) => {
    setIsProcessing(true);
    try {
      await rejectOffer(offerId);
    } catch (err) {
      console.error(err);
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="space-y-4 pt-1">
      {/* Top Header & Priority SOS Button */}
      <div className="flex items-center justify-between">
        <div>
          <span className="text-[10px] font-extrabold uppercase px-2 py-0.5 rounded-full bg-slate-200 text-slate-800">
            Job #{job.id?.slice(-6) || 'LIVE'}
          </span>
          <h1 className="text-lg font-black text-slate-900 tracking-tight capitalize mt-0.5">
            {job.category} Service
          </h1>
        </div>

        {/* SOS Button Visible on active-job screen */}
        <SosButton jobId={job.id} jobLocation={job.location} />
      </div>

      {/* Live Status Tracker Bar */}
      <div className="bg-white rounded-2xl p-4 border border-slate-200 shadow-sm space-y-2">
        <div className="flex justify-between items-center text-xs">
          <span className="font-extrabold text-slate-900 capitalize">
            Status: <span className="text-brand-600">{job.status.replace('_', ' ')}</span>
          </span>
          <span className="text-[10px] font-semibold text-slate-400 flex items-center gap-1">
            <RefreshCw className="w-3 h-3 animate-spin" /> Live 5s sync
          </span>
        </div>

        {/* Step progress pills */}
        <div className="grid grid-cols-5 gap-1 pt-1">
          {STATUS_STEPS.map((step, idx) => {
            const isPassed = currentStepIdx >= idx;
            const isCurrent = currentStepIdx === idx;
            return (
              <div key={step.key} className="text-center space-y-1">
                <div
                  className={`h-2 rounded-full transition-all ${
                    isPassed ? 'bg-brand-600' : 'bg-slate-200'
                  } ${isCurrent ? 'ring-2 ring-brand-400 ring-offset-1 animate-pulse' : ''}`}
                />
                <span
                  className={`text-[9px] block font-bold leading-tight ${
                    isPassed ? 'text-slate-900' : 'text-slate-400'
                  }`}
                >
                  {step.label}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Assigned Worker Card if Accepted or In Progress */}
      {[JOB_STATUS.ACCEPTED, JOB_STATUS.IN_PROGRESS].includes(job.status) && assignedWorker && (
        <div className="bg-white rounded-3xl p-4 border-2 border-brand-500 shadow-md space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-1 text-[11px] font-black text-brand-700 bg-brand-50 px-2.5 py-1 rounded-full">
              <Zap className="w-3.5 h-3.5 fill-brand-600 text-brand-600" />
              <span>
                {job.status === JOB_STATUS.IN_PROGRESS ? 'Service In Progress' : 'Provider is En Route (~12 min)'}
              </span>
            </div>
            <span className="text-sm font-black text-slate-900">
              Agreed: {formatCurrency(job.finalPrice)}
            </span>
          </div>

          <div className="flex items-center justify-between pt-1">
            <div className="flex items-center gap-3">
              <img
                src={assignedWorker.avatarUrl}
                alt={assignedWorker.name}
                className="w-12 h-12 rounded-full object-cover border-2 border-brand-500"
              />
              <div>
                <h3 className="font-extrabold text-sm text-slate-900">{assignedWorker.name}</h3>
                <div className="flex items-center gap-1 text-amber-500 font-bold text-xs">
                  <Star className="w-3 h-3 fill-amber-400 text-amber-400" />
                  <span>{assignedWorker.rating}</span>
                  <span className="text-slate-400 font-normal">({assignedWorker.jobsDone} jobs)</span>
                </div>
              </div>
            </div>

            <a
              href={`tel:${assignedWorker.phone}`}
              className="w-10 h-10 rounded-2xl bg-emerald-600 text-white flex items-center justify-center shadow-md shadow-emerald-500/20 active:scale-95 transition"
              title="Call Worker"
            >
              <Phone className="w-4 h-4" />
            </a>
          </div>

          <div className="flex items-center justify-between pt-2 border-t border-slate-100 text-xs text-slate-600">
            <div className="flex items-center gap-1 text-[11px]">
              <MapPin className="w-3.5 h-3.5 text-slate-400" />
              <span className="line-clamp-1">{job.location?.address}</span>
            </div>
            <button
              onClick={() => setShowReportModal(true)}
              className="text-[11px] font-bold text-slate-400 hover:text-red-600 flex items-center gap-1"
            >
              <Flag className="w-3 h-3" /> Report
            </button>
          </div>

          {/* Road Network Route Map with Live Polling */}
          <div className="pt-2">
            <RouteMap
              jobId={job.id}
              workerId={assignedWorker.uid}
              workerLocation={assignedWorker.location}
              customerLocation={job.location}
              height="220px"
            />
          </div>
        </div>
      )}

      {/* Completed Job Screen Banner */}
      {job.status === JOB_STATUS.COMPLETED && (
        <div className="bg-emerald-50 border-2 border-emerald-500 rounded-3xl p-5 text-center space-y-3">
          <div className="w-14 h-14 rounded-full bg-emerald-100 text-emerald-600 mx-auto flex items-center justify-center">
            <CheckCircle2 className="w-8 h-8" />
          </div>
          <div>
            <h2 className="text-lg font-black text-slate-900">Work Completed!</h2>
            <p className="text-xs text-slate-600 mt-1">
              Final paid amount: <span className="font-bold text-emerald-700">{formatCurrency(job.finalPrice)}</span> (Cash on completion)
            </p>
          </div>
          <button
            onClick={() => navigate(`/customer/review/${job.id}`)}
            className="w-full py-3.5 rounded-2xl bg-emerald-600 hover:bg-emerald-700 text-white font-extrabold text-xs shadow-lg shadow-emerald-600/25 active:scale-95 transition min-h-touch flex items-center justify-center gap-2"
          >
            <Star className="w-4 h-4 fill-white" />
            <span>Rate &amp; Review Worker</span>
          </button>
        </div>
      )}

      {/* Negotiation Offer Timeline */}
      <div className="bg-white rounded-3xl p-5 border border-slate-200 shadow-sm space-y-4">
        <div className="flex items-center justify-between pb-2 border-b border-slate-100">
          <h3 className="font-extrabold text-sm text-slate-900 flex items-center gap-1.5">
            <TrendingUp className="w-4 h-4 text-brand-600" />
            <span>Negotiation &amp; Offer Timeline</span>
          </h3>
          <span className="text-[11px] text-slate-500 font-semibold">{offers.length} updates</span>
        </div>

        {offers.length === 0 ? (
          <p className="text-xs text-slate-500 text-center py-4">
            No bids or offers exchanged yet. Worker is reviewing your job.
          </p>
        ) : (
          <div className="space-y-3">
            {offers.map((offer, idx) => {
              const isWorker = offer.by === 'worker';
              const isAccepted = offer.status === OFFER_STATUS.ACCEPTED;
              const isRejected = offer.status === OFFER_STATUS.REJECTED;

              return (
                <div
                  key={offer.id || idx}
                  className={`p-3.5 rounded-2xl border transition-all ${
                    isAccepted
                      ? 'bg-emerald-50 border-emerald-300'
                      : isRejected
                      ? 'bg-slate-50 border-slate-200 opacity-60'
                      : isWorker
                      ? 'bg-blue-50/70 border-blue-200'
                      : 'bg-amber-50/70 border-amber-200'
                  }`}
                >
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-extrabold text-slate-900">
                      {isWorker ? 'Provider Proposed' : 'You Proposed'}
                    </span>
                    <span className="text-base font-black text-brand-700">
                      {formatCurrency(offer.price)}
                    </span>
                  </div>

                  <div className="flex items-center justify-between text-[11px] text-slate-500 mt-1">
                    <span>{formatTimeAgo(offer.createdAt)}</span>
                    <span
                      className={`font-bold px-2 py-0.5 rounded uppercase text-[10px] ${
                        isAccepted
                          ? 'bg-emerald-200 text-emerald-900'
                          : isRejected
                          ? 'bg-slate-200 text-slate-700'
                          : 'bg-amber-100 text-amber-800 animate-pulse'
                      }`}
                    >
                      {offer.status}
                    </span>
                  </div>

                  {/* If this is the latest pending offer from worker, customer can respond */}
                  {offer.status === OFFER_STATUS.PENDING && isWorker && (
                    <div className="mt-3 pt-2.5 border-t border-blue-200/80 space-y-2">
                      <p className="text-[11px] font-bold text-slate-700">
                        Worker proposed {formatCurrency(offer.price)}. Respond:
                      </p>

                      <div className="grid grid-cols-3 gap-2">
                        <button
                          disabled={isProcessing}
                          onClick={() => handleAccept(offer.id)}
                          className="py-2 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-extrabold text-xs shadow-sm active:scale-95 transition"
                        >
                          Accept
                        </button>

                        <button
                          disabled={isProcessing}
                          onClick={() => {
                            setActiveCounterOfferId(offer.id);
                            setCounterInputPrice(offer.price - 50 > 0 ? offer.price - 50 : offer.price);
                          }}
                          className="py-2 rounded-xl bg-brand-50 hover:bg-brand-100 text-brand-700 border border-brand-300 font-extrabold text-xs active:scale-95 transition"
                        >
                          Counter
                        </button>

                        <button
                          disabled={isProcessing}
                          onClick={() => handleReject(offer.id)}
                          className="py-2 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 font-extrabold text-xs active:scale-95 transition"
                        >
                          Decline
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}

            {/* Waiting for response state */}
            {isPendingCustomerOffer && (
              <div className="bg-amber-50 border border-amber-200 rounded-2xl p-3 text-xs text-amber-800 flex items-center gap-2">
                <Clock className="w-4 h-4 text-amber-600 shrink-0 animate-spin" />
                <span>Offer sent. Waiting for worker to accept or counter...</span>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Inline Counter Dialog */}
      {activeCounterOfferId && (
        <div className="bg-white rounded-3xl p-4 border-2 border-brand-500 shadow-xl space-y-3">
          <h4 className="font-extrabold text-xs text-slate-900">Enter Your Counter Offer</h4>
          <form onSubmit={handleCounter} className="space-y-3">
            <div className="relative">
              <span className="absolute left-3 top-2 text-slate-400 font-bold text-sm">₹</span>
              <input
                type="number"
                required
                min="100"
                step="25"
                value={counterInputPrice}
                onChange={(e) => setCounterInputPrice(e.target.value)}
                placeholder="Enter counter amount"
                className="w-full text-sm font-black pl-7 pr-3 py-2 rounded-xl border border-slate-200 focus:ring-2 focus:ring-brand-500"
              />
            </div>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setActiveCounterOfferId(null)}
                className="flex-1 py-2 rounded-xl bg-slate-100 text-slate-700 text-xs font-bold"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isProcessing || !counterInputPrice}
                className="flex-1 py-2 rounded-xl bg-brand-600 hover:bg-brand-700 text-white text-xs font-extrabold shadow-md shadow-brand-500/20"
              >
                Send Counter
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Report Modal */}
      <ReportModal
        isOpen={showReportModal}
        onClose={() => setShowReportModal(false)}
        jobId={job.id}
        targetUserId={assignedWorker?.uid || ''}
        targetUserName={assignedWorker?.name || 'Worker'}
      />
    </div>
  );
}
