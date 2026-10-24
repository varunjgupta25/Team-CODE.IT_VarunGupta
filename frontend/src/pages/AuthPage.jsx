import React, { useState } from 'react';
import { useAuthStore } from '../store/authStore';
import { ROLES, CATEGORIES } from '../types';
import { INITIAL_CUSTOMER, INITIAL_WORKER, SEED_WORKERS } from '../api/mockData';
import {
  User,
  Briefcase,
  Phone,
  ShieldCheck,
  CheckCircle2,
  Lock,
  ArrowRight,
  Sparkles,
  KeyRound,
  RotateCcw,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useToastStore } from '../store/toastStore';
import { api } from '../api';

export function AuthPage() {
  const { loginAsCustomer, loginAsWorker, sendOtp } = useAuthStore();
  const navigate = useNavigate();

  // Active portal tab: 'customer' or 'worker'
  const [activePortal, setActivePortal] = useState(ROLES.CUSTOMER);

  // Form states
  const [phone, setPhone] = useState('9876543210');
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
    if (portal === ROLES.CUSTOMER) {
      setPhone('9876543210');
      setName('Priya Sharma');
    } else {
      setPhone('9820112345');
      setName('Ramesh Kanojia');
    }
  };

  // 1-Click Demo Profiles for instant testing
  const handleQuickCustomer = () => {
    loginAsCustomer(INITIAL_CUSTOMER);
    useToastStore.getState().success(`Logged in as Customer (${INITIAL_CUSTOMER.name})`);
    navigate('/');
  };

  const handleQuickWorker = (seed = INITIAL_WORKER) => {
    loginAsWorker(seed);
    useToastStore.getState().success(`Logged in as Worker (${seed.name})`);
    navigate('/worker');
  };

  // Step 1: Send OTP
  const handleRequestOtp = (e) => {
    e.preventDefault();
    if (!phone || phone.length < 10) {
      useToastStore.getState().error('Please enter a valid 10-digit mobile number');
      return;
    }

    const code = sendOtp(phone);
    setSimulatedCode(code);
    setOtpSent(true);
    useToastStore.getState().info(`SMS Sent! Verification OTP is: ${code}`);
  };

  // Step 2: Verify OTP & Sign In
  const handleVerifyOtp = (e) => {
    e.preventDefault();
    if (otpInput !== simulatedCode && otpInput !== '1234') {
      useToastStore.getState().error('Invalid OTP. Use simulated OTP: 1234');
      return;
    }

    setIsVerifying(true);
    setTimeout(() => {
      setIsVerifying(false);
      if (activePortal === ROLES.CUSTOMER) {
        loginAsCustomer({
          name: name.trim() || 'Priya Sharma',
          phone: `+91 ${phone}`,
        });
        useToastStore.getState().success('Customer login successful!');
        navigate('/');
      } else {
        loginAsWorker({
          name: name.trim() || 'Ramesh Kanojia',
          phone: `+91 ${phone}`,
          skills: [selectedTrade],
          rates: { [selectedTrade]: Number(rate) },
        });
        useToastStore.getState().success('Worker login successful!');
        navigate('/worker');
      }
    }, 400);
  };

  const handleResetData = () => {
    api.resetMockData();
    useToastStore.getState().info('Mock data reset to initial state!');
  };

  return (
    <div className="space-y-5 pt-1">
      {/* Brand Heading */}
      <div className="text-center space-y-1">
        <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-brand-50 text-brand-700 text-[11px] font-extrabold mb-1">
          <ShieldCheck className="w-3.5 h-3.5" />
          <span>Secure Hyperlocal Authentication</span>
        </div>
        <h1 className="text-2xl font-black text-slate-900 tracking-tight">Sign In to RepairBuddy</h1>
        <p className="text-xs text-slate-500">
          Separate, dedicated login system for Customers and Service Workers
        </p>
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
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder={activePortal === ROLES.CUSTOMER ? 'Priya Sharma' : 'Ramesh Kanojia'}
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

            <button
              type="submit"
              className="w-full py-3.5 rounded-2xl bg-brand-600 hover:bg-brand-700 text-white font-extrabold text-xs shadow-md shadow-brand-500/20 active:scale-95 transition min-h-touch flex items-center justify-center gap-2"
            >
              <span>Send Verification Code (OTP)</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </form>
        ) : (
          /* Step 2: OTP Verification */
          <form onSubmit={handleVerifyOtp} className="space-y-4 animate-in fade-in">
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

            <div>
              <label className="block text-[11px] font-bold text-slate-700 mb-1">
                Enter 4-Digit OTP
              </label>
              <input
                type="text"
                required
                maxLength="4"
                value={otpInput}
                onChange={(e) => setOtpInput(e.target.value)}
                placeholder="1234"
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
      </div>

      {/* 1-Click Fast Track Testing */}
      <div className="space-y-2.5">
        <p className="text-xs font-bold text-slate-500 uppercase tracking-wider text-center">
          Or Quick Test Account
        </p>

        {activePortal === ROLES.CUSTOMER ? (
          <button
            type="button"
            onClick={handleQuickCustomer}
            className="w-full p-3.5 rounded-2xl border-2 border-brand-200 bg-white hover:bg-brand-50/50 text-left transition-all shadow-sm flex items-center justify-between group active:scale-95"
          >
            <div className="flex items-center gap-3">
              <img
                src={INITIAL_CUSTOMER.avatarUrl || 'https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=100&auto=format&fit=crop&q=80'}
                alt="Priya"
                className="w-10 h-10 rounded-full object-cover border border-brand-300"
              />
              <div>
                <p className="font-black text-xs text-slate-900 group-hover:text-brand-600">
                  Quick Sign-In: Priya Sharma
                </p>
                <p className="text-[11px] text-slate-500">Customer • Mira Road East</p>
              </div>
            </div>
            <span className="text-xs font-black text-brand-600">Enter &rarr;</span>
          </button>
        ) : (
          <button
            type="button"
            onClick={() => handleQuickWorker(INITIAL_WORKER)}
            className="w-full p-3.5 rounded-2xl border-2 border-amber-200 bg-white hover:bg-amber-50/50 text-left transition-all shadow-sm flex items-center justify-between group active:scale-95"
          >
            <div className="flex items-center gap-3">
              <img
                src={INITIAL_WORKER.avatarUrl}
                alt="Ramesh"
                className="w-10 h-10 rounded-full object-cover border border-amber-300"
              />
              <div>
                <p className="font-black text-xs text-slate-900 group-hover:text-amber-700">
                  Quick Sign-In: Ramesh Kanojia
                </p>
                <p className="text-[11px] text-slate-500">Verified Plumber • 4.8★ Gold</p>
              </div>
            </div>
            <span className="text-xs font-black text-amber-700">Enter &rarr;</span>
          </button>
        )}
      </div>

      {/* Reset Mock DB */}
      <div className="text-center pt-2">
        <button
          onClick={handleResetData}
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-400 hover:text-slate-700 transition p-2"
        >
          <RotateCcw className="w-3.5 h-3.5" />
          <span>Reset All Mock Data to Default</span>
        </button>
      </div>
    </div>
  );
}
