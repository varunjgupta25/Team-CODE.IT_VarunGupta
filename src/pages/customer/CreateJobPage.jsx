import React, { useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useJobStore } from '../../store/jobStore';
import { useAuthStore } from '../../store/authStore';
import { CATEGORIES, DEFAULT_COORDINATES } from '../../types';
import { MapPicker } from '../../components/map/MapPicker';
import { ArrowLeft, Clock, Calendar, Sparkles } from 'lucide-react';

export function CreateJobPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const initialCategory = searchParams.get('category') || 'plumber';

  const { createJob, isLoading } = useJobStore();
  const { user } = useAuthStore();

  const [category, setCategory] = useState(initialCategory);
  const [description, setDescription] = useState('');
  const [customerName, setCustomerName] = useState(user?.name || '');
  const [customerPhone, setCustomerPhone] = useState(user?.phone || '');
  const [mode, setMode] = useState('on_demand'); // 'on_demand' or 'scheduled'
  const [scheduledDate, setScheduledDate] = useState('');
  const [budget, setBudget] = useState('');
  const [location, setLocation] = useState(DEFAULT_COORDINATES);
  const [address, setAddress] = useState('B-402, Shanti Park, Mira Road East, Mumbai');


  const selectedCategoryObj = CATEGORIES.find((c) => c.id === category) || CATEGORIES[0];

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!description.trim()) {
      return;
    }

    try {
      const resolvedName = (customerName || user?.name || 'Customer').trim();
      const resolvedPhone = (customerPhone || user?.phone || '').trim();

      const jobData = {
        customerId: user?.uid || `cust_${Date.now()}`,
        customerName: resolvedName,
        customerPhone: resolvedPhone,
        category,
        description,
        mode,
        scheduledAt: mode === 'scheduled' ? scheduledDate : null,
        budget: budget ? Number(budget) : null,
        location: {
          lat: location.lat,
          lng: location.lng,
          address: address.trim() || 'Mira Road, Mumbai',
        },
      };

      const newJob = await createJob(jobData);
      navigate(`/customer/match/${newJob.id}`);
    } catch (err) {
      console.error('Job creation error:', err);
    }
  };

  return (
    <div className="space-y-4 pt-1">
      {/* Header with back button */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => navigate('/')}
          className="w-9 h-9 rounded-xl bg-white border border-slate-200 flex items-center justify-center text-slate-700 hover:bg-slate-100 active:scale-95 transition"
        >
          <ArrowLeft className="w-4 h-4" />
        </button>
        <div>
          <h1 className="text-lg font-black text-slate-900 tracking-tight">Request Service</h1>
          <p className="text-[11px] text-slate-500">Nearest verified workers will be matched</p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Service Category Selector Pills */}
        <div className="space-y-1.5">
          <label className="block text-xs font-bold text-slate-800">Service Category</label>
          <div className="flex gap-2 overflow-x-auto no-scrollbar py-1">
            {CATEGORIES.map((cat) => (
              <button
                key={cat.id}
                type="button"
                onClick={() => setCategory(cat.id)}
                className={`px-3 py-2 rounded-xl text-xs font-bold whitespace-nowrap border shrink-0 transition-all ${
                  category === cat.id
                    ? 'bg-brand-600 text-white border-brand-600 shadow-md shadow-brand-500/20'
                    : 'bg-white text-slate-700 border-slate-200 hover:bg-slate-50'
                }`}
              >
                {cat.label}
              </button>
            ))}
          </div>
        </div>

        {/* Contact Info (Pre-filled from login) */}
        <div className="grid grid-cols-2 gap-2.5">
          <div className="space-y-1">
            <label className="block text-[11px] font-bold text-slate-800">Your Name</label>
            <input
              type="text"
              required
              value={customerName}
              onChange={(e) => setCustomerName(e.target.value)}
              placeholder="E.g. Varun Gupta"
              className="w-full text-xs p-2.5 rounded-xl border border-slate-200 bg-white focus:ring-2 focus:ring-brand-500"
            />
          </div>
          <div className="space-y-1">
            <label className="block text-[11px] font-bold text-slate-800">Mobile Number</label>
            <input
              type="tel"
              required
              value={customerPhone}
              onChange={(e) => setCustomerPhone(e.target.value)}
              placeholder="E.g. +91 98765 00000"
              className="w-full text-xs p-2.5 rounded-xl border border-slate-200 bg-white focus:ring-2 focus:ring-brand-500"
            />
          </div>
        </div>

        {/* Problem Description */}
        <div className="space-y-1.5">
          <div className="flex justify-between items-center">
            <label className="text-xs font-bold text-slate-800">Problem Description</label>
            <span className="text-[10px] text-slate-400">Be specific</span>
          </div>
          <textarea
            required
            rows={3}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder={`E.g., Kitchen sink pipe is leaking under the counter. Need immediate tap replacement.`}
            className="w-full text-xs p-3 rounded-2xl border border-slate-200 bg-white focus:outline-none focus:ring-2 focus:ring-brand-500 shadow-sm"
          />
        </div>

        {/* Urgency Mode: On-Demand vs Scheduled */}
        <div className="space-y-1.5">
          <label className="block text-xs font-bold text-slate-800">When do you need it?</label>
          <div className="grid grid-cols-2 gap-2.5">
            <button
              type="button"
              onClick={() => setMode('on_demand')}
              className={`p-3 rounded-2xl border text-left transition-all ${
                mode === 'on_demand'
                  ? 'border-brand-600 bg-brand-50/50 shadow-sm'
                  : 'border-slate-200 bg-white hover:bg-slate-50'
              }`}
            >
              <div className="flex items-center gap-1.5 font-extrabold text-xs text-brand-700 mb-1">
                <Clock className="w-3.5 h-3.5" />
                <span>On-Demand</span>
              </div>
              <p className="text-[11px] text-slate-600 font-medium">Doorstep in ~30 mins</p>
            </button>

            <button
              type="button"
              onClick={() => setMode('scheduled')}
              className={`p-3 rounded-2xl border text-left transition-all ${
                mode === 'scheduled'
                  ? 'border-brand-600 bg-brand-50/50 shadow-sm'
                  : 'border-slate-200 bg-white hover:bg-slate-50'
              }`}
            >
              <div className="flex items-center gap-1.5 font-extrabold text-xs text-slate-800 mb-1">
                <Calendar className="w-3.5 h-3.5 text-slate-600" />
                <span>Schedule Later</span>
              </div>
              <p className="text-[11px] text-slate-600 font-medium">Pick a date &amp; time</p>
            </button>
          </div>

          {mode === 'scheduled' && (
            <div className="pt-1">
              <input
                type="datetime-local"
                required
                value={scheduledDate}
                onChange={(e) => setScheduledDate(e.target.value)}
                className="w-full text-xs p-2.5 rounded-xl border border-slate-200 bg-white focus:ring-2 focus:ring-brand-500"
              />
            </div>
          )}
        </div>

        {/* Budget (Optional) with Fair Price Hint */}
        <div className="space-y-1.5">
          <div className="flex justify-between items-center">
            <label className="text-xs font-bold text-slate-800">Your Target Budget (Optional)</label>
            <span className="text-[10px] text-brand-600 font-bold bg-brand-50 px-2 py-0.5 rounded-full">
              Fair hint: ₹{selectedCategoryObj.typicalRate - 50} - ₹{selectedCategoryObj.typicalRate + 100}
            </span>
          </div>
          <div className="relative">
            <span className="absolute left-3 top-2.5 text-slate-400 font-bold text-xs">₹</span>
            <input
              type="number"
              min="100"
              step="50"
              value={budget}
              onChange={(e) => setBudget(e.target.value)}
              placeholder={`Typical rate is ~₹${selectedCategoryObj.typicalRate} (leave empty if unsure)`}
              className="w-full text-xs pl-7 pr-3 py-2.5 rounded-xl border border-slate-200 bg-white focus:ring-2 focus:ring-brand-500"
            />
          </div>
          <p className="text-[10px] text-slate-500">
            Workers set their own rates and you can counter-offer after matching.
          </p>
        </div>

        {/* Drop Map Pin Picker */}
        <div className="space-y-1.5">
          <label className="block text-xs font-bold text-slate-800">
            Service Location (Drop Pin)
          </label>
          <MapPicker
            value={location}
            onChange={(newPos) => setLocation(newPos)}
            address={address}
            onAddressChange={(newAddr) => setAddress(newAddr)}
          />

          <div className="mt-1">
            <input
              type="text"
              required
              value={address}
              onChange={(e) => setAddress(e.target.value)}
              placeholder="Flat / Wing, Society name, Landmark"
              className="w-full text-xs p-2.5 rounded-xl border border-slate-200 bg-white focus:ring-2 focus:ring-brand-500"
            />
          </div>
        </div>

        {/* Submit Button */}
        <div className="pt-2">
          <button
            type="submit"
            disabled={isLoading || !description.trim()}
            className="w-full py-3.5 rounded-2xl bg-brand-600 hover:bg-brand-700 disabled:opacity-50 text-white font-extrabold text-sm shadow-lg shadow-brand-500/25 active:scale-95 transition-all flex items-center justify-center gap-2 min-h-touch"
          >
            <Sparkles className="w-4 h-4" />
            <span>{isLoading ? 'Creating Job...' : 'Find Nearest Verified Workers'}</span>
          </button>
        </div>
      </form>
    </div>
  );
}
