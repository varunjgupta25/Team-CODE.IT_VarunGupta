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
  Camera,
  AlertTriangle,
  RotateCcw,
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
  const [idFile, setIdFile] = useState(null);
  const [idPreview, setIdPreview] = useState(null);
  const [selfieFile, setSelfieFile] = useState(null);
  const [selfiePreview, setSelfiePreview] = useState(null);
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
  const isRejected = user?.verificationStatus === 'rejected';
  const trust = user ? computeTrust(user) : { score: 60, tier: 'Bronze' };

  const handleIdFileSelect = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      if (file.size > 5 * 1024 * 1024) {
        useToastStore.getState().error('ID Document image must be under 5MB');
        return;
      }
      setIdFile(file);
      setIdPreview(URL.createObjectURL(file));
      setValidationError('');
    }
  };

  const handleSelfieSelect = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      if (file.size > 5 * 1024 * 1024) {
        useToastStore.getState().error('Selfie photo must be under 5MB');
        return;
      }
      setSelfieFile(file);
      setSelfiePreview(URL.createObjectURL(file));
      setValidationError('');
    }
  };

  const validateDocNumber = (type, val) => {
    const clean = val.replace(/[\s-]/g, '').toUpperCase();
    if (!clean) return 'Document number is required';

    if (type === 'aadhaar') {
      if (!/^\d{12}$/.test(clean)) return 'Aadhaar must be exactly 12 numeric digits';
    } else if (type === 'pan') {
      if (!/^[A-Z]{5}[0-9]{4}[A-Z]$/.test(clean)) return 'PAN must follow format: ABCDE1234F';
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

    if (!idFile) {
      setValidationError('Please upload a photo of your ID document');
      return;
    }

    if (!selfieFile) {
      setValidationError('Please upload a clear live selfie photo');
      return;
    }

    const cleanNum = docNumber.replace(/[\s-]/g, '').toUpperCase();
    setIsSubmitting(true);

    try {
      const formData = new FormData();
      formData.append('documentType', docType);
      formData.append('documentNumber', cleanNum);
      formData.append('id_document', idFile);
      formData.append('selfie', selfieFile);

      const res = await api.uploadWorkerVerification(formData);

      updateUser({
        verificationStatus: 'pending',
        documentType: docType,
        last4: cleanNum.slice(-4),
        rejectionReason: null,
      });

      useToastStore.getState().success(res?.message || 'Verification submitted for manual review!');
      setDocNumber('');
      setIdFile(null);
      setIdPreview(null);
      setSelfieFile(null);
      setSelfiePreview(null);
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
              Your government ID document and selfie have been securely received. Our compliance team is verifying your details. You will appear in customer searches as soon as approved!
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

  // State 3: Rejected / Unverified - Form to Upload & Verify
  const selectedDocObj = DOC_TYPES.find((d) => d.id === docType) || DOC_TYPES[0];

  return (
    <div className="bg-white rounded-3xl p-5 border-2 border-brand-200 shadow-md space-y-4">
      {/* Rejection Alert if rejected */}
      {isRejected && (
        <div className="bg-red-50 border border-red-200 rounded-2xl p-4 space-y-2">
          <div className="flex items-center gap-2 text-red-800 font-extrabold text-xs">
            <AlertTriangle className="w-4 h-4 text-red-600" />
            <span>Verification Rejected</span>
          </div>
          <p className="text-xs text-red-700 leading-relaxed">
            <span className="font-semibold">Reason:</span> {user?.rejectionReason || 'Document could not be verified. Please re-upload clearer photos.'}
          </p>
          <p className="text-[10px] text-red-500">
            Please re-upload a clear, readable ID document and live selfie below.
          </p>
        </div>
      )}

      <div className="flex items-start gap-3">
        <div className="w-11 h-11 rounded-2xl bg-brand-600 text-white flex items-center justify-center shadow-md shadow-brand-500/25 shrink-0">
          <ShieldCheck className="w-6 h-6" />
        </div>
        <div>
          <div className="flex items-center gap-1.5">
            <h2 className="font-extrabold text-sm text-slate-900">
              {isRejected ? 'Resubmit Verification' : 'Get Verified & Start Earning'}
            </h2>
            <span className="px-1.5 py-0.5 rounded bg-red-100 text-red-800 text-[10px] font-bold">
              Required
            </span>
          </div>
          <p className="text-[11px] text-slate-500 mt-0.5">
            Upload your Govt ID &amp; live selfie. Images are encrypted and private.
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
        </div>

        {/* Two-Column Uploads: ID Document + Selfie */}
        <div className="grid grid-cols-2 gap-2.5 pt-1">
          {/* 1. ID Photo */}
          <div className="space-y-1">
            <label className="block text-[10px] font-bold text-slate-700">
              1. ID Card Photo *
            </label>
            {idPreview ? (
              <div className="relative rounded-2xl overflow-hidden border border-slate-200 h-24 bg-slate-100">
                <img src={idPreview} alt="ID preview" className="w-full h-full object-cover" />
                <button
                  type="button"
                  onClick={() => {
                    setIdFile(null);
                    setIdPreview(null);
                  }}
                  className="absolute top-1 right-1 p-1 rounded-full bg-black/60 text-white hover:bg-black"
                >
                  <X className="w-3 h-3" />
                </button>
              </div>
            ) : (
              <label className="flex flex-col items-center justify-center p-3 rounded-2xl border-2 border-dashed border-slate-200 hover:border-brand-400 bg-slate-50/50 cursor-pointer text-slate-600 transition h-24 text-center">
                <Upload className="w-4 h-4 text-brand-600 mb-1" />
                <span className="text-[10px] font-bold">Front of ID</span>
                <span className="text-[8px] text-slate-400">JPG/PNG &lt; 5MB</span>
                <input
                  type="file"
                  accept="image/jpeg,image/png"
                  onChange={handleIdFileSelect}
                  className="hidden"
                />
              </label>
            )}
          </div>

          {/* 2. Selfie */}
          <div className="space-y-1">
            <label className="block text-[10px] font-bold text-slate-700">
              2. Live Face Selfie *
            </label>
            {selfiePreview ? (
              <div className="relative rounded-2xl overflow-hidden border border-slate-200 h-24 bg-slate-100">
                <img src={selfiePreview} alt="Selfie preview" className="w-full h-full object-cover" />
                <button
                  type="button"
                  onClick={() => {
                    setSelfieFile(null);
                    setSelfiePreview(null);
                  }}
                  className="absolute top-1 right-1 p-1 rounded-full bg-black/60 text-white hover:bg-black"
                >
                  <X className="w-3 h-3" />
                </button>
              </div>
            ) : (
              <label className="flex flex-col items-center justify-center p-3 rounded-2xl border-2 border-dashed border-slate-200 hover:border-brand-400 bg-slate-50/50 cursor-pointer text-slate-600 transition h-24 text-center">
                <Camera className="w-4 h-4 text-brand-600 mb-1" />
                <span className="text-[10px] font-bold">Take Selfie</span>
                <span className="text-[8px] text-slate-400">Clear face photo</span>
                <input
                  type="file"
                  accept="image/jpeg,image/png"
                  capture="user"
                  onChange={handleSelfieSelect}
                  className="hidden"
                />
              </label>
            )}
          </div>
        </div>

        {validationError && (
          <p className="text-[10px] text-red-600 font-semibold flex items-center gap-1">
            <AlertCircle className="w-3 h-3" />
            {validationError}
          </p>
        )}

        {/* Privacy Note */}
        <p className="text-[10px] text-slate-400 leading-tight">
          🔒 DPDP compliant: Images are securely stored in private storage and permanently purged once verified.
        </p>

        {/* Submit Verification Request */}
        <button
          type="submit"
          disabled={isSubmitting || !docNumber.trim() || !idFile || !selfieFile}
          className="w-full py-3 rounded-xl bg-brand-600 hover:bg-brand-700 disabled:opacity-50 text-white font-extrabold text-xs shadow-md shadow-brand-500/25 active:scale-95 transition-all flex items-center justify-center gap-1.5"
        >
          {isRejected ? <RotateCcw className="w-4 h-4" /> : <ShieldCheck className="w-4 h-4" />}
          <span>{isSubmitting ? 'Uploading & Encrypting...' : isRejected ? 'Resubmit Verification' : 'Upload & Submit for Verification'}</span>
        </button>
      </form>
    </div>
  );
}
