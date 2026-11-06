import React, { useState, useEffect } from 'react';
import {
  AlertOctagon,
  PhoneCall,
  ShieldAlert,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  ExternalLink,
  UserPlus,
} from 'lucide-react';
import { useJobStore } from '../../store/jobStore';
import { api } from '../../api';
import { useToastStore } from '../../store/toastStore';

export function SosButton({ jobId, jobLocation }) {
  const [showModal, setShowModal] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [sentAlert, setSentAlert] = useState(null);
  const [emergencyContact, setEmergencyContact] = useState(null);
  const [showAddContact, setShowAddContact] = useState(false);
  const [contactName, setContactName] = useState('');
  const [contactPhone, setContactPhone] = useState('');
  const [isSavingContact, setIsSavingContact] = useState(false);
  const { triggerSos } = useJobStore();

  useEffect(() => {
    if (showModal) {
      api.getEmergencyContact().then((c) => {
        setEmergencyContact(c);
      }).catch(() => {
        setEmergencyContact(null);
      });
    }
  }, [showModal]);

  const handleSaveContact = async (e) => {
    e.preventDefault();
    if (!contactName.trim() || !contactPhone.trim()) return;

    setIsSavingContact(true);
    try {
      const res = await api.setEmergencyContact({
        name: contactName.trim(),
        phone: contactPhone.trim(),
      });
      setEmergencyContact(res?.emergencyContact || { name: contactName.trim(), phone: contactPhone.trim() });
      setShowAddContact(false);
      useToastStore.getState().success('Emergency contact saved successfully!');
    } catch (err) {
      useToastStore.getState().error(err.message || 'Failed to save contact. Ensure valid Indian +91 number.');
    } finally {
      setIsSavingContact(false);
    }
  };

  const handleConfirmSos = async () => {
    setIsSending(true);
    try {
      const coords = jobLocation || { lat: 19.2812, lng: 72.8697 };
      const res = await triggerSos(jobId, coords);
      setSentAlert(res);
    } catch (err) {
      console.error('SOS dispatch error:', err);
      setSentAlert({
        status: 'failed',
        message: err.message || 'SOS dispatch failed. Please call 112 immediately.',
        recipients: [],
      });
    } finally {
      setIsSending(false);
    }
  };

  const isNotified = sentAlert?.status === 'notified' || sentAlert?.status === 'recorded';
  const isPartial = sentAlert?.status === 'partial';
  const isFailed = sentAlert?.status === 'failed' || (sentAlert && !isNotified && !isPartial);

  return (
    <>
      <button
        type="button"
        onClick={() => {
          setShowModal(true);
          setSentAlert(null);
        }}
        className="flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-xl bg-red-600 hover:bg-red-700 text-white font-extrabold text-xs shadow-md shadow-red-500/30 animate-sos-glow active:scale-95 transition-all min-h-touch"
        title="Emergency Assistance SOS"
      >
        <AlertOctagon className="w-4 h-4 fill-white text-red-600" />
        <span>SOS EMERGENCY</span>
      </button>

      {showModal && (
        <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4 animate-in fade-in duration-150">
          <div className="bg-white rounded-3xl max-w-sm w-full p-5 shadow-2xl border-2 border-red-500 text-center space-y-4">
            <div className="w-14 h-14 rounded-full bg-red-100 text-red-600 mx-auto flex items-center justify-center animate-bounce">
              <ShieldAlert className="w-8 h-8" />
            </div>

            <div>
              <h3 className="text-lg font-black text-slate-900">Emergency SOS Dispatch</h3>
              <p className="text-xs text-slate-600 mt-1 leading-relaxed">
                Sends live GPS coordinates directly to your emergency contact and 24/7 Safety Ops.
              </p>
            </div>

            {/* Emergency Contact Warning if none is configured */}
            {!sentAlert && !emergencyContact && !showAddContact && (
              <div className="bg-amber-50 border border-amber-200 rounded-2xl p-3 text-left space-y-1.5">
                <div className="flex items-center gap-1.5 text-amber-900 font-extrabold text-[11px]">
                  <AlertTriangle className="w-3.5 h-3.5 text-amber-600 shrink-0" />
                  <span>No Emergency Contact Set</span>
                </div>
                <p className="text-[10px] text-amber-800 leading-tight">
                  Only Safety Ops will be notified. Add a family member/friend for immediate SMS alert.
                </p>
                <button
                  type="button"
                  onClick={() => setShowAddContact(true)}
                  className="text-[10px] font-bold text-amber-900 underline flex items-center gap-1 pt-0.5"
                >
                  <UserPlus className="w-3 h-3" /> Add Emergency Contact Now
                </button>
              </div>
            )}

            {/* Quick Add Emergency Contact Form */}
            {!sentAlert && showAddContact && (
              <form onSubmit={handleSaveContact} className="bg-slate-50 border border-slate-200 rounded-2xl p-3 text-left space-y-2">
                <span className="text-[11px] font-bold text-slate-800 block">Add Emergency Contact (+91)</span>
                <input
                  type="text"
                  required
                  placeholder="Contact Name (e.g. Papa / Priya)"
                  value={contactName}
                  onChange={(e) => setContactName(e.target.value)}
                  className="w-full text-xs p-2 rounded-xl border border-slate-200 bg-white"
                />
                <input
                  type="tel"
                  required
                  placeholder="10-digit Mobile (e.g. 9820123456)"
                  value={contactPhone}
                  onChange={(e) => setContactPhone(e.target.value)}
                  className="w-full text-xs p-2 rounded-xl border border-slate-200 bg-white"
                />
                <div className="flex items-center gap-1.5">
                  <button
                    type="submit"
                    disabled={isSavingContact}
                    className="flex-1 py-1.5 rounded-xl bg-brand-600 text-white text-[10px] font-bold"
                  >
                    {isSavingContact ? 'Saving...' : 'Save Contact'}
                  </button>
                  <button
                    type="button"
                    onClick={() => setShowAddContact(false)}
                    className="px-2 py-1.5 rounded-xl bg-slate-200 text-slate-700 text-[10px] font-bold"
                  >
                    Cancel
                  </button>
                </div>
              </form>
            )}

            {/* Configured Contact Notice */}
            {!sentAlert && emergencyContact && (
              <div className="bg-slate-50 border border-slate-200 rounded-2xl p-2.5 text-left text-[11px] text-slate-700 flex items-center justify-between">
                <div>
                  <span className="text-[10px] text-slate-400 block font-medium">Emergency Contact</span>
                  <span className="font-bold text-slate-900">{emergencyContact.name}</span>
                  <span className="text-slate-500 font-mono text-[10px] ml-1.5">{emergencyContact.phone}</span>
                </div>
                <button
                  type="button"
                  onClick={() => {
                    setContactName(emergencyContact.name || '');
                    setContactPhone(emergencyContact.phone || '');
                    setShowAddContact(true);
                  }}
                  className="text-[10px] text-brand-600 underline font-semibold"
                >
                  Edit
                </button>
              </div>
            )}

            {/* Post-Dispatch State Handling */}
            {sentAlert ? (
              <div className="space-y-3">
                {/* 1. Fully Notified State */}
                {isNotified && (
                  <div className="bg-emerald-50 border border-emerald-200 rounded-2xl p-4 text-left space-y-2">
                    <div className="flex items-center gap-1.5 text-emerald-800 font-extrabold text-xs">
                      <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                      <span>HELP REQUEST NOTIFIED</span>
                    </div>
                    <p className="text-[11px] text-slate-700 leading-snug">
                      Alert sent with live GPS coordinates to all configured contacts &amp; Safety Ops team.
                    </p>
                    <div className="pt-1 border-t border-emerald-100 space-y-1 text-[10px] text-slate-600">
                      {sentAlert.recipients?.map((r, i) => (
                        <div key={i} className="flex items-center justify-between font-mono">
                          <span>{r.target === 'emergency_contact' ? 'Emergency Contact' : 'Ops Dispatch'}:</span>
                          <span className="text-emerald-700 font-bold">✓ DELIVERED</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* 2. Partial State */}
                {isPartial && (
                  <div className="bg-amber-50 border border-amber-200 rounded-2xl p-4 text-left space-y-2">
                    <div className="flex items-center gap-1.5 text-amber-800 font-extrabold text-xs">
                      <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
                      <span>PARTIAL ALERT DELIVERY</span>
                    </div>
                    <p className="text-[11px] text-slate-700 leading-snug">
                      Some alert channels failed to confirm receipt. Do not wait — call helpline below.
                    </p>
                  </div>
                )}

                {/* 3. Failed State - NEVER claim help is coming! */}
                {isFailed && (
                  <div className="bg-red-50 border-2 border-red-300 rounded-2xl p-4 text-left space-y-2">
                    <div className="flex items-center gap-1.5 text-red-800 font-extrabold text-xs">
                      <XCircle className="w-4 h-4 text-red-600 shrink-0" />
                      <span>AUTOMATED DISPATCH FAILED</span>
                    </div>
                    <p className="text-xs text-red-700 font-semibold leading-relaxed">
                      Automated alert notification could not be delivered to contacts. Please call the emergency helpline directly right now.
                    </p>
                  </div>
                )}

                {/* Always prominent 112 Call Button */}
                <a
                  href="tel:112"
                  className="flex items-center justify-center gap-2 w-full py-3 rounded-2xl bg-red-600 text-white font-black text-sm hover:bg-red-700 shadow-md shadow-red-500/25 transition"
                >
                  <PhoneCall className="w-4 h-4" /> Tap to Call Emergency (112)
                </a>

                {sentAlert.mapsUrl && (
                  <a
                    href={sentAlert.mapsUrl}
                    target="_blank"
                    rel="noreferrer"
                    className="flex items-center justify-center gap-1 text-[11px] text-slate-500 underline font-medium"
                  >
                    <span>View GPS Location on Google Maps</span>
                    <ExternalLink className="w-3 h-3" />
                  </a>
                )}
              </div>
            ) : (
              <div className="space-y-2 pt-1">
                <button
                  disabled={isSending}
                  onClick={handleConfirmSos}
                  className="w-full py-3.5 rounded-2xl bg-red-600 hover:bg-red-700 text-white font-extrabold text-sm shadow-lg shadow-red-600/30 active:scale-95 transition-all flex items-center justify-center gap-2"
                >
                  <AlertOctagon className="w-5 h-5 fill-white text-red-600" />
                  {isSending ? 'DISPATCHING SOS...' : 'CONFIRM & SEND SOS NOW'}
                </button>

                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="w-full py-2.5 rounded-xl text-slate-500 hover:text-slate-800 text-xs font-semibold"
                >
                  Cancel (False Alarm)
                </button>
              </div>
            )}

            {sentAlert && (
              <button
                onClick={() => {
                  setShowModal(false);
                  setSentAlert(null);
                }}
                className="w-full py-2.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-800 text-xs font-bold transition"
              >
                Close Window
              </button>
            )}
          </div>
        </div>
      )}
    </>
  );
}
