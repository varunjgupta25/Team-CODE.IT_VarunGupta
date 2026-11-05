import React, { useState, useEffect } from 'react';
import { useAuthStore } from '../store/authStore';
import { ROLES } from '../types';
import { computeTrust, formatCurrency } from '../lib/utils';
import { TrustBadge } from '../components/common/TrustBadge';
import { VerificationCard } from '../components/worker/VerificationCard';
import { api } from '../api';
import {
  Phone,
  MapPin,
  ShieldCheck,
  LogOut,
  AlertOctagon,
  CheckCircle2,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useToastStore } from '../store/toastStore';

export function ProfilePage() {
  const { user, role, logout } = useAuthStore();
  const navigate = useNavigate();

  const [emergencyContact, setEmergencyContact] = useState(null);
  const [isEditingContact, setIsEditingContact] = useState(false);
  const [contactName, setContactName] = useState('');
  const [contactPhone, setContactPhone] = useState('');
  const [isSavingContact, setIsSavingContact] = useState(false);

  useEffect(() => {
    api.getEmergencyContact().then((c) => {
      if (c) {
        setEmergencyContact(c);
        setContactName(c.name || '');
        setContactPhone(c.phone || '');
      }
    }).catch(() => {
      setEmergencyContact(null);
    });
  }, []);

  if (!user) {
    navigate('/login');
    return null;
  }

  const isCustomer = role === ROLES.CUSTOMER;
  const trust = role === ROLES.WORKER ? computeTrust(user) : null;

  const handleSaveContact = async (e) => {
    e.preventDefault();
    if (!contactName.trim() || !contactPhone.trim()) return;

    setIsSavingContact(true);
    try {
      const res = await api.setEmergencyContact({
        name: contactName.trim(),
        phone: contactPhone.trim(),
      });
      const saved = res?.emergencyContact || { name: contactName.trim(), phone: contactPhone.trim() };
      setEmergencyContact(saved);
      setIsEditingContact(false);
      useToastStore.getState().success('Emergency contact saved successfully!');
    } catch (err) {
      useToastStore.getState().error(err.message || 'Failed to save contact. Please enter valid +91 10-digit number.');
    } finally {
      setIsSavingContact(false);
    }
  };

  const handleLogout = () => {
    logout();
    useToastStore.getState().info('You have logged out.');
    navigate('/login');
  };

  return (
    <div className="space-y-4 pt-1">
      <div>
        <h1 className="text-xl font-black text-slate-900 tracking-tight">Account Profile</h1>
        <p className="text-xs text-slate-500">Your registered details on RepairBuddy</p>
      </div>

      {/* Profile Card */}
      <div className="bg-white rounded-3xl p-5 border border-slate-200 shadow-sm space-y-4">
        <div className="flex items-center gap-3.5">
          <img
            src={
              user.avatarUrl ||
              'https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=150&auto=format&fit=crop&q=80'
            }
            alt={user.name}
            className="w-16 h-16 rounded-2xl object-cover border-2 border-brand-500 shadow-sm"
          />
          <div>
            <div className="flex items-center gap-1.5 flex-wrap">
              <h2 className="text-base font-extrabold text-slate-900">{user.name}</h2>
              <span
                className={`text-[10px] font-black px-2 py-0.5 rounded uppercase ${
                  isCustomer ? 'bg-blue-100 text-blue-800' : 'bg-amber-100 text-amber-800'
                }`}
              >
                {role}
              </span>
            </div>
            <p className="text-xs text-slate-500 mt-0.5 flex items-center gap-1">
              <Phone className="w-3 h-3 text-slate-400" />
              <span>{user.phone}</span>
            </p>
            {trust && (
              <div className="mt-1">
                <TrustBadge score={trust.score} tier={trust.tier} />
              </div>
            )}
          </div>
        </div>

        {/* Role Specific Details */}
        <div className="pt-3 border-t border-slate-100 space-y-2 text-xs">
          {isCustomer ? (
            <div className="flex items-start gap-2 bg-slate-50 p-3 rounded-2xl border border-slate-100">
              <MapPin className="w-4 h-4 text-brand-600 shrink-0 mt-0.5" />
              <div>
                <span className="font-bold text-slate-900 block">Default Service Address</span>
                <span className="text-slate-600 text-[11px]">{user.location?.address}</span>
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-2 text-center">
              <div className="p-3 bg-slate-50 rounded-2xl border border-slate-100">
                <span className="text-[10px] text-slate-500 block">Primary Trade</span>
                <span className="font-black text-slate-900 capitalize">
                  {user.skills?.join(', ') || 'Plumber'}
                </span>
              </div>
              <div className="p-3 bg-slate-50 rounded-2xl border border-slate-100">
                <span className="text-[10px] text-slate-500 block">Base Rate</span>
                <span className="font-black text-brand-700">
                  {formatCurrency(user.rates?.[user.skills?.[0]] || 350)}
                </span>
              </div>
            </div>
          )}
        </div>

        {/* Emergency SOS Contact Section */}
        <div className="bg-red-50/70 border border-red-200 rounded-2xl p-4 space-y-2 text-xs">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <AlertOctagon className="w-4 h-4 text-red-600" />
              <span className="font-extrabold text-slate-900">Emergency SOS Contact</span>
            </div>
            {!isEditingContact && (
              <button
                onClick={() => setIsEditingContact(true)}
                className="text-[11px] text-red-700 font-bold underline"
              >
                {emergencyContact ? 'Edit' : '+ Add Contact'}
              </button>
            )}
          </div>

          {emergencyContact && !isEditingContact ? (
            <div className="flex items-center justify-between pt-1">
              <div>
                <span className="font-bold text-slate-800 text-xs block">{emergencyContact.name}</span>
                <span className="text-slate-500 font-mono text-[11px]">{emergencyContact.phone}</span>
              </div>
              <span className="px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 text-[10px] font-bold flex items-center gap-1">
                <CheckCircle2 className="w-3 h-3" /> Active
              </span>
            </div>
          ) : !isEditingContact ? (
            <p className="text-[11px] text-slate-600">
              No emergency contact set. Set an emergency contact now so they receive SMS with live GPS in an emergency.
            </p>
          ) : null}

          {isEditingContact && (
            <form onSubmit={handleSaveContact} className="space-y-2 pt-2 border-t border-red-100">
              <input
                type="text"
                required
                placeholder="Contact Name (e.g. Papa / Spouse)"
                value={contactName}
                onChange={(e) => setContactName(e.target.value)}
                className="w-full text-xs p-2 rounded-xl border border-slate-200 bg-white"
              />
              <input
                type="tel"
                required
                placeholder="10-digit Mobile (+91 format)"
                value={contactPhone}
                onChange={(e) => setContactPhone(e.target.value)}
                className="w-full text-xs p-2 rounded-xl border border-slate-200 bg-white"
              />
              <div className="flex items-center gap-2">
                <button
                  type="submit"
                  disabled={isSavingContact}
                  className="flex-1 py-2 rounded-xl bg-red-600 text-white font-bold text-xs shadow-sm hover:bg-red-700"
                >
                  {isSavingContact ? 'Saving...' : 'Save Emergency Contact'}
                </button>
                <button
                  type="button"
                  onClick={() => setIsEditingContact(false)}
                  className="px-3 py-2 rounded-xl bg-slate-200 text-slate-700 font-bold text-xs"
                >
                  Cancel
                </button>
              </div>
            </form>
          )}
        </div>

        {/* Worker Verification Card or Customer Verified notice */}
        {!isCustomer ? (
          <VerificationCard />
        ) : (
          <div className="bg-emerald-50 border border-emerald-200 rounded-2xl p-3 flex items-center gap-2.5 text-xs text-emerald-900">
            <ShieldCheck className="w-4 h-4 text-emerald-600 shrink-0" />
            <span>Customer Verified • OTP Verified Account</span>
          </div>
        )}

        {/* Log Out Button */}
        <button
          onClick={handleLogout}
          className="w-full py-3.5 rounded-2xl bg-red-50 hover:bg-red-100 text-red-600 font-extrabold text-xs border border-red-200 flex items-center justify-center gap-2 active:scale-95 transition"
        >
          <LogOut className="w-4 h-4" />
          <span>Log Out of Session</span>
        </button>
      </div>
    </div>
  );
}
