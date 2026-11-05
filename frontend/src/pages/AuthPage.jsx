import React, { useState, useEffect } from 'react';
import { useAuthStore } from '../store/authStore';
import { ROLES, CATEGORIES } from '../types';
import {
  User,
  Briefcase,
  ShieldCheck,
  ArrowRight,
  RotateCcw,
  AlertCircle,
  RefreshCw,
  PhoneCall,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useToastStore } from '../store/toastStore';
import { api } from '../api';
import { auth } from '../lib/firebase';
import { RecaptchaVerifier, signInWithPhoneNumber } from 'firebase/auth';

// Helper to format phone number to E.164 (defaults to India +91)
const formatPhoneE164 = (raw) => {
  const cleaned = (raw || '').replace(/\D/g, '');
  if (cleaned.startsWith('91') && cleaned.length === 12) {
    return `+${cleaned}`;
  }
  return `+91${cleaned.slice(-10)}`;
};

// Map Firebase Auth error codes to user-friendly messages
const getFriendlyAuthError = (err) => {
  const code = err?.code || '';
  if (code === 'auth/invalid-phone-number') {
    return 'The phone number entered is invalid. Please check and try again.';
  }
  if (code === 'auth/too-many-requests') {
    return 'Too many attempts. Please wait a few minutes before trying again.';
  }
  if (code === 'auth/invalid-verification-code') {
    return 'Invalid verification code. Please enter the correct 6-digit code received on your phone.';
  }
  if (code === 'auth/code-expired') {
    return 'Verification code has expired. Please request a new OTP.';
  }
  if (code === 'auth/quota-exceeded') {
    return 'SMS quota exceeded for today. Please try again later or contact support.';
  }
  if (code === 'auth/missing-phone-number') {
    return 'Phone number is required.';
  }
  if (code === 'auth/captcha-check-failed') {
    return 'reCAPTCHA check failed. Please refresh the page and try again.';
  }
  return err?.message || 'Authentication failed. Please try again.';
};

export function AuthPage() {
  const {
    loginAsCustomer,
    loginAsWorker,
    loginAsAdmin,
    syncStatus,
    lastError,
    retryLastSync,
  } = useAuthStore();
  const navigate = useNavigate();

  // Active portal tab: 'customer' or 'worker'
  const [activePortal, setActivePortal] = useState(ROLES.CUSTOMER);

  // Form states - user entered data is kept throughout retries
  const [phone, setPhone] = useState('');
  const [name, setName] = useState('');
  const [selectedTrade, setSelectedTrade] = useState('plumber');
  const [rate, setRate] = useState('350');

  // Firebase Phone Auth states
  const [confirmationResult, setConfirmationResult] = useState(null);
  const [otpSent, setOtpSent] = useState(false);
  const [otpInput, setOtpInput] = useState('');
  const [isSendingOtp, setIsSendingOtp] = useState(false);
  const [isVerifying, setIsVerifying] = useState(false);
  const [resendCountdown, setResendCountdown] = useState(0);

  const isSyncing = syncStatus === 'syncing' || isSendingOtp || isVerifying;

  // Cleanup reCAPTCHA verifier on unmount
  useEffect(() => {
    return () => {
      if (window.recaptchaVerifier) {
        try {
          window.recaptchaVerifier.clear();
        } catch {}
        window.recaptchaVerifier = null;
      }
    };
  }, []);

  // 30-second countdown timer for resend OTP
  useEffect(() => {
    if (resendCountdown <= 0) return;
    const timer = setInterval(() => {
      setResendCountdown((prev) => (prev > 0 ? prev - 1 : 0));
    }, 1000);
    return () => clearInterval(timer);
  }, [resendCountdown]);

  // Setup / reset invisible RecaptchaVerifier
  const getOrCreateRecaptchaVerifier = () => {
    if (window.recaptchaVerifier) {
      try {
        window.recaptchaVerifier.clear();
      } catch {}
      window.recaptchaVerifier = null;
    }
    const container = document.getElementById('recaptcha-container');
    if (!container) {
      throw new Error('reCAPTCHA container missing from DOM.');
    }
    const verifier = new RecaptchaVerifier(auth, 'recaptcha-container', {
      size: 'invisible',
      callback: () => {
        // Invisible reCAPTCHA solved
      },
    });
    window.recaptchaVerifier = verifier;
    return verifier;
  };

  // Switch portal tab
  const handleTabChange = (portal) => {
    if (isSyncing) return; // Prevent tab switch during active submission
    setActivePortal(portal);
    setOtpSent(false);
    setConfirmationResult(null);
    setOtpInput('');
    setPhone('');
    setName('');
  };

  // Step 1: Send OTP via Firebase Phone Auth
  const handleRequestOtp = async (e) => {
    if (e) e.preventDefault();
    if (isSyncing) return;

    const cleaned = (phone || '').replace(/\D/g, '');
    if (!cleaned || cleaned.length < 10) {
      useToastStore.getState().error('Please enter a valid 10-digit mobile number');
      return;
    }

    setIsSendingOtp(true);
    const formattedPhone = formatPhoneE164(phone);

    try {
      const appVerifier = getOrCreateRecaptchaVerifier();
      const confirmation = await signInWithPhoneNumber(auth, formattedPhone, appVerifier);
      setConfirmationResult(confirmation);
      setOtpSent(true);
      setResendCountdown(30);
      useToastStore.getState().success(`Verification code sent via SMS to ${formattedPhone}`);
    } catch (err) {
      const friendlyMsg = getFriendlyAuthError(err);
      useToastStore.getState().error(friendlyMsg);
      if (window.recaptchaVerifier) {
        try {
          window.recaptchaVerifier.clear();
        } catch {}
        window.recaptchaVerifier = null;
      }
    } finally {
      setIsSendingOtp(false);
    }
  };

  // Resend OTP
  const triggerOtpResend = async () => {
    if (resendCountdown > 0 || isSyncing) return;
    await handleRequestOtp();
  };

  // Step 2: Verify OTP via Firebase confirmationResult & Sign In / Register
  const handleVerifyOtp = async (e) => {
    e.preventDefault();
    if (isSyncing) return;

    if (!confirmationResult) {
      useToastStore.getState().error('No active verification session. Please request a new OTP.');
      setOtpSent(false);
      return;
    }

    const trimmedCode = otpInput.trim();
    if (trimmedCode.length !== 6) {
      useToastStore.getState().error('Please enter the 6-digit verification code received on your phone.');
      return;
    }

    setIsVerifying(true);
    try {
      // Confirm OTP code with Firebase Phone Auth
      const userCredential = await confirmationResult.confirm(trimmedCode);
      const firebaseUser = userCredential.user;
      const formattedPhone = formatPhoneE164(phone);

      if (activePortal === ROLES.CUSTOMER) {
        await loginAsCustomer({
          uid: firebaseUser.uid,
          name: name.trim() || 'Customer',
          phone: firebaseUser.phoneNumber || formattedPhone,
        });
        useToastStore.getState().success('Customer login successful!');
        navigate('/');
      } else {
        await loginAsWorker({
          uid: firebaseUser.uid,
          name: name.trim() || 'Tradesman',
          phone: firebaseUser.phoneNumber || formattedPhone,
          skills: [selectedTrade],
          rates: { [selectedTrade]: Number(rate) },
          verified: false,
          verificationStatus: 'unverified',
        });
        useToastStore.getState().success('Worker registered & logged in!');
        navigate('/worker');
      }
    } catch (err) {
      // Keep form fields (name, phone, trade, rate, otpInput) intact
      const friendlyMsg = getFriendlyAuthError(err);
      useToastStore.getState().error(friendlyMsg);
    } finally {
      setIsVerifying(false);
    }
  };

  // Retry the failed registration / sync call
  const handleRetrySync = async () => {
    if (isSyncing) return;
    try {
      await retryLastSync();
      if (activePortal === ROLES.CUSTOMER) {
        useToastStore.getState().success('Customer registration successful!');
        navigate('/');
      } else {
        useToastStore.getState().success('Worker registration successful!');
        navigate('/worker');
      }
    } catch {
      // Handled by store (toast + inline error banner)
    }
  };

  const handleResetData = () => {
    api.resetMockData();
    useToastStore.getState().info('Mock data reset to initial state!');
  };

  return (
    <div className="space-y-5 pt-1">
      {/* Invisible container required by Firebase Phone Authentication */}
      <div id="recaptcha-container"></div>

      {/* Brand Heading */}
      <div className="text-center space-y-1">
        <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-brand-50 text-brand-700 text-[11px] font-extrabold mb-1">
          <ShieldCheck className="w-3.5 h-3.5" />
          <span>Firebase Phone Authentication</span>
        </div>
        <h1 className="text-2xl font-black text-slate-900 tracking-tight">Sign In to RepairBuddy</h1>
        <p className="text-xs text-slate-500">
          Separate, dedicated login system for Customers and Service Workers
        </p>
      </div>

      {/* Visible Inline Banner for Registration / Sync Failures with Retry Button */}
      {syncStatus === 'failed' && lastError && (
        <div className="p-4 rounded-2xl bg-red-50 border border-red-200 flex items-center justify-between gap-3 text-xs text-red-900 shadow-sm animate-in fade-in">
          <div className="flex items-start gap-2.5">
            <AlertCircle className="w-5 h-5 text-red-600 shrink-0 mt-0.5" />
            <div>
              <p className="font-extrabold text-red-800">Registration / Sync Failed</p>
              <p className="text-[11px] text-red-600 mt-0.5">{lastError}</p>
            </div>
          </div>
          <button
            type="button"
            onClick={handleRetrySync}
            disabled={isSyncing}
            className="px-3.5 py-2 rounded-xl bg-red-600 hover:bg-red-700 disabled:opacity-50 text-white font-bold text-xs shadow-sm active:scale-95 transition shrink-0 flex items-center gap-1.5"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isSyncing ? 'animate-spin' : ''}`} />
            <span>{isSyncing ? 'Retrying...' : 'Retry'}</span>
          </button>
        </div>
      )}

      {/* Strict Portal Tabs */}
      <div className="bg-slate-200/80 p-1.5 rounded-2xl grid grid-cols-2 gap-1.5">
        <button
          type="button"
          onClick={() => handleTabChange(ROLES.CUSTOMER)}
          disabled={isSyncing}
          className={`py-2.5 rounded-xl text-xs font-black transition-all flex items-center justify-center gap-2 ${
            activePortal === ROLES.CUSTOMER
              ? 'bg-white text-brand-700 shadow-md shadow-slate-300'
              : 'text-slate-600 hover:text-slate-900'
          }`}
        >
          <User className="w-4 h-4" />
          <span>Customer Portal</span>
        </button>

        <button
          type="button"
          onClick={() => handleTabChange(ROLES.WORKER)}
          disabled={isSyncing}
          className={`py-2.5 rounded-xl text-xs font-black transition-all flex items-center justify-center gap-2 ${
            activePortal === ROLES.WORKER
              ? 'bg-white text-amber-700 shadow-md shadow-slate-300'
              : 'text-slate-600 hover:text-slate-900'
          }`}
        >
          <Briefcase className="w-4 h-4" />
          <span>Worker Portal</span>
        </button>
      </div>

      {/* Main Authentication Box */}
      <div className="bg-white rounded-3xl p-5 border border-slate-200 shadow-sm space-y-4">
        <div className="border-b border-slate-100 pb-3">
          <h2 className="font-extrabold text-sm text-slate-900">
            {activePortal === ROLES.CUSTOMER ? 'Customer Verification' : 'Tradesman & Worker Sign In'}
          </h2>
          <p className="text-[11px] text-slate-500 mt-0.5">
            {activePortal === ROLES.CUSTOMER
              ? 'Sign in to request, negotiate, and book 30-min services'
              : 'Sign in to accept nearby jobs, submit bids, and track earnings'}
          </p>
        </div>

        {!otpSent ? (
          /* Step 1: Phone Entry */
          <form onSubmit={handleRequestOtp} className="space-y-3.5">
            <div>
              <label className="block text-[11px] font-bold text-slate-700 mb-1">Full Name</label>
              <input
                type="text"
                required
                disabled={isSyncing}
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder={activePortal === ROLES.CUSTOMER ? 'Enter your full name' : 'Enter worker name'}
                className="w-full text-xs px-3.5 py-2.5 rounded-xl border border-slate-200 bg-slate-50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
            </div>

            <div>
              <label className="block text-[11px] font-bold text-slate-700 mb-1">Mobile Number (E.164)</label>
              <div className="flex gap-2">
                <span className="px-3 py-2.5 rounded-xl bg-slate-100 border border-slate-200 text-xs font-bold text-slate-600">
                  +91
                </span>
                <input
                  type="tel"
                  required
                  maxLength="10"
                  disabled={isSyncing}
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  placeholder="10-digit mobile number"
                  className="flex-1 text-xs px-3.5 py-2.5 rounded-xl border border-slate-200 bg-slate-50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-brand-500"
                />
              </div>
            </div>

            {/* If Worker, provide trade selection */}
            {activePortal === ROLES.WORKER && (
              <div className="space-y-3 pt-1 border-t border-slate-100">
                <div>
                  <label className="block text-[11px] font-bold text-slate-700 mb-1">Primary Skill</label>
                  <select
                    disabled={isSyncing}
                    value={selectedTrade}
                    onChange={(e) => setSelectedTrade(e.target.value)}
                    className="w-full text-xs px-3 py-2.5 rounded-xl border border-slate-200 bg-slate-50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-brand-500"
                  >
                    {CATEGORIES.map((cat) => (
                      <option key={cat.id} value={cat.id}>
                        {cat.label} (Standard: ₹{cat.typicalRate})
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-[11px] font-bold text-slate-700 mb-1">Base Rate (₹/visit)</label>
                  <input
                    type="number"
                    min="100"
                    step="50"
                    disabled={isSyncing}
                    value={rate}
                    onChange={(e) => setRate(e.target.value)}
                    className="w-full text-xs px-3 py-2.5 rounded-xl border border-slate-200 bg-slate-50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-brand-500"
                  />
                </div>
              </div>
            )}

            <button
              type="submit"
              disabled={isSyncing || !phone || phone.replace(/\D/g, '').length < 10}
              className="w-full py-3.5 rounded-2xl bg-brand-600 hover:bg-brand-700 disabled:opacity-50 text-white font-extrabold text-xs shadow-md shadow-brand-500/20 active:scale-95 transition min-h-touch flex items-center justify-center gap-2"
            >
              {isSendingOtp ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  <span>Sending SMS OTP...</span>
                </>
              ) : (
                <>
                  <span>Send Firebase Verification Code</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </form>
        ) : (
          /* Step 2: Firebase OTP Verification */
          <form onSubmit={handleVerifyOtp} className="space-y-4 animate-in fade-in">
            <div className="bg-emerald-50 border border-emerald-200 rounded-2xl p-3 text-xs text-emerald-900 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <PhoneCall className="w-4 h-4 text-emerald-600 shrink-0" />
                <div>
                  <p className="font-extrabold">SMS Code Sent</p>
                  <p className="text-[11px] text-emerald-700">Sent to {formatPhoneE164(phone)}</p>
                </div>
              </div>
              <button
                type="button"
                onClick={triggerOtpResend}
                disabled={resendCountdown > 0 || isSyncing}
                className="text-xs font-bold text-emerald-700 hover:text-emerald-900 disabled:text-emerald-400 disabled:cursor-not-allowed underline transition"
              >
                {resendCountdown > 0 ? `Resend in ${resendCountdown}s` : 'Resend OTP'}
              </button>
            </div>

            <div>
              <label className="block text-[11px] font-bold text-slate-700 mb-1">
                Enter 6-Digit SMS Code
              </label>
              <input
                type="text"
                required
                maxLength="6"
                disabled={isSyncing}
                value={otpInput}
                onChange={(e) => setOtpInput(e.target.value.replace(/\D/g, ''))}
                placeholder="123456"
                className="w-full text-center text-xl font-black tracking-widest px-3 py-3 rounded-xl border border-slate-200 bg-slate-50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
            </div>

            <div className="flex gap-2">
              <button
                type="button"
                disabled={isSyncing}
                onClick={() => {
                  setOtpSent(false);
                  setConfirmationResult(null);
                  setOtpInput('');
                }}
                className="flex-1 py-3 rounded-xl bg-slate-100 hover:bg-slate-200 disabled:opacity-50 text-slate-700 text-xs font-bold"
              >
                Change Number
              </button>
              <button
                type="submit"
                disabled={isSyncing || otpInput.trim().length !== 6}
                className="flex-1 py-3 rounded-xl bg-brand-600 hover:bg-brand-700 disabled:opacity-50 text-white text-xs font-extrabold shadow-md shadow-brand-500/20 active:scale-95 transition flex items-center justify-center gap-1.5"
              >
                {isSyncing ? (
                  <>
                    <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                    <span>Verifying...</span>
                  </>
                ) : (
                  <span>Verify &amp; Sign In</span>
                )}
              </button>
            </div>
          </form>
        )}

        {/* 1-Click Fast Testing Accounts */}
        <div className="pt-3 border-t border-slate-100 space-y-2">
          <p className="text-[10px] font-extrabold uppercase tracking-wider text-slate-400">
            Fast Testing Accounts
          </p>
          {activePortal === ROLES.WORKER ? (
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                disabled={isSyncing}
                onClick={async () => {
                  try {
                    await loginAsWorker({
                      uid: 'w_plumb_unverified',
                      name: 'Kamlesh Verma',
                      phone: '+91 91101 00005',
                      verified: false,
                      verificationStatus: 'unverified',
                      skills: ['plumber'],
                      rates: { plumber: 300 },
                    });
                    useToastStore.getState().info('Logged in as Unverified Worker');
                    navigate('/worker');
                  } catch {
                    // Store records lastError and shows banner/toast
                  }
                }}
                className="p-2.5 rounded-xl border border-amber-200 bg-amber-50 hover:bg-amber-100 disabled:opacity-50 text-left transition"
              >
                <div className="flex items-center gap-1.5 text-amber-900 font-extrabold text-[11px]">
                  <span className="w-2 h-2 rounded-full bg-amber-500" />
                  <span>Unverified Worker</span>
                </div>
                <p className="text-[10px] text-amber-700 mt-0.5">Test Document Upload</p>
              </button>

              <button
                type="button"
                disabled={isSyncing}
                onClick={async () => {
                  try {
                    await loginAsWorker({
                      uid: 'w_plumb_1',
                      name: 'Ramesh Kanojia',
                      phone: '+91 98201 12345',
                      verified: true,
                      verificationStatus: 'approved',
                      skills: ['plumber'],
                      rates: { plumber: 350 },
                    });
                    useToastStore.getState().success('Logged in as Verified Worker');
                    navigate('/worker');
                  } catch {
                    // Store records lastError and shows banner/toast
                  }
                }}
                className="p-2.5 rounded-xl border border-emerald-200 bg-emerald-50 hover:bg-emerald-100 disabled:opacity-50 text-left transition"
              >
                <div className="flex items-center gap-1.5 text-emerald-900 font-extrabold text-[11px]">
                  <span className="w-2 h-2 rounded-full bg-emerald-500" />
                  <span>Verified Worker</span>
                </div>
                <p className="text-[10px] text-emerald-700 mt-0.5">Ramesh Kanojia (Plumber)</p>
              </button>
            </div>
          ) : (
            <button
              type="button"
              disabled={isSyncing}
              onClick={async () => {
                try {
                  await loginAsCustomer({
                    uid: 'cust_priya',
                    name: 'Priya Sharma',
                    phone: '+91 98200 11001',
                  });
                  useToastStore.getState().success('Logged in as Priya Sharma');
                  navigate('/');
                } catch {
                  // Store records lastError and shows banner/toast
                }
              }}
              className="w-full p-2.5 rounded-xl border border-blue-200 bg-blue-50 hover:bg-blue-100 disabled:opacity-50 text-left transition flex items-center justify-between"
            >
              <div>
                <span className="font-extrabold text-blue-900 text-xs">Priya Sharma</span>
                <p className="text-[10px] text-blue-700">Mira Road East • Customer</p>
              </div>
              <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-blue-200 text-blue-800">
                1-Click Sign In
              </span>
            </button>
          )}
        </div>
      </div>

      {/* Reset Mock DB */}
      <div className="text-center pt-2 space-y-1">
        <div>
          <button
            onClick={handleResetData}
            className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-400 hover:text-slate-700 transition p-1.5"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>Reset All Mock Data to Default</span>
          </button>
        </div>
        <div>
          <button
            type="button"
            onClick={() => {
              loginAsAdmin();
              useToastStore.getState().success('Logged in as Administrator');
              navigate('/admin');
            }}
            className="text-[11px] text-slate-400 hover:text-purple-600 underline font-medium transition py-1"
          >
            Administrator Console
          </button>
        </div>
      </div>
    </div>
  );
}
