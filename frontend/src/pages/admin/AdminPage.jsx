import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../../api';
import { useAuthStore } from '../../store/authStore';
import { useToastStore } from '../../store/toastStore';
import {
  ShieldCheck,
  CheckCircle,
  UserCheck,
  LogOut,
  RefreshCw,
  Search,
  Clock,
  Sparkles,
  AlertCircle,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export function AdminPage() {
  const { logout } = useAuthStore();
  const navigate = useNavigate();

  const [workerIdInput, setWorkerIdInput] = useState('');
  const [isApproving, setIsApproving] = useState(false);
  const [pendingList, setPendingList] = useState([]);
  const [isLoadingPending, setIsLoadingPending] = useState(false);
  const [pendingError, setPendingError] = useState(null);
  const [recentlyApproved, setRecentlyApproved] = useState([]);

  // Fetch pending verifications via API abstraction
  const loadPendingWorkers = useCallback(async () => {
    setIsLoadingPending(true);
    setPendingError(null);
    try {
      const list = await api.getPendingVerifications();
      setPendingList(Array.isArray(list) ? list : []);
    } catch (err) {
      const status = err?.status || err?.response?.status;
      let errorMsg = "Couldn't reach the server";
      if (status === 401 || status === 403) {
        errorMsg = "You don't have permission or your session expired";
      } else if (status >= 500 || !status) {
        errorMsg = "Couldn't reach the server";
      } else if (err?.message) {
        errorMsg = err.message;
      }
      setPendingError({
        message: errorMsg,
        status,
      });
      setPendingList([]);
    } finally {
      setIsLoadingPending(false);
    }
  }, []);

  useEffect(() => {
    loadPendingWorkers();
  }, [loadPendingWorkers]);

  const handleApprove = async (targetUid) => {
    const uidToApprove = (targetUid || workerIdInput).trim();
    if (!uidToApprove) {
      useToastStore.getState().error('Please enter a Worker ID');
      return;
    }

    setIsApproving(true);
    try {
      const res = await api.approveWorkerVerification(uidToApprove);

      useToastStore.getState().success(
        `Worker ${res?.workerId || uidToApprove} verified & approved successfully!`
      );

      // Record in session recently approved list
      setRecentlyApproved((prev) => [
        {
          workerId: res?.workerId || uidToApprove,
          status: 'approved',
          approvedAt: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
        },
        ...prev.filter((item) => item.workerId !== (res?.workerId || uidToApprove)),
      ]);

      if (targetUid === undefined || targetUid === workerIdInput) {
        setWorkerIdInput('');
      }

      // Refresh list
      loadPendingWorkers();
    } catch (err) {
      // Backend returns 404 with exact detail message: "Worker with UID '...' not found"
      useToastStore.getState().error(err.message || 'Verification approval failed');
    } finally {
      setIsApproving(false);
    }
  };

  const handleLogout = () => {
    logout();
    useToastStore.getState().info('Admin logged out');
    navigate('/login');
  };

  return (
    <div className="space-y-5 pt-1">
      {/* Header */}
      <div className="flex items-center justify-between pb-2 border-b border-slate-200">
        <div className="flex items-center gap-2.5">
          <div className="w-10 h-10 rounded-2xl bg-purple-600 text-white flex items-center justify-center shadow-md shadow-purple-500/25">
            <ShieldCheck className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-lg font-black text-slate-900 tracking-tight">Admin Console</h1>
              <span className="text-[10px] font-black px-2 py-0.5 rounded-full bg-purple-100 text-purple-800 uppercase">
                Staff Only
              </span>
            </div>
            <p className="text-[11px] text-slate-500">Worker ID Verification &amp; Trust Approval</p>
          </div>
        </div>

        <button
          onClick={handleLogout}
          className="p-2 rounded-xl text-slate-400 hover:text-red-600 hover:bg-slate-100 transition"
          title="Logout Admin"
        >
          <LogOut className="w-4 h-4" />
        </button>
      </div>

      {/* Manual Worker Approval Form (Mandatory per constraint) */}
      <div className="bg-white rounded-3xl p-5 border border-slate-200 shadow-sm space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <UserCheck className="w-4 h-4 text-purple-600" />
            <h2 className="font-extrabold text-sm text-slate-900">Approve Worker by ID</h2>
          </div>
          <span className="text-[10px] text-slate-400 font-mono">POST /admin/verifications/...</span>
        </div>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleApprove();
          }}
          className="space-y-3"
        >
          <div>
            <label className="block text-[11px] font-bold text-slate-700 mb-1">
              Worker UID or Seed ID
            </label>
            <div className="relative">
              <input
                type="text"
                required
                value={workerIdInput}
                onChange={(e) => setWorkerIdInput(e.target.value)}
                placeholder="e.g. worker_plumber_unverified or worker_1729..."
                className="w-full text-xs p-2.5 pr-8 rounded-xl border border-slate-200 bg-slate-50 focus:bg-white focus:ring-2 focus:ring-purple-500 font-mono"
              />
              <Search className="w-4 h-4 text-slate-400 absolute right-2.5 top-2.5" />
            </div>
            <p className="text-[10px] text-slate-400 mt-1">
              Test unverified IDs: <code className="bg-slate-100 px-1 rounded text-purple-700 font-bold">worker_plumber_unverified</code>, <code className="bg-slate-100 px-1 rounded text-purple-700 font-bold">worker_elec_unverified</code>
            </p>
          </div>

          <button
            type="submit"
            disabled={isApproving || !workerIdInput.trim()}
            className="w-full py-3 rounded-xl bg-purple-600 hover:bg-purple-700 disabled:opacity-50 text-white font-extrabold text-xs shadow-md shadow-purple-500/25 active:scale-95 transition flex items-center justify-center gap-1.5"
          >
            <CheckCircle className="w-4 h-4" />
            <span>{isApproving ? 'Verifying...' : 'Approve & Verify Worker'}</span>
          </button>
        </form>
      </div>

      {/* Pending Verifications Queue (Drop-in ready for future GET list) */}
      <div className="bg-white rounded-3xl p-5 border border-slate-200 shadow-sm space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Clock className="w-4 h-4 text-amber-500" />
            <h2 className="font-extrabold text-sm text-slate-900">Pending Review Queue</h2>
          </div>
          <button
            onClick={loadPendingWorkers}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 transition"
            title="Refresh"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoadingPending ? 'animate-spin' : ''}`} />
          </button>
        </div>

        {isLoadingPending ? (
          <div className="p-6 rounded-2xl bg-slate-50 border border-slate-100 flex flex-col items-center justify-center gap-2 text-center">
            <RefreshCw className="w-5 h-5 text-purple-600 animate-spin" />
            <p className="text-xs text-slate-500 font-medium">Loading pending verifications...</p>
          </div>
        ) : pendingError ? (
          <div className="p-4 rounded-2xl bg-red-50 border border-red-200 text-center space-y-2">
            <div className="flex items-center justify-center gap-1.5 text-red-700 font-bold text-xs">
              <AlertCircle className="w-4 h-4 text-red-600 shrink-0" />
              <span>{pendingError.message}</span>
            </div>
            <button
              type="button"
              onClick={loadPendingWorkers}
              className="px-3.5 py-1.5 rounded-xl bg-red-600 hover:bg-red-700 text-white text-xs font-bold shadow-sm active:scale-95 transition inline-flex items-center gap-1.5"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Retry</span>
            </button>
          </div>
        ) : pendingList.length > 0 ? (
          <div className="space-y-2">
            {pendingList.map((w) => (
              <div
                key={w.uid}
                className="p-3 rounded-2xl border border-slate-100 bg-slate-50/70 flex items-center justify-between text-xs"
              >
                <div>
                  <div className="flex items-center gap-1.5">
                    <span className="font-extrabold text-slate-900">{w.name}</span>
                    <span className="text-[9px] uppercase px-1.5 py-0.5 rounded bg-amber-100 text-amber-800 font-bold">
                      {w.verificationStatus || 'unverified'}
                    </span>
                  </div>
                  <p className="text-[10px] text-slate-500 font-mono mt-0.5">{w.uid}</p>
                </div>

                <button
                  type="button"
                  onClick={() => handleApprove(w.uid)}
                  disabled={isApproving}
                  className="px-3 py-1.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-[11px] font-bold shadow-sm active:scale-95 transition"
                >
                  Approve
                </button>
              </div>
            ))}
          </div>
        ) : (
          <div className="p-4 rounded-2xl bg-slate-50 border border-slate-100 text-center">
            <p className="text-xs text-slate-500 font-medium">
              No pending verifications
            </p>
            <p className="text-[10px] text-slate-400 mt-0.5">
              Enter any newly registered or unverified worker UID above to approve immediately.
            </p>
          </div>
        )}
      </div>

      {/* Recently Approved in Session */}
      <div className="bg-white rounded-3xl p-5 border border-slate-200 shadow-sm space-y-3">
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-emerald-600" />
          <h2 className="font-extrabold text-sm text-slate-900">Recently Approved (Session)</h2>
        </div>

        {recentlyApproved.length > 0 ? (
          <div className="space-y-2">
            {recentlyApproved.map((item, idx) => (
              <div
                key={`${item.workerId}-${idx}`}
                className="p-2.5 rounded-2xl border border-emerald-100 bg-emerald-50/50 flex items-center justify-between text-xs"
              >
                <div className="flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 text-emerald-600" />
                  <div>
                    <span className="font-bold text-slate-900 font-mono text-[11px]">{item.workerId}</span>
                    <span className="text-[10px] text-slate-400 block">At {item.approvedAt}</span>
                  </div>
                </div>
                <span className="text-[10px] font-extrabold px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 uppercase">
                  Verified
                </span>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-xs text-slate-400 italic text-center py-2">
            No verifications approved in this session yet.
          </p>
        )}
      </div>
    </div>
  );
}
