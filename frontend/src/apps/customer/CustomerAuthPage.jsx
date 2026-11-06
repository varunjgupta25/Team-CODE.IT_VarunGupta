import React, { useState } from 'react';
import { useAuthStore } from '../../store/authStore';
import {
  ShieldCheck,
  ArrowRight,
  RotateCcw,
  UserCheck,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useToastStore } from '../../store/toastStore';
import { api } from '../../api';

export function CustomerAuthPage() {
  const { loginAsCustomer, requestPhoneOtp, confirmPhoneOtp } = useAuthStore();
  const navigate = useNavigate();

  // Form states
  const [phone, setPhone] = useState('');
  const [name, setName] = useState('');
  
  // OTP flow states
  const [otpSent, setOtpSent] = useState(false);
  const [otpInput, setOtpInput] = useState('');
  const [simulatedCode, setSimulatedCode] = useState('');
  const [isVerifying, setIsVerifying] = useState(false);

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

      await loginAsCustomer({
        uid: resolvedUser?.uid,
        name: name.trim() || 'Customer',
        phone: formattedPhone,
      });
      useToastStore.getState().success('Customer login successful!');
      navigate('/');
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
      {/* Brand Heading */}
      <div className="text-center space-y-1">
        <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-brand-50 text-brand-700 text-[11px] font-extrabold mb-1">
          <ShieldCheck className="w-3.5 h-3.5" />
          <span>Customer Authentication</span>
        </div>
        <h1 className="text-2xl font-black text-slate-900 tracking-tight">Sign In to RepairBuddy</h1>
        <p className="text-xs text-slate-500">
          Book verified hyperlocal plumbers, electricians, and technicians in 30 minutes
        </p>
      </div>

      {/* Main Authentication Box */}
      <div className="bg-white rounded-3xl p-5 border border-slate-200 shadow-sm space-y-4">
        <div className="border-b border-slate-100 pb-3">
          <h2 className="font-extrabold text-sm text-slate-900">
            Customer Mobile Sign In
          </h2>
          <p className="text-[11px] text-slate-500 mt-0.5">
            Sign in to request, negotiate, and book 30-min doorstep home services
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
                placeholder="Enter your full name"
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

        {/* 1-Click Fast Testing Account for Customer */}
        <div className="pt-3 border-t border-slate-100 space-y-2">
          <p className="text-[10px] font-extrabold uppercase tracking-wider text-slate-400">
            Fast Testing Account
          </p>
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
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-lg bg-blue-600 text-white flex items-center justify-center">
                <UserCheck className="w-4 h-4" />
              </div>
              <div>
                <span className="font-extrabold text-blue-900 text-xs">Priya Sharma</span>
                <p className="text-[10px] text-blue-700">Mira Road East • Customer</p>
              </div>
            </div>
            <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-blue-200 text-blue-800">
              1-Click Sign In
            </span>
          </button>
        </div>
      </div>

      {/* Reset Mock DB */}
      <div className="text-center pt-2">
        <button
          onClick={handleResetData}
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-400 hover:text-slate-700 transition p-1.5"
        >
          <RotateCcw className="w-3.5 h-3.5" />
          <span>Reset All Mock Data to Default</span>
        </button>
      </div>
    </div>
  );
}

