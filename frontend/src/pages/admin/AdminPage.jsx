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
  Eye,
  X,
  XCircle,
  AlertTriangle,
  FileText,
  User,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export function AdminPage() {
  const { logout } = useAuthStore();
  const navigate = useNavigate();

  const [workerIdInput, setWorkerIdInput] = useState('');
  const [isApproving, setIsApproving] = useState(false);
  const [isRejecting, setIsRejecting] = useState(false);
  const [pendingList, setPendingList] = useState([]);
  const [isLoadingPending, setIsLoadingPending] = useState(false);
  const [recentlyApproved, setRecentlyApproved] = useState([]);
  const [sosAlerts, setSosAlerts] = useState([]);
  const [isLoadingSos, setIsLoadingSos] = useState(false);

  // Inspection Modal state
  const [activeReviewWorker, setActiveReviewWorker] = useState(null);
  const [idDocUrl, setIdDocUrl] = useState(null);
  const [selfieUrl, setSelfieUrl] = useState(null);
  const [isLoadingImages, setIsLoadingImages] = useState(false);

  // Reject dialog state
  const [rejectModalWorker, setRejectModalWorker] = useState(null);
  const [rejectReason, setRejectReason] = useState('');

  // Fetch pending verifications via trimmed DTO API
  const loadPendingWorkers = useCallback(async () => {
    setIsLoadingPending(true);
    try {
      const list = await api.getPendingVerifications();
      setPendingList(Array.isArray(list) ? list : []);
    } catch {
      setPendingList([]);
    } finally {
      setIsLoadingPending(false);
    }
  }, []);

  useEffect(() => {
    let active = true;
    api.getPendingVerifications().then((list) => {
      if (active) setPendingList(Array.isArray(list) ? list : []);
    }).catch(() => {
      if (active) setPendingList([]);
    });

    api.getAdminSosAlerts().then((alerts) => {
      if (active) setSosAlerts(Array.isArray(alerts) ? alerts : []);
    }).catch(() => {
      if (active) setSosAlerts([]);
    });

    return () => {
      active = false;
    };
  }, []);

  const openDocumentReview = async (worker) => {
    setActiveReviewWorker(worker);
    setIsLoadingImages(true);
    setIdDocUrl(null);
    setSelfieUrl(null);

    try {
      const idUrl = await api.getVerificationDocumentBlobUrl(worker.uid, 'id_document');
      setIdDocUrl(idUrl);
    } catch {
      setIdDocUrl(null);
    }

    try {
      const sfUrl = await api.getVerificationDocumentBlobUrl(worker.uid, 'selfie');
      setSelfieUrl(sfUrl);
    } catch {
      setSelfieUrl(null);
    }

    setIsLoadingImages(false);
  };

  const closeReviewModal = () => {
    setActiveReviewWorker(null);
    setIdDocUrl(null);
    setSelfieUrl(null);
  };

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

      closeReviewModal();
      loadPendingWorkers();
    } catch (err) {
      useToastStore.getState().error(err.message || 'Verification approval failed');
    } finally {
      setIsApproving(false);
    }
  };

  const handleRejectSubmit = async (e) => {
    e.preventDefault();
    if (!rejectModalWorker) return;
    if (!rejectReason.trim() || rejectReason.trim().length < 3) {
      useToastStore.getState().error('Please enter a valid rejection reason (min 3 characters)');
      return;
    }

    setIsRejecting(true);
    try {
      await api.rejectWorkerVerification(rejectModalWorker.uid, rejectReason.trim());
      useToastStore.getState().info(`Verification rejected for ${rejectModalWorker.uid}`);
      setRejectModalWorker(null);
      setRejectReason('');
      closeReviewModal();
      loadPendingWorkers();
    } catch (err) {
      useToastStore.getState().error(err.message || 'Rejection failed');
    } finally {
      setIsRejecting(false);
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

      {/* Manual Worker Approval Form */}
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

      {/* Pending Verifications Queue */}
      <div className="bg-white rounded-3xl p-5 border border-slate-200 shadow-sm space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Clock className="w-4 h-4 text-amber-500" />
            <h2 className="font-extrabold text-sm text-slate-900">Pending Review Queue</h2>
            <span className="px-2 py-0.5 rounded-full bg-amber-100 text-amber-800 text-[10px] font-bold">
              {pendingList.length}
            </span>
          </div>
          <button
            onClick={loadPendingWorkers}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 transition"
            title="Refresh"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoadingPending ? 'animate-spin' : ''}`} />
          </button>
        </div>

        {pendingList.length > 0 ? (
          <div className="space-y-2.5">
            {pendingList.map((w) => (
              <div
                key={w.uid}
                className="p-3.5 rounded-2xl border border-slate-100 bg-slate-50/70 space-y-2 text-xs"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <div className="flex items-center gap-1.5">
                      <span className="font-extrabold text-slate-900">{w.name}</span>
                      <span className="text-[9px] uppercase px-1.5 py-0.5 rounded bg-amber-100 text-amber-800 font-bold">
                        {w.status || 'pending'}
                      </span>
                    </div>
                    <p className="text-[10px] text-slate-500 font-mono mt-0.5">
                      UID: {w.uid} • {w.docType?.toUpperCase()} ({w.last4 ? `•••• ${w.last4}` : 'No doc#'}) • Attempt #{w.attemptCount || 1}
                    </p>
                  </div>

                  <div className="flex items-center gap-1.5">
                    <button
                      type="button"
                      onClick={() => openDocumentReview(w)}
                      className="px-2.5 py-1.5 rounded-xl bg-purple-50 hover:bg-purple-100 text-purple-700 text-[11px] font-bold border border-purple-200 flex items-center gap-1"
                    >
                      <Eye className="w-3.5 h-3.5" />
                      <span>Review</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => handleApprove(w.uid)}
                      disabled={isApproving}
                      className="px-3 py-1.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-[11px] font-bold shadow-sm active:scale-95 transition"
                    >
                      Approve
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        setRejectModalWorker(w);
                        setRejectReason('');
                      }}
                      className="px-2.5 py-1.5 rounded-xl bg-red-50 hover:bg-red-100 text-red-600 text-[11px] font-bold border border-red-200"
                    >
                      Reject
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="p-4 rounded-2xl bg-slate-50 border border-slate-100 text-center">
            <p className="text-xs text-slate-500 font-medium">
              No workers currently in queue.
            </p>
          </div>
        )}
      </div>

      {/* Document Review Modal */}
      {activeReviewWorker && (
        <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl max-w-md w-full p-5 shadow-2xl space-y-4">
            <div className="flex items-center justify-between pb-2 border-b border-slate-100">
              <div>
                <h3 className="font-extrabold text-sm text-slate-900">
                  Reviewing: {activeReviewWorker.name}
                </h3>
                <p className="text-[10px] text-slate-500 font-mono">
                  {activeReviewWorker.uid} • {activeReviewWorker.docType?.toUpperCase()} (•••• {activeReviewWorker.last4})
                </p>
              </div>
              <button onClick={closeReviewModal} className="p-1 rounded-full hover:bg-slate-100">
                <X className="w-4 h-4 text-slate-500" />
              </button>
            </div>

            {/* Document Images */}
            {isLoadingImages ? (
              <div className="py-8 text-center text-xs text-slate-400">Loading private document streams...</div>
            ) : (
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <span className="text-[10px] font-bold text-slate-700 flex items-center gap-1">
                    <FileText className="w-3 h-3 text-purple-600" /> ID Document
                  </span>
                  <div className="rounded-xl overflow-hidden border border-slate-200 bg-slate-100 h-32 flex items-center justify-center">
                    {idDocUrl ? (
                      <img src={idDocUrl} alt="ID Document" className="w-full h-full object-cover" />
                    ) : (
                      <span className="text-[10px] text-slate-400">Not on file</span>
                    )}
                  </div>
                </div>

                <div className="space-y-1">
                  <span className="text-[10px] font-bold text-slate-700 flex items-center gap-1">
                    <User className="w-3 h-3 text-purple-600" /> Live Selfie
                  </span>
                  <div className="rounded-xl overflow-hidden border border-slate-200 bg-slate-100 h-32 flex items-center justify-center">
                    {selfieUrl ? (
                      <img src={selfieUrl} alt="Selfie" className="w-full h-full object-cover" />
                    ) : (
                      <span className="text-[10px] text-slate-400">Not on file</span>
                    )}
                  </div>
                </div>
              </div>
            )}

            <div className="pt-2 flex items-center gap-2">
              <button
                onClick={() => handleApprove(activeReviewWorker.uid)}
                disabled={isApproving}
                className="flex-1 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs flex items-center justify-center gap-1"
              >
                <CheckCircle className="w-3.5 h-3.5" /> Approve
              </button>
              <button
                onClick={() => {
                  setRejectModalWorker(activeReviewWorker);
                  setRejectReason('');
                }}
                className="flex-1 py-2.5 rounded-xl bg-red-600 hover:bg-red-700 text-white font-bold text-xs flex items-center justify-center gap-1"
              >
                <XCircle className="w-3.5 h-3.5" /> Reject with Reason
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Reject Reason Modal */}
      {rejectModalWorker && (
        <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl max-w-sm w-full p-5 shadow-2xl space-y-3">
            <div className="flex items-center gap-2 text-red-600">
              <AlertTriangle className="w-5 h-5" />
              <h3 className="font-extrabold text-sm text-slate-900">Reject Verification</h3>
            </div>
            <p className="text-xs text-slate-600">
              Enter the reason for rejecting <strong className="font-mono">{rejectModalWorker.uid}</strong>. The worker will see this reason to fix their submission.
            </p>

            <form onSubmit={handleRejectSubmit} className="space-y-3 pt-1">
              <textarea
                required
                rows={3}
                value={rejectReason}
                onChange={(e) => setRejectReason(e.target.value)}
                placeholder="e.g. Document image is blurry and unreadable; name does not match Aadhaar..."
                className="w-full text-xs p-2.5 rounded-xl border border-slate-200 bg-slate-50 focus:bg-white focus:ring-2 focus:ring-red-500 focus:outline-none"
              />

              <div className="flex items-center gap-2">
                <button
                  type="submit"
                  disabled={isRejecting || rejectReason.trim().length < 3}
                  className="flex-1 py-2.5 rounded-xl bg-red-600 hover:bg-red-700 disabled:opacity-50 text-white font-bold text-xs"
                >
                  {isRejecting ? 'Rejecting...' : 'Confirm Rejection'}
                </button>
                <button
                  type="button"
                  onClick={() => setRejectModalWorker(null)}
                  className="px-3 py-2.5 rounded-xl bg-slate-100 text-slate-700 font-bold text-xs"
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Recent SOS Emergency Alerts (Fix 4: Admin minimal UI row) */}
      <div className="bg-white rounded-3xl p-5 border border-red-200 shadow-sm space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-red-600" />
            <h2 className="font-extrabold text-sm text-slate-900">Emergency SOS Dispatch Log</h2>
            <span className="px-2 py-0.5 rounded-full bg-red-100 text-red-800 text-[10px] font-bold">
              {sosAlerts.length}
            </span>
          </div>
          <button
            onClick={() => api.getAdminSosAlerts().then(setSosAlerts)}
            className="p-1 rounded-lg text-slate-400 hover:text-slate-700"
            title="Refresh SOS Log"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
        </div>

        {sosAlerts.length > 0 ? (
          <div className="space-y-2">
            {sosAlerts.map((alert) => (
              <div
                key={alert.id}
                className="p-3 rounded-2xl border border-slate-100 bg-slate-50/70 flex items-center justify-between text-xs"
              >
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-slate-900 font-mono text-[11px]">{alert.id}</span>
                    <span
                      className={`text-[9px] font-extrabold uppercase px-1.5 py-0.5 rounded ${
                        alert.status === 'notified'
                          ? 'bg-emerald-100 text-emerald-800'
                          : alert.status === 'partial'
                          ? 'bg-amber-100 text-amber-800'
                          : 'bg-red-100 text-red-800'
                      }`}
                    >
                      {alert.status}
                    </span>
                  </div>
                  <p className="text-[10px] text-slate-500 font-mono mt-0.5">
                    User: {alert.userId} • Job: {alert.jobId || 'Standalone'} • {alert.recipients?.length || 0} notified
                  </p>
                </div>

                {alert.mapsUrl && (
                  <a
                    href={alert.mapsUrl}
                    target="_blank"
                    rel="noreferrer"
                    className="px-2.5 py-1 rounded-xl bg-red-50 text-red-700 border border-red-200 text-[10px] font-bold hover:bg-red-100"
                  >
                    View Map
                  </a>
                )}
              </div>
            ))}
          </div>
        ) : (
          <p className="text-xs text-slate-400 italic text-center py-2">
            No emergency SOS alerts logged in this session.
          </p>
        )}
      </div>
    </div>
  );
}
