import React, { useState } from 'react';
import { ShieldCheck, Award, Info, X } from 'lucide-react';

export function TrustBadge({ score = 85, tier = 'Gold', showDetails = false }) {
  const [openModal, setOpenModal] = useState(false);

  let badgeColor = 'bg-amber-50 text-amber-800 border-amber-300';
  let badgeIconColor = 'text-amber-600';
  if (tier === 'Gold') {
    badgeColor = 'bg-yellow-50 text-yellow-900 border-yellow-400';
    badgeIconColor = 'text-yellow-600';
  } else if (tier === 'Silver') {
    badgeColor = 'bg-slate-100 text-slate-800 border-slate-300';
    badgeIconColor = 'text-slate-600';
  }

  return (
    <>
      <div 
        onClick={(e) => {
          e.stopPropagation();
          setOpenModal(true);
        }}
        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full border text-[11px] font-bold cursor-pointer hover:opacity-90 active:scale-95 transition-all ${badgeColor}`}
        title="Click to view trust calculation"
      >
        <ShieldCheck className={`w-3 h-3 ${badgeIconColor}`} />
        <span>{tier} Trust ({score})</span>
      </div>

      {openModal && (
        <div 
          onClick={(e) => {
            e.stopPropagation();
            setOpenModal(false);
          }}
          className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4"
        >
          <div 
            onClick={(e) => e.stopPropagation()}
            className="bg-white rounded-2xl max-w-xs w-full p-5 shadow-2xl border border-slate-200 animate-in fade-in zoom-in-95 duration-150"
          >
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-full bg-yellow-100 text-yellow-700 flex items-center justify-center font-black">
                  <Award className="w-4 h-4" />
                </div>
                <div>
                  <h4 className="text-sm font-bold text-slate-900">{tier} Trust Tier</h4>
                  <p className="text-[11px] text-slate-500">Score: {score}/100</p>
                </div>
              </div>
              <button 
                onClick={() => setOpenModal(false)}
                className="p-1 rounded-lg hover:bg-slate-100 text-slate-400 hover:text-slate-700"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="py-3 space-y-2 text-xs text-slate-600">
              <p className="font-semibold text-slate-900">How Trust Score is Computed:</p>
              <div className="flex justify-between py-1 border-b border-slate-50">
                <span>Government ID Verified</span>
                <span className="font-bold text-emerald-600">+30 pts</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-50">
                <span>Customer Ratings (avg &gt; 4.5)</span>
                <span className="font-bold text-emerald-600">+30 pts</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-50">
                <span>Jobs Successfully Delivered</span>
                <span className="font-bold text-emerald-600">+20 pts</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-50">
                <span>Active History &amp; Clean Record</span>
                <span className="font-bold text-emerald-600">+20 pts</span>
              </div>
              <div className="flex justify-between py-1 text-slate-500 text-[10px]">
                <span>Tiers: Gold (&ge;80), Silver (&ge;50), Bronze (&lt;50)</span>
              </div>
            </div>

            <button
              onClick={() => setOpenModal(false)}
              className="w-full mt-2 py-2 rounded-xl bg-slate-900 text-white text-xs font-bold hover:bg-slate-800 transition"
            >
              Got it
            </button>
          </div>
        </div>
      )}
    </>
  );
}
