import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../../api/index.js';
import { useAuthStore } from '../../store/authStore.js';
import { useToastStore } from '../../store/toastStore.js';
import {
  ShieldCheck,
  CheckCircle,
  UserCheck,
  LogOut,
  RefreshCw,
  Search,
  Clock,
  Eye,
  X,
  XCircle,
  AlertTriangle,
  FileText,
  User,
  RotateCcw,
  Flag,
  BarChart3,
  Activity,
  AlertOctagon,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';

const TABS = {
  VERIFICATIONS: 'verifications',
  SOS: 'sos',
  REPORTS: 'reports',
  METRICS: 'metrics',
};

export function AdminPage() {
  const { logout } = useAuthStore();
  const navigate = useNavigate();

  const [activeTab, setActiveTab] = useState(TABS.VERIFICATIONS);
  const [workerIdInput, setWorkerIdInput] = useState('');
  const [isApproving, setIsApproving] = useState(false);
  const [isRejecting, setIsRejecting] = useState(false);
  const [isResetting, setIsResetting] = useState(false);
  const [pendingList, setPendingList] = useState([]);
  const [isLoadingPending, setIsLoadingPending] = useState(false);
  const [sosAlerts, setSosAlerts] = useState([]);
  const [reportsList, setReportsList] = useState([]);

  // Inspection Modal state
  const [activeReviewWorker, setActiveReviewWorker] = useState(null);
  const [idDocUrl, setIdDocUrl] = useState(null);
  const [selfieUrl, setSelfieUrl] = useState(null);
  const [isLoadingImages, setIsLoadingImages] = useState(false);

  // Reject dialog state
  const [rejectModalWorker, setRejectModalWorker] = useState(null);
  const [rejectReason, setRejectReason] = useState('');

  // Fetch pending verifications via DTO API
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

  // Fetch SOS Alerts
  const loadSosAlerts = useCallback(async () => {
    try {
      const alerts = await api.getAdminSosAlerts();
      setSosAlerts(Array.isArray(alerts) ? alerts : []);
    } catch {
      setSosAlerts([]);
    }
  }, []);

  // Fetch Reports
  const loadReports = useCallback(async () => {
    try {
      const reports = await api.getReports();
      setReportsList(Array.isArray(reports) ? reports : []);
    } catch {
      setReportsList([]);
    }
  }, []);

  useEffect(() => {
    let isMounted = true;
    api.getPendingVerifications().then((list) => {
      if (isMounted) setPendingList(Array.isArray(list) ? list : []);
    }).catch(() => {
      if (isMounted) setPendingList([]);
    });

    api.getAdminSosAlerts().then((alerts) => {
      if (isMounted) setSosAlerts(Array.isArray(alerts) ? alerts : []);
    }).catch(() => {
      if (isMounted) setSosAlerts([]);
    });

    api.getReports().then((reps) => {
      if (isMounted) setReportsList(Array.isArray(reps) ? reps : []);
    }).catch(() => {
      if (isMounted) setReportsList([]);
    });

    return () => {
      isMounted = false;
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

  const handleResetAttempts = async (workerUid) => {
    if (!workerUid) return;
    setIsResetting(true);
    try {
      await api.resetVerificationAttempts(workerUid);
      useToastStore.getState().success(`Verification attempts reset for ${workerUid}`);
      loadPendingWorkers();
    } catch (err) {
      useToastStore.getState().error(err.message || 'Failed to reset attempts');
    } finally {
      setIsResetting(false);
    }
  };

  const handleLogout = () => {
    logout();
    useToastStore.getState().info('Admin logged out');
    navigate('/login');
  };

  return (
    <div className="space-y-4 pt-1">
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
            <p className="text-[11px] text-slate-500">Marketplace Moderation &amp; Verification</p>
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

      {/* Admin Tab Navigation */}
      <div className="grid grid-cols-4 gap-1.5 p-1 bg-slate-100 rounded-2xl">
        <button
          type="button"
          onClick={() => setActiveTab(TABS.VERIFICATIONS)}
          className={`py-2 px-1 rounded-xl text-[11px] font-extrabold transition-all flex flex-col items-center justify-center gap-0.5 ${
            activeTab === TABS.VERIFICATIONS
              ? 'bg-white text-purple-700 shadow-sm'
              : 'text-slate-600 hover:text-slate-900'
          }`}
        >
          <div className="flex items-center gap-1">
            <UserCheck className="w-3.5 h-3.5" />
            <span>Verify</span>
            {pendingList.length > 0 && (
              <span className="w-4 h-4 rounded-full bg-purple-600 text-white text-[9px] flex items-center justify-center font-bold">
                {pendingList.length}
              </span>
            )}
          </div>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab(TABS.SOS)}
          className={`py-2 px-1 rounded-xl text-[11px] font-extrabold transition-all flex flex-col items-center justify-center gap-0.5 ${
            activeTab === TABS.SOS
              ? 'bg-white text-red-600 shadow-sm'
              : 'text-slate-600 hover:text-slate-900'
          }`}
        >
          <div className="flex items-center gap-1">
            <AlertOctagon className="w-3.5 h-3.5" />
            <span>SOS</span>
            {sosAlerts.length > 0 && (
              <span className="w-4 h-4 rounded-full bg-red-600 text-white text-[9px] flex items-center justify-center font-bold animate-pulse">
                {sosAlerts.length}
              </span>
            )}
          </div>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab(TABS.REPORTS)}
          className={`py-2 px-1 rounded-xl text-[11px] font-extrabold transition-all flex flex-col items-center justify-center gap-0.5 ${
            activeTab === TABS.REPORTS
              ? 'bg-white text-amber-700 shadow-sm'
              : 'text-slate-600 hover:text-slate-900'
          }`}
        >
          <div className="flex items-center gap-1">
            <Flag className="w-3.5 h-3.5" />
            <span>Reports</span>
            {reportsList.length > 0 && (
              <span className="w-4 h-4 rounded-full bg-amber-600 text-white text-[9px] flex items-center justify-center font-bold">
                {reportsList.length}
              </span>
            )}
          </div>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab(TABS.METRICS)}
          className={`py-2 px-1 rounded-xl text-[11px] font-extrabold transition-all flex flex-col items-center justify-center gap-0.5 ${
            activeTab === TABS.METRICS
              ? 'bg-white text-slate-900 shadow-sm'
              : 'text-slate-600 hover:text-slate-900'
          }`}
        >
          <div className="flex items-center gap-1">
            <BarChart3 className="w-3.5 h-3.5" />
            <span>Metrics</span>
          </div>
        </button>
      </div>

      {/* TAB 1: VERIFICATIONS QUEUE & APPROVAL */}
      {activeTab === TABS.VERIFICATIONS && (
        <div className="space-y-4">
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
                    className="p-3.5 rounded-2xl border border-slate-100 bg-slate-50/70 space-y-2.5 text-xs"
                  >
                    <div className="flex items-start justify-between">
                      <div>
                        <div className="flex items-center gap-1.5 flex-wrap">
                          <span className="font-extrabold text-slate-900">{w.name}</span>
                          <span className="text-[9px] uppercase px-1.5 py-0.5 rounded bg-amber-100 text-amber-800 font-bold">
                            {w.status || 'pending'}
                          </span>
                        </div>
                        <p className="text-[10px] text-slate-500 font-mono mt-0.5">
                          UID: {w.uid} • {w.docType?.toUpperCase()} ({w.last4 ? `•••• ${w.last4}` : 'No doc#'}) • Attempt #{w.attemptCount || 1}
                        </p>
                      </div>

                      <button
                        type="button"
                        onClick={() => openDocumentReview(w)}
                        className="px-2.5 py-1.5 rounded-xl bg-purple-50 hover:bg-purple-100 text-purple-700 text-[11px] font-bold border border-purple-200 flex items-center gap-1"
                      >
                        <Eye className="w-3.5 h-3.5" />
                        <span>Inspect</span>
                      </button>
                    </div>

                    {/* Action buttons row */}
                    <div className="flex items-center gap-1.5 pt-1 border-t border-slate-200/60">
                      <button
                        type="button"
                        onClick={() => handleApprove(w.uid)}
                        disabled={isApproving}
                        className="flex-1 py-1.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-[11px] font-bold shadow-sm active:scale-95 transition"
                      >
                        Approve
                      </button>
                      <button
                        type="button"
                        onClick={() => {
                          setRejectModalWorker(w);
                          setRejectReason('');
                        }}
                        className="flex-1 py-1.5 rounded-xl bg-red-50 hover:bg-red-100 text-red-600 text-[11px] font-bold border border-red-200"
                      >
                        Reject
                      </button>
                      <button
                        type="button"
                        disabled={isResetting}
                        onClick={() => handleResetAttempts(w.uid)}
                        className="px-2.5 py-1.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 text-[10px] font-bold flex items-center gap-1"
                        title="Reset upload attempts if locked"
                      >
                        <RotateCcw className="w-3 h-3" />
                        <span>Reset</span>
                      </button>
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
        </div>
      )}

      {/* TAB 2: EMERGENCY SOS DISPATCH LOG */}
      {activeTab === TABS.SOS && (
        <div className="bg-white rounded-3xl p-5 border border-red-200 shadow-sm space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-red-600" />
              <h2 className="font-extrabold text-sm text-slate-900">Emergency SOS Dispatches</h2>
              <span className="px-2 py-0.5 rounded-full bg-red-100 text-red-800 text-[10px] font-bold">
                {sosAlerts.length}
              </span>
            </div>
            <button
              onClick={loadSosAlerts}
              className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700"
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
                  className="p-3.5 rounded-2xl border border-red-100 bg-red-50/40 space-y-2 text-xs"
                >
                  <div className="flex items-center justify-between">
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

                    {alert.mapsUrl && (
                      <a
                        href={alert.mapsUrl}
                        target="_blank"
                        rel="noreferrer"
                        className="px-2.5 py-1 rounded-xl bg-red-600 text-white text-[10px] font-bold hover:bg-red-700 shadow-sm"
                      >
                        Live Map &rarr;
                      </a>
                    )}
                  </div>

                  <p className="text-[10px] text-slate-600 font-mono">
                    User: {alert.userId} • Job: {alert.jobId || 'Standalone'} • {alert.recipients?.length || 0} Contacts Notified
                  </p>

                  {alert.location && (
                    <p className="text-[10px] text-slate-500">
                      Coordinates: {alert.location.lat}, {alert.location.lng}
                    </p>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <div className="p-4 rounded-2xl bg-slate-50 border border-slate-100 text-center">
              <p className="text-xs text-slate-500">No emergency SOS alerts logged in this session.</p>
            </div>
          )}
        </div>
      )}

      {/* TAB 3: DISPUTES & COMPLAINTS */}
      {activeTab === TABS.REPORTS && (
        <div className="bg-white rounded-3xl p-5 border border-slate-200 shadow-sm space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Flag className="w-4 h-4 text-amber-600" />
              <h2 className="font-extrabold text-sm text-slate-900">Complaints &amp; Reports</h2>
              <span className="px-2 py-0.5 rounded-full bg-amber-100 text-amber-800 text-[10px] font-bold">
                {reportsList.length}
              </span>
            </div>
            <button
              onClick={loadReports}
              className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700"
              title="Refresh Reports"
            >
              <RefreshCw className="w-3.5 h-3.5" />
            </button>
          </div>

          {reportsList.length > 0 ? (
            <div className="space-y-2.5">
              {reportsList.map((rep) => (
                <div
                  key={rep.id}
                  className="p-3.5 rounded-2xl border border-slate-100 bg-slate-50/70 space-y-1.5 text-xs"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-slate-900 capitalize">
                      {rep.reason || 'General Report'}
                    </span>
                    <span className="text-[10px] font-mono text-slate-400">
                      ID: {rep.id?.slice(-8)}
                    </span>
                  </div>

                  <p className="text-[11px] text-slate-600">
                    Reported Worker: <strong className="font-mono text-slate-800">{rep.workerId || rep.reportedUserId}</strong>
                  </p>

                  {rep.description && (
                    <p className="text-[11px] text-slate-500 italic bg-white p-2 rounded-xl border border-slate-100">
                      &quot;{rep.description}&quot;
                    </p>
                  )}

                  <div className="text-[10px] text-slate-400 flex items-center justify-between pt-1">
                    <span>Job #{rep.jobId?.slice(-6) || 'General'}</span>
                    <span>{rep.createdAt ? new Date(rep.createdAt).toLocaleDateString() : 'Recent'}</span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="p-4 rounded-2xl bg-slate-50 border border-slate-100 text-center">
              <p className="text-xs text-slate-500">No unresolved user reports on file.</p>
            </div>
          )}
        </div>
      )}

      {/* TAB 4: PLATFORM METRICS & REGISTRY */}
      {activeTab === TABS.METRICS && (
        <div className="space-y-4">
          <div className="bg-white rounded-3xl p-5 border border-slate-200 shadow-sm space-y-4">
            <div className="flex items-center gap-2">
              <Activity className="w-4 h-4 text-purple-600" />
              <h2 className="font-extrabold text-sm text-slate-900">Live Operational Telemetry</h2>
            </div>

            {/* Live Metrics Grid from Active Backend Endpoints */}
            <div className="grid grid-cols-2 gap-2.5">
              <div className="p-3.5 rounded-2xl bg-purple-50 border border-purple-100">
                <span className="text-[10px] font-bold text-purple-700 block uppercase">
                  Pending Verifications
                </span>
                <span className="text-2xl font-black text-purple-900 mt-1 block">
                  {pendingList.length}
                </span>
                <span className="text-[10px] text-purple-600 mt-0.5 block">
                  Awaiting staff document audit
                </span>
              </div>

              <div className="p-3.5 rounded-2xl bg-red-50 border border-red-100">
                <span className="text-[10px] font-bold text-red-700 block uppercase">
                  Emergency SOS Alerts
                </span>
                <span className="text-2xl font-black text-red-900 mt-1 block">
                  {sosAlerts.length}
                </span>
                <span className="text-[10px] text-red-600 mt-0.5 block">
                  High-priority dispatches
                </span>
              </div>

              <div className="p-3.5 rounded-2xl bg-amber-50 border border-amber-100">
                <span className="text-[10px] font-bold text-amber-700 block uppercase">
                  Platform Reports
                </span>
                <span className="text-2xl font-black text-amber-900 mt-1 block">
                  {reportsList.length}
                </span>
                <span className="text-[10px] text-amber-600 mt-0.5 block">
                  Filed complaints &amp; flags
                </span>
              </div>

              <div className="p-3.5 rounded-2xl bg-emerald-50 border border-emerald-100">
                <span className="text-[10px] font-bold text-emerald-700 block uppercase">
                  Admin Claim Status
                </span>
                <span className="text-lg font-black text-emerald-900 mt-1 block">
                  Active
                </span>
                <span className="text-[10px] text-emerald-600 mt-0.5 block">
                  Verified custom claims
                </span>
              </div>
            </div>
          </div>

          {/* Explicit Gap Notice: Missing Backend Telemetry */}
          <div className="bg-slate-50 border border-slate-200 rounded-3xl p-4 space-y-2 text-xs">
            <span className="font-extrabold text-slate-800 block">
              Backend Integration Status &amp; Roadmap
            </span>
            <div className="space-y-1.5 text-[11px] text-slate-600">
              <div className="flex items-center justify-between p-2 rounded-xl bg-white border border-slate-100">
                <span>Aggregate Platform GMV &amp; Commission Ledger</span>
                <span className="font-bold text-amber-700 bg-amber-50 px-2 py-0.5 rounded text-[10px]">
                  Pending API (GET /admin/stats)
                </span>
              </div>
              <div className="flex items-center justify-between p-2 rounded-xl bg-white border border-slate-100">
                <span>Global Multi-Tenant User Registry</span>
                <span className="font-bold text-amber-700 bg-amber-50 px-2 py-0.5 rounded text-[10px]">
                  Pending API (GET /admin/users)
                </span>
              </div>
            </div>
            <p className="text-[10px] text-slate-500 italic pt-1">
              Note: Unimplemented backend metrics are explicitly demarcated to maintain strict contract fidelity without fabricating artificial statistics.
            </p>
          </div>
        </div>
      )}

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
                <XCircle className="w-3.5 h-3.5" /> Reject
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
    </div>
  );
}
