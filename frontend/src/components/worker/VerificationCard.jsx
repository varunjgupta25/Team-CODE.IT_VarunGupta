import React, { useState, useEffect } from 'react';
import { useAuthStore } from '../../store/authStore';
import { api } from '../../api';
import { useToastStore } from '../../store/toastStore';
import { TrustBadge } from '../common/TrustBadge';
import { computeTrust } from '../../lib/utils';
import {
  ShieldCheck,
  Clock,
  FileText,
  Upload,
  CheckCircle2,
  AlertCircle,
  X,
  Sparkles,
} from 'lucide-react';

const DOC_TYPES = [
  { id: 'aadhaar', label: 'Aadhaar Card (12 digits)', placeholder: '1234 5678 9012' },
  { id: 'pan', label: 'PAN Card (10 chars)', placeholder: 'ABCDE1234F' },
  { id: 'voter_id', label: 'Voter ID (10 chars)', placeholder: 'ABC1234567' },
];

export function VerificationCard() {
  const { user, updateUser, refreshWorkerProfile } = useAuthStore();
  const [docType, setDocType] = useState('aadhaar');
  const [docNumber, setDocNumber] = useState('');
  const [localPhotoPreview, setLocalPhotoPreview] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [validationError, setValidationError] = useState('');

  // Sync latest status from backend on mount
  useEffect(() => {
    if (refreshWorkerProfile) {
      refreshWorkerProfile();
    }
  }, [refreshWorkerProfile]);

  const isVerified = Boolean(user?.verified);
  const isPending = user?.verificationStatus === 'pending';
  const trust = user ? computeTrust(user) : { score: 60, tier: 'Bronze' };

  // Local document photo preview only - never uploaded or sent
  const handlePhotoSelect = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      if (file.size > 5 * 1024 * 1024) {
        useToastStore.getState().error('Image must be under 5MB');
        return;
      }
      const previewUrl = URL.createObjectURL(file);
      setLocalPhotoPreview(previewUrl);
    }
  };

  const validateDocNumber = (type, val) => {
    const clean = val.replace(/[\s-]/g, '').toUpperCase();
    if (!clean) return 'Document number is required';

    if (type === 'aadhaar') {
      if (!/^\d{12}$/.test(clean)) return 'Aadhaar must be exactly 12 numeric digits';
    } else if (type === 'pan') {
      if (!/^[A-Z]{5}[0-9]{4}[A-Z]$/.test(clean)) return 'PAN must follow format: ABCDE1234F (5 letters, 4 digits, 1 letter)';
    } else if (type === 'voter_id') {
      if (!/^[A-Z0-9]{10}$/.test(clean)) return 'Voter ID must be 10 alphanumeric characters';
    }
    return '';
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setValidationError('');

    const err = validateDocNumber(docType, docNumber);
    if (err) {
      setValidationError(err);
      return;
    }

    const cleanNum = docNumber.replace(/[\s-]/g, '').toUpperCase();
    setIsSubmitting(true);

    try {
      const res = await api.verifyWorker({
        documentType: docType,
        documentNumber: cleanNum,
      });

      updateUser({
        verificationStatus: 'pending',
      });

      useToastStore.getState().success(res?.message || 'Verification request submitted! Awaiting administrator approval.');
      setDocNumber('');
      setLocalPhotoPreview(null);
    } catch (error) {
      useToastStore.getState().error(error.message || 'Failed to submit verification');
    } finally {
      setIsSubmitting(false);
    }
  };

  // State 1: Verified
  if (isVerified) {
    return (
      <div className="bg-gradient-to-br from-emerald-500/10 via-emerald-50 to-white rounded-3xl p-5 border border-emerald-200 shadow-sm space-y-3">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className="w-11 h-11 rounded-2xl bg-emerald-600 text-white flex items-center justify-center shadow-md shadow-emerald-500/20">
              <CheckCircle2 className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center gap-1.5">
                <span className="font-extrabold text-sm text-slate-900">ID Verification Complete</span>
                <span className="px-1.5 py-0.5 rounded bg-emerald-100 text-emerald-800 text-[10px] font-black uppercase">
                  Verified
                </span>
              </div>
              <p className="text-[11px] text-slate-500 mt-0.5">
                Govt ID verified. Your profile receives priority in customer matches.
              </p>
            </div>
          </div>
        </div>

        <div className="pt-2 border-t border-emerald-100 flex items-center justify-between text-xs">
          <span className="text-slate-600 font-medium text-[11px]">Active Trust Status:</span>
          <TrustBadge score={trust.score} tier={trust.tier} />
        </div>
      </div>
    );
  }

  // State 2: Pending review
  if (isPending) {
    return (
      <div className="bg-gradient-to-br from-amber-500/10 via-amber-50 to-white rounded-3xl p-5 border border-amber-200 shadow-sm space-y-3">
        <div className="flex items-start gap-3">
          <div className="w-11 h-11 rounded-2xl bg-amber-500 text-white flex items-center justify-center shadow-md shadow-amber-500/20 shrink-0">
            <Clock className="w-6 h-6 animate-spin-slow" />
          </div>
          <div>
            <div className="flex items-center gap-1.5">
              <span className="font-extrabold text-sm text-slate-900">Verification Under Review</span>
              <span className="px-2 py-0.5 rounded bg-amber-100 text-amber-800 text-[10px] font-black uppercase">
                Pending
              </span>
            </div>
            <p className="text-[11px] text-slate-600 mt-1 leading-relaxed">
              Your government ID document has been submitted. Our compliance team is verifying your details. You will appear in customer job searches as soon as approved!
            </p>
          </div>
        </div>

        <div className="pt-2 border-t border-amber-100 flex items-center justify-between text-[11px] text-amber-900 font-semibold bg-amber-100/60 p-2.5 rounded-xl">
          <span className="flex items-center gap-1">
            <Sparkles className="w-3.5 h-3.5 text-amber-600" />
            Expected approval: ~15 mins
          </span>
          <button
            onClick={() => refreshWorkerProfile && refreshWorkerProfile()}
            className="text-[10px] text-amber-700 underline font-bold"
          >
            Check Status
          </button>
        </div>
      </div>
    );
  }

  // State 3: Unverified - Form to Get Verified
  const selectedDocObj = DOC_TYPES.find((d) => d.id === docType) || DOC_TYPES[0];

  return (
    <div className="bg-white rounded-3xl p-5 border-2 border-brand-200 shadow-md space-y-4">
      <div className="flex items-start gap-3">
        <div className="w-11 h-11 rounded-2xl bg-brand-600 text-white flex items-center justify-center shadow-md shadow-brand-500/25 shrink-0">
          <ShieldCheck className="w-6 h-6" />
        </div>
        <div>
          <div className="flex items-center gap-1.5">
            <h2 className="font-extrabold text-sm text-slate-900">Get Verified &amp; Start Earning</h2>
            <span className="px-1.5 py-0.5 rounded bg-red-100 text-red-800 text-[10px] font-bold">
              Required
            </span>
          </div>
          <p className="text-[11px] text-slate-500 mt-0.5">
            RepairBuddy only matches 100% verified providers to protect customers and workers.
          </p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-3 pt-1">
        {/* Document Type Dropdown */}
        <div className="space-y-1">
          <label className="block text-[11px] font-bold text-slate-700">Select Document Type</label>
          <div className="grid grid-cols-3 gap-1.5">
            {DOC_TYPES.map((dt) => (
              <button
                key={dt.id}
                type="button"
                onClick={() => {
                  setDocType(dt.id);
                  setValidationError('');
                }}
                className={`py-2 px-2 rounded-xl text-[11px] font-bold border text-center transition-all ${
                  docType === dt.id
                    ? 'bg-brand-600 text-white border-brand-600 shadow-sm'
                    : 'bg-slate-50 text-slate-700 border-slate-200 hover:bg-slate-100'
                }`}
              >
                {dt.id === 'aadhaar' ? 'Aadhaar' : dt.id === 'pan' ? 'PAN Card' : 'Voter ID'}
              </button>
            ))}
          </div>
        </div>

        {/* Document Number Input */}
        <div className="space-y-1">
          <label className="block text-[11px] font-bold text-slate-700">
            {selectedDocObj.label}
          </label>
          <div className="relative">
            <input
              type="text"
              required
              value={docNumber}
              onChange={(e) => {
                setDocNumber(e.target.value);
                setValidationError('');
              }}
              placeholder={selectedDocObj.placeholder}
              className="w-full text-xs p-2.5 rounded-xl border border-slate-200 bg-slate-50 focus:bg-white focus:ring-2 focus:ring-brand-500 focus:outline-none uppercase font-mono tracking-wider"
            />
            <FileText className="w-4 h-4 text-slate-400 absolute right-3 top-2.5" />
          </div>
          {validationError && (
            <p className="text-[10px] text-red-600 font-semibold flex items-center gap-1">
              <AlertCircle className="w-3 h-3" />
              {validationError}
            </p>
          )}
        </div>

        {/* Optional Local Photo Preview (Never transmitted) */}
        <div className="space-y-1">
          <div className="flex items-center justify-between">
            <label className="text-[11px] font-bold text-slate-700">
              Document Photo (Optional Preview)
            </label>
            <span className="text-[10px] text-slate-400">Local-only</span>
          </div>

          {localPhotoPreview ? (
            <div className="relative rounded-2xl overflow-hidden border border-slate-200 w-full h-28 bg-slate-100">
              <img
                src={localPhotoPreview}
                alt="Document preview"
                className="w-full h-full object-cover"
              />
              <button
                type="button"
                onClick={() => setLocalPhotoPreview(null)}
                className="absolute top-2 right-2 p-1 rounded-full bg-black/60 text-white hover:bg-black"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
          ) : (
            <label className="flex items-center justify-center gap-2 p-3 rounded-2xl border-2 border-dashed border-slate-200 hover:border-brand-400 bg-slate-50/50 cursor-pointer text-slate-600 transition">
              <Upload className="w-4 h-4 text-brand-600" />
              <span className="text-xs font-medium">Select photo for inspection</span>
              <input
                type="file"
                accept="image/*"
                onChange={handlePhotoSelect}
                className="hidden"
              />
            </label>
          )}
        </div>

        {/* Submit Verification Request */}
        <button
          type="submit"
          disabled={isSubmitting || !docNumber.trim()}
          className="w-full py-3 rounded-xl bg-brand-600 hover:bg-brand-700 disabled:opacity-50 text-white font-extrabold text-xs shadow-md shadow-brand-500/25 active:scale-95 transition-all flex items-center justify-center gap-1.5"
        >
          <ShieldCheck className="w-4 h-4" />
          <span>{isSubmitting ? 'Submitting...' : 'Submit ID for Verification'}</span>
        </button>
      </form>
    </div>
  );
}
