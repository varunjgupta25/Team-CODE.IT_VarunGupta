import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useJobStore } from '../../store/jobStore';
import { api } from '../../api';
import { useToastStore } from '../../store/toastStore';
import { Star, CheckCircle2, ArrowLeft, Heart, ShieldCheck, Check } from 'lucide-react';
import { storage } from '../../lib/storage';

const COMPLIMENT_TAGS = [
  'Punctual arrival',
  'Polite & Professional',
  'Clean Workmanship',
  'Fair agreed pricing',
  'Fast Resolution',
];

export function ReviewPage() {
  const { jobId } = useParams();
  const navigate = useNavigate();
  const { currentJob, fetchJob } = useJobStore();

  const [rating, setRating] = useState(5);
  const [hoverRating, setHoverRating] = useState(5);
  const [comment, setComment] = useState('');
  const [selectedTags, setSelectedTags] = useState([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [loadedJob, setLoadedJob] = useState(currentJob);
  const [workerDetails, setWorkerDetails] = useState(null);

  useEffect(() => {
    if (jobId && !currentJob) {
      fetchJob(jobId).then((res) => {
        if (res) setLoadedJob(res);
      }).catch(() => {});
    }
  }, [jobId, currentJob, fetchJob]);

  const activeJob = currentJob || loadedJob;
  const workerId = activeJob?.acceptedWorkerId;
  const allWorkers = storage.get('rb_mock_workers_v1', []);
  const storedWorker = allWorkers.find((w) => w.uid === workerId) || null;
  const worker = workerDetails || storedWorker;
  const resolvedWorkerId = worker?.uid || workerId || activeJob?.acceptedWorkerId;

  useEffect(() => {
    if (resolvedWorkerId && !workerDetails) {
      api.getWorker(resolvedWorkerId).then((res) => {
        if (res) setWorkerDetails(res);
      }).catch(() => {});
    }
  }, [resolvedWorkerId, workerDetails]);

  const toggleTag = (tag) => {
    setSelectedTags((prev) =>
      prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag]
    );
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!resolvedWorkerId) {
      useToastStore.getState().error('Could not identify assigned worker for this review.');
      return;
    }
    setIsSubmitting(true);
    try {
      const fullComment = [
        comment.trim(),
        selectedTags.length > 0 ? `Compliments: ${selectedTags.join(', ')}` : '',
      ].filter(Boolean).join(' | ');

      await api.submitReview({
        jobId: jobId || activeJob?.id || 'job_test',
        workerId: resolvedWorkerId,
        rating,
        comment: fullComment || 'Great service!',
        tags: selectedTags,
      });
      setIsSubmitted(true);
      useToastStore.getState().success('Review submitted! Worker rating updated.');
    } catch {
      useToastStore.getState().error('Failed to submit review');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isSubmitted) {
    return (
      <div className="pt-8 text-center space-y-4">
        <div className="w-16 h-16 rounded-full bg-emerald-100 text-emerald-600 mx-auto flex items-center justify-center animate-bounce">
          <CheckCircle2 className="w-10 h-10" />
        </div>
        <div>
          <h2 className="text-xl font-black text-slate-900">Thank You!</h2>
          <p className="text-xs text-slate-600 mt-1 max-w-xs mx-auto">
            Your feedback directly boosts {worker?.name || 'the worker'}&apos;s verified trust score on the platform.
          </p>
        </div>
        <button
          onClick={() => navigate('/')}
          className="w-full py-3.5 rounded-2xl bg-brand-600 hover:bg-brand-700 text-white font-extrabold text-xs shadow-lg shadow-brand-500/20 active:scale-95 transition min-h-touch"
        >
          Return to Home
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-5 pt-1">
      {/* Top Header */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => navigate('/')}
          className="w-9 h-9 rounded-xl bg-white border border-slate-200 flex items-center justify-center text-slate-700 hover:bg-slate-100 active:scale-95 transition"
        >
          <ArrowLeft className="w-4 h-4" />
        </button>
        <div>
          <h1 className="text-lg font-black text-slate-900 tracking-tight">Rate Service</h1>
          <p className="text-[11px] text-slate-500">Help the community discover reliable tradesmen</p>
        </div>
      </div>

      {/* Worker Card */}
      {worker && (
        <div className="bg-white rounded-3xl p-4 border border-slate-200 shadow-sm flex items-center gap-3.5">
          <img
            src={worker.avatarUrl}
            alt={worker.name}
            className="w-14 h-14 rounded-2xl object-cover border-2 border-brand-500"
          />
          <div>
            <div className="flex items-center gap-1.5">
              <h3 className="font-extrabold text-sm text-slate-900">{worker.name}</h3>
              <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-emerald-100 text-emerald-800 flex items-center gap-0.5">
                <ShieldCheck className="w-2.5 h-2.5" /> Verified
              </span>
            </div>
            <p className="text-xs text-slate-500 capitalize">{currentJob?.category || 'Service'} Specialist</p>
            <p className="text-[11px] text-brand-600 font-semibold mt-0.5">Mira Road, Mumbai</p>
          </div>
        </div>
      )}

      {/* Review Form */}
      <form onSubmit={handleSubmit} className="bg-white rounded-3xl p-5 border border-slate-200 shadow-sm space-y-4">
        {/* Star Rating Selector */}
        <div className="text-center space-y-2">
          <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider">
            How was your experience?
          </label>

          <div className="flex items-center justify-center gap-2 py-2">
            {[1, 2, 3, 4, 5].map((star) => (
              <button
                key={star}
                type="button"
                onClick={() => setRating(star)}
                onMouseEnter={() => setHoverRating(star)}
                onMouseLeave={() => setHoverRating(rating)}
                className="p-1 active:scale-125 transition-transform"
              >
                <Star
                  className={`w-8 h-8 ${
                    (hoverRating || rating) >= star
                      ? 'fill-amber-400 text-amber-400'
                      : 'text-slate-200'
                  }`}
                />
              </button>
            ))}
          </div>

          <p className="text-xs font-extrabold text-amber-600">
            {rating === 5 && 'Outstanding & Professional (5/5)'}
            {rating === 4 && 'Very Good Quality (4/5)'}
            {rating === 3 && 'Average Job (3/5)'}
            {rating === 2 && 'Needs Improvement (2/5)'}
            {rating === 1 && 'Unsatisfactory (1/5)'}
          </p>
        </div>

        {/* Written Review */}
        <div className="space-y-1.5">
          <label className="block text-xs font-bold text-slate-800">
            Write a Quick Review (Optional)
          </label>
          <textarea
            rows={3}
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            placeholder="Punctual, polite, fixed the pipe leak in 20 minutes without any mess..."
            className="w-full text-xs p-3 rounded-2xl border border-slate-200 bg-slate-50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-brand-500"
          />
        </div>

        {/* Quick Tag Pills (Module H) */}
        <div className="space-y-1.5">
          <span className="text-[11px] font-semibold text-slate-600 block">
            Tap compliments to highlight exceptional service:
          </span>
          <div className="flex flex-wrap gap-1.5 pt-0.5">
            {COMPLIMENT_TAGS.map((tag) => {
              const isSelected = selectedTags.includes(tag);
              return (
                <button
                  key={tag}
                  type="button"
                  onClick={() => toggleTag(tag)}
                  className={`text-[11px] font-bold px-3 py-1.5 rounded-full border transition-all flex items-center gap-1 active:scale-95 ${
                    isSelected
                      ? 'bg-brand-600 border-brand-600 text-white shadow-sm shadow-brand-500/20'
                      : 'bg-slate-50 border-slate-200 text-slate-700 hover:bg-slate-100'
                  }`}
                >
                  {isSelected && <Check className="w-3 h-3 stroke-[3]" />}
                  <span>{tag}</span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Submit Review Button */}
        <div className="pt-2">
          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full py-3.5 rounded-2xl bg-brand-600 hover:bg-brand-700 text-white font-extrabold text-xs shadow-lg shadow-brand-500/20 active:scale-95 transition min-h-touch flex items-center justify-center gap-2"
          >
            <Heart className="w-4 h-4 fill-white" />
            <span>{isSubmitting ? 'Posting Review...' : 'Submit Rating & Feedback'}</span>
          </button>
        </div>
      </form>
    </div>
  );
}
