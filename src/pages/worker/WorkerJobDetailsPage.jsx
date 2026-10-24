import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useJobStore } from '../../store/jobStore';
import { useAuthStore } from '../../store/authStore';
import { JOB_STATUS, OFFER_STATUS } from '../../types';
import { formatCurrency, formatTimeAgo } from '../../lib/utils';
import { SosButton } from '../../components/common/SosButton';
import { ReportModal } from '../../components/common/ReportModal';
import {
  ArrowLeft,
  MapPin,
  Clock,
  Phone,
  CheckCircle2,
  AlertCircle,
  Play,
  Check,
  TrendingUp,
  Flag,
  DollarSign,
  User,
} from 'lucide-react';

export function WorkerJobDetailsPage() {
  const { jobId } = useParams();
  const navigate = useNavigate();
  const { user } = useAuthStore();
  const {
    currentJob,
    fetchJob,
    offers,
    fetchOffers,
    createOffer,
    counterOffer,
    acceptOffer,
    startJob,
    completeJob,
    startPolling,
    stopPolling,
  } = useJobStore();

  const defaultRate = (user?.rates && user?.rates[job.category]) || job.budget || 350;
  const [quotePrice, setQuotePrice] = useState(defaultRate);
  const [counterPrice, setCounterPrice] = useState('');
  const [showCounterBox, setShowCounterBox] = useState(false);
  const [showReportModal, setShowReportModal] = useState(false);
  const [isActionLoading, setIsActionLoading] = useState(false);

  useEffect(() => {
    if (jobId) {
      startPolling(jobId);
    }
    return () => {
      stopPolling();
    };
  }, [jobId]);

  useEffect(() => {
    if (user?.rates && job?.category && user.rates[job.category]) {
      setQuotePrice(user.rates[job.category]);
    }
  }, [user, job?.category]);

  const job = currentJob || { id: jobId, status: JOB_STATUS.OPEN, category: 'Plumber' };
  const latestOffer = offers.length > 0 ? offers[offers.length - 1] : null;
  const isCustomerPendingOffer = latestOffer && latestOffer.status === OFFER_STATUS.PENDING && latestOffer.by === 'customer';

  // Worker sends initial quote / offer
  const handleSendInitialQuote = async (e) => {
    e.preventDefault();
    if (!quotePrice) return;
    setIsActionLoading(true);
    try {
      await createOffer({
        jobId,
        workerId: user?.uid,
        price: Number(quotePrice),
        by: 'worker',
      });
    } catch (err) {
      console.error(err);
    } finally {
      setIsActionLoading(false);
    }
  };

  // Worker accepts customer offer
  const handleAcceptOffer = async (offerId) => {
    setIsActionLoading(true);
    try {
      await acceptOffer(offerId);
    } catch (err) {
      console.error(err);
    } finally {
      setIsActionLoading(false);
    }
  };

  // Worker counters customer offer
  const handleCounterOffer = async (e) => {
    e.preventDefault();
    if (!counterPrice || !latestOffer) return;
    setIsActionLoading(true);
    try {
      await counterOffer(latestOffer.id, {
        price: Number(counterPrice),
        by: 'worker',
      });
      setShowCounterBox(false);
    } catch (err) {
      console.error(err);
    } finally {
      setIsActionLoading(false);
    }
  };

  // Worker starts job
  const handleStartJob = async () => {
    setIsActionLoading(true);
    try {
      await startJob(jobId);
    } catch (err) {
      console.error(err);
    } finally {
      setIsActionLoading(false);
    }
  };

  // Worker completes job
  const handleCompleteJob = async () => {
    setIsActionLoading(true);
    try {
      await completeJob(jobId);
      navigate('/worker/earnings');
    } catch (err) {
      console.error(err);
    } finally {
      setIsActionLoading(false);
    }
  };

  return (
    <div className="space-y-4 pt-1">
      {/* Header & Priority Emergency SOS */}
      <div className="flex items-center justify-between">
        <button
          onClick={() => navigate('/worker')}
          className="w-9 h-9 rounded-xl bg-white border border-slate-200 flex items-center justify-center text-slate-700 hover:bg-slate-100 active:scale-95 transition"
        >
          <ArrowLeft className="w-4 h-4" />
        </button>

        {/* SOS button visible on every active job */}
        <SosButton jobId={job.id} jobLocation={job.location} />
      </div>

      {/* Main Job Overview Card */}
      <div className="bg-white rounded-3xl p-5 border border-slate-200 shadow-sm space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-[10px] font-extrabold uppercase px-2.5 py-0.5 rounded-full bg-blue-100 text-blue-800">
            {job.category} Job
          </span>
          <span
            className={`text-[10px] font-extrabold px-2.5 py-0.5 rounded-full uppercase ${
              job.status === JOB_STATUS.COMPLETED
                ? 'bg-emerald-100 text-emerald-800'
                : job.status === JOB_STATUS.IN_PROGRESS
                ? 'bg-purple-100 text-purple-800 animate-pulse'
                : job.status === JOB_STATUS.ACCEPTED
                ? 'bg-amber-100 text-amber-800'
                : 'bg-slate-100 text-slate-800'
            }`}
          >
            {job.status.replace('_', ' ')}
          </span>
        </div>

        <div>
          <h2 className="text-base font-extrabold text-slate-900 leading-snug">
            {job.description}
          </h2>
          <div className="flex items-center gap-1.5 text-xs text-slate-500 mt-2">
            <MapPin className="w-4 h-4 text-brand-600 shrink-0" />
            <span className="font-medium">{job.location?.address}</span>
          </div>
        </div>

        <div className="bg-slate-50 rounded-2xl p-3 flex items-center justify-between border border-slate-100 text-xs">
          <div>
            <span className="text-[10px] text-slate-500 font-medium block">Customer</span>
            <span className="font-extrabold text-slate-900">{job.customerName || 'Priya Sharma'}</span>
          </div>
          <div className="text-right">
            <span className="text-[10px] text-slate-500 font-medium block">Customer Budget</span>
            <span className="font-extrabold text-brand-700 text-sm">
              {job.budget ? formatCurrency(job.budget) : 'Open to quote'}
            </span>
          </div>
        </div>

        {/* Customer phone & direct call if accepted/in-progress */}
        {[JOB_STATUS.ACCEPTED, JOB_STATUS.IN_PROGRESS].includes(job.status) && (
          <div className="pt-2 border-t border-slate-100 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-full bg-slate-100 flex items-center justify-center text-slate-700">
                <User className="w-4 h-4" />
              </div>
              <div className="text-xs">
                <p className="font-bold text-slate-900">{job.customerName || 'Customer'}</p>
                <p className="text-slate-500 text-[10px]">{job.customerPhone || '+91 98765 43210'}</p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <a
                href={`tel:${job.customerPhone || '9876543210'}`}
                className="px-3 py-1.5 rounded-xl bg-emerald-600 text-white text-xs font-bold flex items-center gap-1 shadow-sm"
              >
                <Phone className="w-3.5 h-3.5" /> Call
              </a>
              <button
                onClick={() => setShowReportModal(true)}
                className="p-2 rounded-xl text-slate-400 hover:text-red-600 hover:bg-slate-100"
                title="Report Customer"
              >
                <Flag className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* JOB LIFECYCLE ACTION STAGES */}

      {/* Stage 1: Accepted -> Start Job */}
      {job.status === JOB_STATUS.ACCEPTED && (
        <div className="bg-amber-50 border-2 border-amber-300 rounded-3xl p-5 space-y-3">
          <div className="flex items-center gap-2 text-amber-900 font-extrabold text-xs">
            <Clock className="w-4 h-4 text-amber-600 animate-spin" />
            <span>Offer Accepted! Final Agreed Price: {formatCurrency(job.finalPrice)}</span>
          </div>
          <p className="text-xs text-slate-600">
            Head to the customer&apos;s address. Once you reach their doorstep, tap the button below to start work.
          </p>
          <button
            disabled={isActionLoading}
            onClick={handleStartJob}
            className="w-full py-3.5 rounded-2xl bg-amber-600 hover:bg-amber-700 text-white font-extrabold text-xs shadow-lg shadow-amber-600/25 active:scale-95 transition min-h-touch flex items-center justify-center gap-2"
          >
            <Play className="w-4 h-4 fill-white" />
            <span>I HAVE ARRIVED &bull; START JOB</span>
          </button>
        </div>
      )}

      {/* Stage 2: In Progress -> Complete Job */}
      {job.status === JOB_STATUS.IN_PROGRESS && (
        <div className="bg-purple-50 border-2 border-purple-400 rounded-3xl p-5 space-y-3">
          <div className="flex items-center justify-between text-purple-900 font-extrabold text-xs">
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-purple-600 animate-ping" />
              Job Currently In Progress
            </span>
            <span className="text-sm font-black text-purple-950">
              {formatCurrency(job.finalPrice)}
            </span>
          </div>
          <div className="bg-white rounded-xl p-3 border border-purple-200 text-xs text-slate-700">
            <span className="font-bold text-slate-900">Payment Reminder:</span> Collect{' '}
            <span className="font-extrabold text-emerald-600">{formatCurrency(job.finalPrice)}</span> in cash directly from customer before marking complete.
          </div>
          <button
            disabled={isActionLoading}
            onClick={handleCompleteJob}
            className="w-full py-3.5 rounded-2xl bg-emerald-600 hover:bg-emerald-700 text-white font-extrabold text-xs shadow-lg shadow-emerald-600/25 active:scale-95 transition min-h-touch flex items-center justify-center gap-2"
          >
            <Check className="w-4 h-4 stroke-[3]" />
            <span>MARK COMPLETE &amp; COLLECT CASH</span>
          </button>
        </div>
      )}

      {/* Stage 3: Open / Negotiating -> Bidding & Countering */}
      {[JOB_STATUS.OPEN, JOB_STATUS.NEGOTIATING].includes(job.status) && (
        <div className="bg-white rounded-3xl p-5 border border-slate-200 shadow-sm space-y-4">
          <h3 className="font-extrabold text-sm text-slate-900 flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-brand-600" />
            <span>Negotiation &amp; Bids</span>
          </h3>

          {/* If customer sent an offer and it's pending */}
          {isCustomerPendingOffer && (
            <div className="bg-blue-50 border border-blue-200 rounded-2xl p-4 space-y-3">
              <div className="flex items-center justify-between">
                <div>
                  <span className="text-[10px] font-bold text-blue-800 uppercase block">Customer Proposal</span>
                  <p className="text-xl font-black text-blue-900">{formatCurrency(latestOffer.price)}</p>
                </div>
                <span className="text-[10px] bg-blue-200 text-blue-900 px-2 py-0.5 rounded font-bold uppercase">
                  Pending Your Action
                </span>
              </div>

              <div className="grid grid-cols-2 gap-2 pt-1">
                <button
                  disabled={isActionLoading}
                  onClick={() => handleAcceptOffer(latestOffer.id)}
                  className="py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-extrabold shadow-sm active:scale-95 transition"
                >
                  Accept at {formatCurrency(latestOffer.price)}
                </button>
                <button
                  disabled={isActionLoading}
                  onClick={() => {
                    setShowCounterBox(true);
                    setCounterPrice(latestOffer.price + 50);
                  }}
                  className="py-2.5 rounded-xl bg-white border border-brand-300 text-brand-700 text-xs font-extrabold active:scale-95 transition hover:bg-brand-50"
                >
                  Counter Offer
                </button>
              </div>
            </div>
          )}

          {/* Counter offer form */}
          {showCounterBox && (
            <form onSubmit={handleCounterOffer} className="space-y-3 bg-slate-50 p-4 rounded-2xl border border-slate-200">
              <label className="block text-xs font-bold text-slate-800">
                Enter Your Counter Rate (₹)
              </label>
              <div className="relative">
                <span className="absolute left-3.5 top-2.5 text-slate-400 font-bold text-sm">₹</span>
                <input
                  type="number"
                  required
                  min="100"
                  step="50"
                  value={counterPrice}
                  onChange={(e) => setCounterPrice(e.target.value)}
                  className="w-full text-base font-bold pl-8 pr-3 py-2 rounded-xl border border-slate-200 focus:ring-2 focus:ring-brand-500 bg-white"
                />
              </div>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => setShowCounterBox(false)}
                  className="flex-1 py-2 rounded-xl bg-slate-200 text-slate-700 text-xs font-bold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isActionLoading || !counterPrice}
                  className="flex-1 py-2 rounded-xl bg-brand-600 hover:bg-brand-700 text-white text-xs font-extrabold shadow-sm"
                >
                  Submit Counter
                </button>
              </div>
            </form>
          )}

          {/* Send Initial Quote Form if no active customer offer */}
          {!isCustomerPendingOffer && (
            <form onSubmit={handleSendInitialQuote} className="space-y-3 pt-1">
              <label className="block text-xs font-bold text-slate-800">
                Send Your Quote to Customer
              </label>
              <div className="relative">
                <span className="absolute left-3.5 top-2.5 text-slate-400 font-bold text-sm">₹</span>
                <input
                  type="number"
                  required
                  min="100"
                  step="50"
                  value={quotePrice}
                  onChange={(e) => setQuotePrice(e.target.value)}
                  className="w-full text-base font-black pl-8 pr-3 py-2.5 rounded-xl border border-slate-200 focus:ring-2 focus:ring-brand-500"
                />
              </div>
              <button
                type="submit"
                disabled={isActionLoading || !quotePrice}
                className="w-full py-3 rounded-2xl bg-brand-600 hover:bg-brand-700 text-white font-extrabold text-xs shadow-md shadow-brand-500/20 active:scale-95 transition min-h-touch"
              >
                Send Quote of {formatCurrency(quotePrice)}
              </button>
            </form>
          )}

          {/* Offers history list */}
          {offers.length > 0 && (
            <div className="pt-2 space-y-2">
              <p className="text-[11px] font-bold text-slate-500 uppercase">Offer History</p>
              {offers.map((off) => (
                <div
                  key={off.id}
                  className="flex justify-between items-center text-xs p-2.5 rounded-xl bg-slate-50 border border-slate-100"
                >
                  <div>
                    <span className="font-bold text-slate-800">
                      {off.by === 'worker' ? 'You offered' : 'Customer offered'}
                    </span>
                    <span className="text-[10px] text-slate-400 block">
                      {formatTimeAgo(off.createdAt)}
                    </span>
                  </div>
                  <div className="text-right">
                    <span className="font-extrabold text-brand-700 block">
                      {formatCurrency(off.price)}
                    </span>
                    <span className="text-[10px] uppercase font-bold text-slate-500">
                      {off.status}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Report Customer Modal */}
      <ReportModal
        isOpen={showReportModal}
        onClose={() => setShowReportModal(false)}
        jobId={job.id}
        targetUserId={job.customerId || 'cust_test'}
        targetUserName={job.customerName || 'Customer'}
      />
    </div>
  );
}
