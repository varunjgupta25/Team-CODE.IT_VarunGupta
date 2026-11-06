import React, { useState } from 'react';
import { useAuthStore } from '../store/authStore';
import { ROLES, CATEGORIES } from '../types';
import {
  User,
  Briefcase,
  ShieldCheck,
  ArrowRight,
  RotateCcw,
  Zap,
  CheckCircle2,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useToastStore } from '../store/toastStore';
import { api } from '../api';

export function AuthPage() {
  const { loginAsCustomer, loginAsWorker, loginAsAdmin, requestPhoneOtp, confirmPhoneOtp } = useAuthStore();
  const navigate = useNavigate();

  // Active portal tab: 'customer' or 'worker'
  const [activePortal, setActivePortal] = useState(ROLES.CUSTOMER);

  // Form states
  const [phone, setPhone] = useState('');
  const [name, setName] = useState('');
  const [selectedTrade, setSelectedTrade] = useState('plumber');
  const [rate, setRate] = useState('350');
  
  // OTP flow states
  const [otpSent, setOtpSent] = useState(false);
  const [otpInput, setOtpInput] = useState('');
  const [simulatedCode, setSimulatedCode] = useState('');
  const [isVerifying, setIsVerifying] = useState(false);

  // Switch portal tab
  const handleTabChange = (portal) => {
    setActivePortal(portal);
    setOtpSent(false);
    setOtpInput('');
    setPhone('');
    setName('');
  };

  // Step 1: Send OTP
  const handleRequestOtp = async (e) => {
    e.preventDefault();
    if (!phone || phone.length < 10) {
      useToastStore.getState().error('Please enter a valid 10-digit mobile number');
      return;
    }

    try {
      setIsVerifying(true);
      const cleanPhone = phone.trim().replace(/^(\+91|0)/, '');
      const formattedPhone = `+91${cleanPhone}`;
      const result = await requestPhoneOtp(formattedPhone, 'recaptcha-container');
      setIsVerifying(false);
      setOtpSent(true);
      if (result.isFirebase) {
        setSimulatedCode('');
        useToastStore.getState().success(`Verification code sent to ${formattedPhone}!`);
      } else {
        setSimulatedCode(result.otp || '1234');
        useToastStore.getState().info(`SMS Sent! Verification OTP is: ${result.otp || '1234'}`);
      }
    } catch (err) {
      setIsVerifying(false);
      useToastStore.getState().error(err.message || 'Failed to send OTP. Please check phone number.');
    }
  };

  // Step 2: Verify OTP & Sign In
  const handleVerifyOtp = async (e) => {
    e.preventDefault();
    if (!otpInput) {
      useToastStore.getState().error('Please enter the OTP');
      return;
    }

    setIsVerifying(true);
    try {
      const resolvedUser = await confirmPhoneOtp(otpInput.trim());
      const cleanPhone = phone.trim().replace(/^(\+91|0)/, '');
      const formattedPhone = `+91 ${cleanPhone}`;

      if (activePortal === ROLES.ADMIN) {
        await loginAsAdmin({
          uid: resolvedUser?.uid,
          name: name.trim() || 'Administrator',
          phone: formattedPhone,
        });
        useToastStore.getState().success('Administrator login successful!');
        navigate('/admin');
      } else if (activePortal === ROLES.CUSTOMER) {
        await loginAsCustomer({
          uid: resolvedUser?.uid,
          name: name.trim() || 'Customer',
          phone: formattedPhone,
        });
        useToastStore.getState().success('Customer login successful!');
        navigate('/');
      } else {
        await loginAsWorker({
          uid: resolvedUser?.uid,
          name: name.trim() || 'Tradesman',
          phone: formattedPhone,
          skills: [selectedTrade],
          rates: { [selectedTrade]: Number(rate) },
          verified: false,
          verificationStatus: 'unverified',
        });
        useToastStore.getState().success('Worker login successful!');
        navigate('/worker');
      }
    } catch (err) {
      useToastStore.getState().error(err.message || 'Invalid OTP code. Please try again.');
    } finally {
      setIsVerifying(false);
    }
  };

  const handleResetData = () => {
    api.resetMockData();
    useToastStore.getState().info('Mock data reset to initial state!');
  };

  return (
    <div className="space-y-5 pt-1">
      {/* Brand Heading & Value Proposition */}
      <div className="text-center space-y-2">
        <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-brand-50 text-brand-700 text-[11px] font-extrabold">
          <ShieldCheck className="w-3.5 h-3.5" />
          <span>India's Hyperlocal Blue-Collar Platform</span>
        </div>
        <h1 className="text-2xl font-black text-slate-900 tracking-tight">RepairBuddy</h1>
        <p className="text-xs text-slate-600 max-w-sm mx-auto leading-relaxed">
          Book verified local plumbers, electricians, maids & technicians in 30 minutes at negotiated rates with zero platform fee.
        </p>

        {/* Value Proposition Badges */}
        <div className="flex flex-wrap items-center justify-center gap-1.5 pt-0.5">
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-emerald-50 text-emerald-700 text-[10px] font-bold">
            <Zap className="w-2.5 h-2.5" /> 30-Min Arrival
          </span>
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-blue-50 text-blue-700 text-[10px] font-bold">
            <ShieldCheck className="w-2.5 h-2.5" /> Verified Trades
          </span>
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-amber-50 text-amber-700 text-[10px] font-bold">
            <CheckCircle2 className="w-2.5 h-2.5" /> Direct Cash Settlement
          </span>
        </div>
      </div>

      {/* Strict Portal Tabs */}
      <div className="bg-slate-200/80 p-1.5 rounded-2xl grid grid-cols-2 gap-1.5">
        <button
          type="button"
          onClick={() => handleTabChange(ROLES.CUSTOMER)}
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
            {activePortal === ROLES.ADMIN
              ? 'Administrator Verification'
              : activePortal === ROLES.CUSTOMER
                ? 'Customer Verification'
                : 'Tradesman & Worker Sign In'}
          </h2>
          <p className="text-[11px] text-slate-500 mt-0.5">
            {activePortal === ROLES.ADMIN
              ? 'Sign in with an authorized phone number to access admin console'
              : activePortal === ROLES.CUSTOMER
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
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder={
                  activePortal === ROLES.ADMIN
                    ? 'Enter admin name'
                    : activePortal === ROLES.CUSTOMER
                      ? 'Enter your full name'
                      : 'Enter worker name'
                }
                className="w-full text-xs px-3.5 py-2.5 rounded-xl border border-slate-200 bg-slate-50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
            </div>

            <div>
              <label className="block text-[11px] font-bold text-slate-700 mb-1">Mobile Number</label>
              <div className="flex gap-2">
                <span className="px-3 py-2.5 rounded-xl bg-slate-100 border border-slate-200 text-xs font-bold text-slate-600">
                  +91
                </span>
                <input
                  type="tel"
                  required
                  maxLength="10"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  placeholder="10-digit phone number"
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
                    value={rate}
                    onChange={(e) => setRate(e.target.value)}
                    className="w-full text-xs px-3 py-2.5 rounded-xl border border-slate-200 bg-slate-50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-brand-500"
                  />
                </div>
              </div>
            )}

            {/* Firebase reCAPTCHA anchor */}
            <div id="recaptcha-container" className="flex justify-center my-1"></div>

            <button
              type="submit"
              disabled={isVerifying}
              className="w-full py-3.5 rounded-2xl bg-brand-600 hover:bg-brand-700 text-white font-extrabold text-xs shadow-md shadow-brand-500/20 active:scale-95 transition min-h-touch flex items-center justify-center gap-2 disabled:opacity-50"
            >
              <span>{isVerifying ? 'Sending...' : 'Send Verification Code (OTP)'}</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </form>
        ) : (
          /* Step 2: OTP Verification */
          <form onSubmit={handleVerifyOtp} className="space-y-4 animate-in fade-in">
            {simulatedCode ? (
              <div className="bg-blue-50 border border-blue-200 rounded-2xl p-3 text-xs text-blue-900 flex items-center justify-between">
                <div>
                  <p className="font-extrabold">Simulated OTP Sent to +91 {phone}</p>
                  <p className="text-[11px] text-blue-700 mt-0.5">
                    Enter code: <span className="font-black underline">{simulatedCode}</span>
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => setOtpInput(simulatedCode)}
                  className="px-2.5 py-1 rounded-lg bg-blue-600 text-white text-[11px] font-bold active:scale-95"
                >
                  Auto-fill
                </button>
              </div>
            ) : (
              <div className="bg-emerald-50 border border-emerald-200 rounded-2xl p-3 text-xs text-emerald-900">
                <p className="font-extrabold">SMS Code Sent to +91 {phone}</p>
                <p className="text-[11px] text-emerald-700 mt-0.5">
                  Enter the 6-digit code received via SMS to complete verification.
                </p>
              </div>
            )}

            <div>
              <label className="block text-[11px] font-bold text-slate-700 mb-1">
                Enter Verification OTP
              </label>
              <input
                type="text"
                required
                maxLength="6"
                value={otpInput}
                onChange={(e) => setOtpInput(e.target.value)}
                placeholder={simulatedCode ? '1234' : '123456'}
                className="w-full text-center text-xl font-black tracking-widest px-3 py-3 rounded-xl border border-slate-200 bg-slate-50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
            </div>

            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setOtpSent(false)}
                className="flex-1 py-3 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-bold"
              >
                Change Number
              </button>
              <button
                type="submit"
                disabled={isVerifying || otpInput.length < 4}
                className="flex-1 py-3 rounded-xl bg-brand-600 hover:bg-brand-700 text-white text-xs font-extrabold shadow-md shadow-brand-500/20 active:scale-95 transition"
              >
                {isVerifying ? 'Verifying...' : 'Verify & Sign In'}
              </button>
            </div>
          </form>
        )}

        {/* 1-Click Fast Testing Accounts */}
        {activePortal !== ROLES.ADMIN && (
          <div className="pt-3 border-t border-slate-100 space-y-2">
            <p className="text-[10px] font-extrabold uppercase tracking-wider text-slate-400">
              Fast Testing Accounts
            </p>
            {activePortal === ROLES.WORKER ? (
              <div className="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  onClick={() => {
                    loginAsWorker({
                      uid: 'worker_plumber_unverified',
                      name: 'Kamlesh Verma',
                      phone: '+91 91101 00005',
                      verified: false,
                      verificationStatus: 'unverified',
                      skills: ['plumber'],
                      rates: { plumber: 300 },
                    });
                    useToastStore.getState().info('Logged in as Unverified Worker');
                    navigate('/worker');
                  }}
                  className="p-2.5 rounded-xl border border-amber-200 bg-amber-50 hover:bg-amber-100 text-left transition"
                >
                  <div className="flex items-center gap-1.5 text-amber-900 font-extrabold text-[11px]">
                    <span className="w-2 h-2 rounded-full bg-amber-500" />
                    <span>Unverified Worker</span>
                  </div>
                  <p className="text-[10px] text-amber-700 mt-0.5">Test Document Upload</p>
                </button>

                <button
                  type="button"
                  onClick={() => {
                    loginAsWorker({
                      uid: 'worker_plumber_1',
                      name: 'Ramesh Kumar',
                      phone: '+91 91101 00001',
                      verified: true,
                      verificationStatus: 'approved',
                      skills: ['plumber'],
                      rates: { plumber: 350 },
                    });
                    useToastStore.getState().success('Logged in as Verified Worker');
                    navigate('/worker');
                  }}
                  className="p-2.5 rounded-xl border border-emerald-200 bg-emerald-50 hover:bg-emerald-100 text-left transition"
                >
                  <div className="flex items-center gap-1.5 text-emerald-900 font-extrabold text-[11px]">
                    <span className="w-2 h-2 rounded-full bg-emerald-500" />
                    <span>Verified Worker</span>
                  </div>
                  <p className="text-[10px] text-emerald-700 mt-0.5">Ramesh (Gold Badge)</p>
                </button>
              </div>
            ) : (
              <button
                type="button"
                onClick={() => {
                  loginAsCustomer({
                    uid: 'cust_priya',
                    name: 'Priya Sharma',
                    phone: '+91 98200 11001',
                  });
                  useToastStore.getState().success('Logged in as Priya Sharma');
                  navigate('/');
                }}
                className="w-full p-2.5 rounded-xl border border-blue-200 bg-blue-50 hover:bg-blue-100 text-left transition flex items-center justify-between"
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
        )}
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
            onClick={() => handleTabChange(ROLES.ADMIN)}
            className={`text-[11px] font-medium transition py-1 ${
              activePortal === ROLES.ADMIN
                ? 'text-purple-700 font-bold underline'
                : 'text-slate-400 hover:text-purple-600 underline'
            }`}
          >
            Administrator Console
          </button>
        </div>
      </div>
    </div>
  );
}
