import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs) {
  return twMerge(clsx(inputs));
}

/**
 * Calculates Haversine distance in kilometers between two lat/lng coordinates
 */
export function calcDistanceKm(lat1, lon1, lat2, lon2) {
  if (!lat1 || !lon1 || !lat2 || !lon2) return 1.5;
  const R = 6371; // Earth's radius in km
  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLon = ((lon2 - lon1) * Math.PI) / 180;
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos((lat1 * Math.PI) / 180) *
      Math.cos((lat2 * Math.PI) / 180) *
      Math.sin(dLon / 2) *
      Math.sin(dLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  const distance = R * c;
  return Math.round(distance * 10) / 10;
}

/**
 * Calculates travel ETA in minutes assuming 25 km/h urban speed + 3 min buffer
 */
export function calcEtaMinutes(distanceKm) {
  if (!distanceKm || distanceKm <= 0) return 8;
  const transitMinutes = Math.round((distanceKm / 25) * 60);
  return Math.max(5, transitMinutes + 3);
}

export function formatCurrency(amount) {
  if (amount === undefined || amount === null) return '₹0';
  return `₹${Number(amount).toLocaleString('en-IN')}`;
}

export function formatTimeAgo(timestamp) {
  if (!timestamp) return 'Just now';
  const diffSec = Math.floor((Date.now() - new Date(timestamp).getTime()) / 1000);
  if (diffSec < 60) return `${diffSec}s ago`;
  const diffMin = Math.floor(diffSec / 60);
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHours = Math.floor(diffMin / 60);
  return `${diffHours}h ago`;
}

/**
 * Trust score formula (0-100):
 * verified (30) + rating scaled (30) + jobs done capped (20) + account age (10) + clean record (10) - penalty
 */
export function computeTrust(worker) {
  const verifiedScore = worker.verified ? 30 : 0;
  const ratingScore = Math.min(30, Math.round(((worker.rating || 4.5) / 5) * 30));
  const jobsDoneScore = Math.min(20, Math.round(((worker.jobsDone || 0) / 50) * 20));
  const accountAgeScore = 10; // Active > 6 months
  const cleanRecordScore = (worker.reportCount || 0) > 0 ? 0 : 10;
  const penalty = (worker.reportCount || 0) * 15;

  const total = Math.max(0, Math.min(100, verifiedScore + ratingScore + jobsDoneScore + accountAgeScore + cleanRecordScore - penalty));

  let tier = 'Bronze';
  let badgeColor = 'bg-amber-100 text-amber-800 border-amber-300';
  if (total >= 80) {
    tier = 'Gold';
    badgeColor = 'bg-yellow-100 text-yellow-800 border-yellow-400';
  } else if (total >= 50) {
    tier = 'Silver';
    badgeColor = 'bg-slate-100 text-slate-800 border-slate-300';
  }

  return { score: total, tier, badgeColor };
}
