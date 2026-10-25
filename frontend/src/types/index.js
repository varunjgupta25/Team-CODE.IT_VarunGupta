export const JOB_STATUS = {
  OPEN: 'open',
  NEGOTIATING: 'negotiating',
  ACCEPTED: 'accepted',
  IN_PROGRESS: 'in_progress',
  COMPLETED: 'completed',
  CANCELLED: 'cancelled',
};

export const OFFER_STATUS = {
  PENDING: 'pending',
  ACCEPTED: 'accepted',
  REJECTED: 'rejected',
};

export const ROLES = {
  CUSTOMER: 'customer',
  WORKER: 'worker',
  ADMIN: 'admin',
};

export const VERIFICATION_STATUS = {
  UNVERIFIED: 'unverified',
  PENDING: 'pending',
  APPROVED: 'approved',
  REJECTED: 'rejected',
};

export const CATEGORIES = [
  { id: 'plumber', label: 'Plumber', icon: 'Wrench', typicalRate: 350, description: 'Pipe leaks, taps, sanitary fitting' },
  { id: 'electrician', label: 'Electrician', icon: 'Zap', typicalRate: 400, description: 'Wiring, MCBs, appliances, switches' },
  { id: 'painter', label: 'Painter', icon: 'Paintbrush', typicalRate: 500, description: 'Touch-ups, full wall painting, waterproofing' },
  { id: 'cleaner', label: 'Cleaner', icon: 'Sparkles', typicalRate: 300, description: 'Deep home cleaning, kitchen & bathroom' },
  { id: 'maid', label: 'Maid', icon: 'Home', typicalRate: 250, description: 'Sweeping, dusting, daily assistance' },
  { id: 'cook', label: 'Cook', icon: 'Utensils', typicalRate: 450, description: 'North / South Indian meals, party help' },
  { id: 'carpenter', label: 'Carpenter', icon: 'Hammer', typicalRate: 450, description: 'Furniture repair, locks, doors, hinges' },
  { id: 'appliance', label: 'Appliance Repair', icon: 'Cpu', typicalRate: 500, description: 'AC service, washing machine, fridge' },
];

export const DEFAULT_COORDINATES = {
  lat: 19.2812,
  lng: 72.8697,
  address: 'Mira Road Station East, Mira Bhayandar, Maharashtra 401107',
};
