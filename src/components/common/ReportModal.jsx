import React, { useState } from 'react';
import { Flag, X } from 'lucide-react';
import { useJobStore } from '../../store/jobStore';

const REPORT_REASONS = [
  'Price dispute / Demanding cash outside app',
  'Unprofessional behavior or harassment',
  'Safety concern or property damage',
  'No show / excessive delay without notice',
  'Substandard work quality / damaged equipment',
];

export function ReportModal({ isOpen, onClose, jobId, targetUserId, targetUserName = 'User' }) {
  const [selectedReason, setSelectedReason] = useState(REPORT_REASONS[0]);
  const [details, setDetails] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const { reportUser } = useJobStore();

  if (!isOpen) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      const fullReason = `${selectedReason}${details ? `: ${details}` : ''}`;
      await reportUser(jobId, targetUserId, fullReason);
      onClose();
    } catch (err) {
      console.error(err);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 animate-in fade-in duration-150">
      <div className="bg-white rounded-3xl max-w-sm w-full p-5 shadow-2xl border border-slate-200">
        <div className="flex items-center justify-between pb-3 border-b border-slate-100">
          <div className="flex items-center gap-2 text-red-600 font-bold text-sm">
            <Flag className="w-4 h-4" />
            <span>Report Issue with {targetUserName}</span>
          </div>
          <button onClick={onClose} className="p-1 rounded-lg hover:bg-slate-100 text-slate-400">
            <X className="w-4 h-4" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="py-3 space-y-3">
          <p className="text-xs text-slate-600">
            Select the primary reason for reporting. Users with multiple reports are automatically reviewed by admin.
          </p>

          <div className="space-y-1.5 max-h-48 overflow-y-auto pr-1">
            {REPORT_REASONS.map((reason) => (
              <label
                key={reason}
                className={`flex items-start gap-2.5 p-2.5 rounded-xl border text-xs cursor-pointer transition ${
                  selectedReason === reason
                    ? 'border-red-500 bg-red-50 text-red-950 font-semibold'
                    : 'border-slate-200 bg-slate-50 text-slate-700 hover:bg-slate-100'
                }`}
              >
                <input
                  type="radio"
                  name="reportReason"
                  checked={selectedReason === reason}
                  onChange={() => setSelectedReason(reason)}
                  className="mt-0.5 text-red-600 focus:ring-red-500"
                />
                <span>{reason}</span>
              </label>
            ))}
          </div>

          <div>
            <label className="block text-[11px] font-bold text-slate-700 mb-1">
              Additional Details (Optional)
            </label>
            <textarea
              rows={2}
              value={details}
              onChange={(e) => setDetails(e.target.value)}
              placeholder="Explain what happened..."
              className="w-full text-xs p-2.5 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-red-500"
            />
          </div>

          <div className="flex gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 py-2.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-bold"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="flex-1 py-2.5 rounded-xl bg-red-600 hover:bg-red-700 text-white text-xs font-bold shadow-md shadow-red-500/20"
            >
              {isSubmitting ? 'Submitting...' : 'Submit Report'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
