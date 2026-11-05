import React, { useState } from 'react';
import { AlertOctagon, PhoneCall, ShieldAlert } from 'lucide-react';
import { useJobStore } from '../../store/jobStore';

export function SosButton({ jobId, jobLocation }) {
  const [showModal, setShowModal] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [sentAlert, setSentAlert] = useState(null);
  const { triggerSos } = useJobStore();

  const handleConfirmSos = async () => {
    setIsSending(true);
    try {
      const res = await triggerSos(jobId, jobLocation || { lat: 19.2812, lng: 72.8697 });
      setSentAlert(res);
    } catch (err) {
      console.error('SOS dispatch error:', err);
    } finally {
      setIsSending(false);
    }
  };

  return (
    <>
      <button
        type="button"
        onClick={() => setShowModal(true)}
        className="flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-xl bg-red-600 hover:bg-red-700 text-white font-extrabold text-xs shadow-md shadow-red-500/30 animate-sos-glow active:scale-95 transition-all min-h-touch"
        title="Emergency Assistance SOS"
      >
        <AlertOctagon className="w-4 h-4 fill-white text-red-600" />
        <span>SOS EMERGENCY</span>
      </button>

      {showModal && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4 animate-in fade-in duration-150">
          <div className="bg-white rounded-3xl max-w-sm w-full p-6 shadow-2xl border-2 border-red-500 text-center space-y-4">
            <div className="w-16 h-16 rounded-full bg-red-100 text-red-600 mx-auto flex items-center justify-center animate-bounce">
              <ShieldAlert className="w-9 h-9" />
            </div>

            <div>
              <h3 className="text-xl font-black text-slate-900">Emergency SOS Alert</h3>
              <p className="text-xs text-slate-600 mt-1.5 leading-relaxed">
                This triggers a priority alert with your GPS coordinates directly to our Safety Dispatch &amp; local emergency response team.
              </p>
            </div>

            {sentAlert ? (
              <div className="bg-red-50 border border-red-200 rounded-2xl p-4 text-left space-y-2">
                <div className="flex items-center gap-2 text-red-800 font-bold text-xs">
                  <span className="w-2 h-2 rounded-full bg-red-600 animate-ping" />
                  ALERT BROADCAST ACTIVE
                </div>
                <p className="text-[11px] text-slate-700">
                  Alert ID: <code className="bg-white px-1.5 py-0.5 rounded border text-red-700">{sentAlert.alertId}</code>
                </p>
                <p className="text-[11px] text-slate-600">
                  Location dispatched: Mira Road (Lat: 19.281, Lng: 72.870)
                </p>
                <a
                  href="tel:112"
                  className="flex items-center justify-center gap-2 w-full mt-3 py-2.5 rounded-xl bg-red-600 text-white font-black text-xs hover:bg-red-700 transition"
                >
                  <PhoneCall className="w-4 h-4" /> Call Police Helpline (112)
                </a>
              </div>
            ) : (
              <div className="space-y-2 pt-2">
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
