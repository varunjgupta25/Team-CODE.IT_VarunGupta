import React from 'react';
import { useAuthStore } from '../../store/authStore';
import { TrustBadge } from '../../components/common/TrustBadge';
import { formatCurrency, computeTrust, formatTimeAgo } from '../../lib/utils';
import { storage } from '../../lib/storage';
import { JOB_STATUS } from '../../types';
import {
  Award,
  ShieldCheck,
  Star,
  CheckCircle2,
  Calendar,
  Briefcase,
} from 'lucide-react';

export function WorkerEarningsPage() {
  const { user } = useAuthStore();

  const jobsDone = user?.jobsDone || 0;
  const rating = user?.rating || 4.8;
  const tradeRate = user?.rates?.[user?.skills?.[0]] || 400;
  const estimatedEarnings = jobsDone * tradeRate;

  // Dynamically compute real trust score breakdown based on active worker
  const verifiedScore = user?.verified ? 30 : 0;
  const ratingScore = Math.min(30, Math.round(((rating) / 5) * 30));
  const jobsScore = Math.min(20, Math.round((jobsDone / 50) * 20));
  const accountAgeScore = 10;
  const cleanScore = (user?.reportCount || 0) > 0 ? 0 : 10;
  const trust = user ? computeTrust(user) : { score: 85, tier: 'Silver' };

  // Dynamically pull real completed jobs from storage for this worker
  const allStoredJobs = storage.get('rb_mock_jobs_v1', []);
  const myCompletedJobs = allStoredJobs.filter(
    (j) => j.status === JOB_STATUS.COMPLETED && (j.acceptedWorkerId === user?.uid || !j.acceptedWorkerId)
  );

  return (
    <div className="space-y-4 pt-1">
      {/* Title */}
      <div>
        <h1 className="text-xl font-black text-slate-900 tracking-tight">Earnings &amp; Trust</h1>
        <p className="text-xs text-slate-500">Track payouts and verified credibility score</p>
      </div>

      {/* Primary Balance / Earnings Card */}
      <div className="bg-gradient-to-br from-brand-600 to-indigo-800 rounded-3xl p-5 text-white shadow-xl space-y-4">
        <div className="flex items-center justify-between">
          <span className="text-xs font-bold text-white/80 uppercase tracking-wider">
            Total Net Earnings
          </span>
          <span className="text-[10px] font-black px-2.5 py-0.5 rounded-full bg-white/20 text-white backdrop-blur-sm">
            0% Commission (Direct Cash)
          </span>
        </div>

        <div>
          <p className="text-3xl font-black tracking-tight">{formatCurrency(estimatedEarnings)}</p>
          <p className="text-xs text-brand-100 mt-1">Paid directly by customers on job completion</p>
        </div>

        <div className="grid grid-cols-2 gap-2 pt-2 border-t border-white/15">
          <div>
            <span className="text-[10px] text-white/70 block font-medium">Completed Deliveries</span>
            <span className="text-base font-extrabold">{jobsDone} Jobs</span>
          </div>
          <div>
            <span className="text-[10px] text-white/70 block font-medium">Average Rating</span>
            <span className="text-base font-extrabold flex items-center gap-1">
              <Star className="w-4 h-4 fill-amber-300 text-amber-300" />
              {rating} / 5.0
            </span>
          </div>
        </div>
      </div>

      {/* Trust Score Breakdown (PRD F22) */}
      <div className="bg-white rounded-3xl p-5 border border-slate-200 shadow-sm space-y-3.5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-full bg-yellow-100 text-yellow-700 flex items-center justify-center">
              <Award className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-sm font-extrabold text-slate-900">Platform Trust Score</h2>
              <p className="text-[10px] text-slate-500">Formula (0–100): High trust = Top match rank</p>
            </div>
          </div>
          <TrustBadge score={trust.score} tier={trust.tier} />
        </div>

        <div className="space-y-2 text-xs text-slate-700 pt-1">
          <div className="flex justify-between items-center py-1.5 border-b border-slate-100">
            <span className="flex items-center gap-1.5 font-medium">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" /> Government ID Verified
            </span>
            <span className="font-extrabold text-emerald-600">{verifiedScore} / 30 pts</span>
          </div>

          <div className="flex justify-between items-center py-1.5 border-b border-slate-100">
            <span className="flex items-center gap-1.5 font-medium">
              <Star className="w-3.5 h-3.5 text-amber-500 fill-amber-400" /> Customer Ratings ({rating}★)
            </span>
            <span className="font-extrabold text-emerald-600">{ratingScore} / 30 pts</span>
          </div>

          <div className="flex justify-between items-center py-1.5 border-b border-slate-100">
            <span className="flex items-center gap-1.5 font-medium">
              <CheckCircle2 className="w-3.5 h-3.5 text-brand-600" /> Jobs Delivered ({jobsDone})
            </span>
            <span className="font-extrabold text-emerald-600">{jobsScore} / 20 pts</span>
          </div>

          <div className="flex justify-between items-center py-1.5 border-b border-slate-100">
            <span className="flex items-center gap-1.5 font-medium">
              <Calendar className="w-3.5 h-3.5 text-slate-500" /> Platform Longevity
            </span>
            <span className="font-extrabold text-emerald-600">{accountAgeScore} / 10 pts</span>
          </div>

          <div className="flex justify-between items-center py-1.5">
            <span className="flex items-center gap-1.5 font-medium">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" /> Clean Incident Record
            </span>
            <span className="font-extrabold text-emerald-600">{cleanScore} / 10 pts</span>
          </div>
        </div>
      </div>

      {/* Recent Completed Jobs */}
      <div className="bg-white rounded-3xl p-5 border border-slate-200 shadow-sm space-y-3">
        <h3 className="font-extrabold text-sm text-slate-900 flex items-center gap-1.5">
          <Briefcase className="w-4 h-4 text-brand-600" />
          <span>Completed Jobs History</span>
        </h3>

        {myCompletedJobs.length === 0 ? (
          <p className="text-xs text-slate-500 text-center py-4">
            No completed jobs logged in this session yet. Complete jobs from your feed to see receipts here!
          </p>
        ) : (
          <div className="space-y-2.5">
            {myCompletedJobs.map((item) => (
              <div
                key={item.id}
                className="p-3 rounded-2xl bg-slate-50 border border-slate-100 flex items-center justify-between text-xs"
              >
                <div>
                  <p className="font-bold text-slate-900">{item.description}</p>
                  <div className="flex items-center gap-2 text-[10px] text-slate-500 mt-0.5">
                    <span>{formatTimeAgo(item.completedAt || item.updatedAt)}</span>
                    <span>&bull;</span>
                    <span>{item.customerName || 'Customer'}</span>
                  </div>
                </div>
                <div className="text-right">
                  <span className="text-sm font-black text-emerald-600">
                    +{formatCurrency(item.finalPrice || tradeRate)}
                  </span>
                  <span className="text-[10px] text-slate-400 block font-medium">Cash Paid</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
