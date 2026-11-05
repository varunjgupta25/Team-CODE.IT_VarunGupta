import React, { useState, useEffect, useRef } from 'react';
import { MapContainer, TileLayer, Marker, Polyline, useMap } from 'react-leaflet';
import L from 'leaflet';
import { api } from '../../api';
import { calcDistanceKm, calcEtaMinutes } from '../../lib/utils';
import { AlertCircle, Clock } from 'lucide-react';

// Custom Worker Icon
const createWorkerPin = () => {
  return L.divIcon({
    className: 'custom-worker-pin',
    html: `
      <div style="
        display: flex;
        align-items: center;
        justify-content: center;
        width: 36px;
        height: 36px;
        background: #10b981;
        color: white;
        border-radius: 50%;
        box-shadow: 0 4px 14px rgba(16,185,129,0.5);
        border: 2px solid white;
      ">
        <svg style="width: 18px; height: 18px;" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
          <polygon points="3 11 22 2 13 21 11 13 3 11"></polygon>
        </svg>
      </div>
    `,
    iconSize: [36, 36],
    iconAnchor: [18, 18],
  });
};

// Custom Customer Destination Icon
const createCustomerPin = () => {
  return L.divIcon({
    className: 'custom-customer-pin',
    html: `
      <div style="
        display: flex;
        align-items: center;
        justify-content: center;
        width: 36px;
        height: 36px;
        background: #2563eb;
        color: white;
        border-radius: 50% 50% 50% 0;
        transform: rotate(-45deg) translate(-25%, -25%);
        box-shadow: 0 4px 14px rgba(37,99,235,0.45);
        border: 2px solid white;
      ">
        <svg style="transform: rotate(45deg); width: 16px; height: 16px;" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
          <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path>
          <polyline points="9 22 9 12 15 12 15 22"></polyline>
        </svg>
      </div>
    `,
    iconSize: [36, 36],
    iconAnchor: [18, 36],
  });
};

// Dynamically auto-fit map view to contain both markers & polyline
function FitBoundsToRoute({ bounds }) {
  const map = useMap();
  useEffect(() => {
    if (bounds && bounds.length >= 2) {
      try {
        map.fitBounds(bounds, { padding: [35, 35], maxZoom: 16 });
      } catch {
        // Ignore zoom race conditions
      }
    }
  }, [map, bounds]);
  return null;
}

export function RouteMap({
  jobId,
  workerId,
  workerLocation,
  customerLocation,
  pollInterval = 5000,
  height = '240px',
}) {
  const defaultWorkerLat = workerLocation?.lat || 19.2812;
  const defaultWorkerLng = workerLocation?.lng || 72.8697;
  const defaultCustLat = customerLocation?.lat || 19.2825;
  const defaultCustLng = customerLocation?.lng || 72.8570;

  const [polyline, setPolyline] = useState([
    [defaultWorkerLat, defaultWorkerLng],
    [defaultCustLat, defaultCustLng],
  ]);
  const [distanceKm, setDistanceKm] = useState(() => {
    const d = calcDistanceKm(defaultWorkerLat, defaultWorkerLng, defaultCustLat, defaultCustLng);
    return Math.round(d * 10) / 10;
  });
  const [etaMinutes, setEtaMinutes] = useState(() => {
    const d = calcDistanceKm(defaultWorkerLat, defaultWorkerLng, defaultCustLat, defaultCustLng);
    return Math.round(calcEtaMinutes(d));
  });
  const [isApproximate, setIsApproximate] = useState(false);
  const isMountedRef = useRef(true);

  useEffect(() => {
    isMountedRef.current = true;

    const fetchRoute = async () => {
      if (!jobId || !workerId) return;

      try {
        const data = await api.getRoute(jobId, workerId);
        if (!isMountedRef.current) return;

        if (data && Array.isArray(data.polyline) && data.polyline.length > 0) {
          setPolyline(data.polyline);
          if (typeof data.distanceKm === 'number') {
            setDistanceKm(data.distanceKm);
          }
          if (typeof data.etaMinutes === 'number') {
            setEtaMinutes(data.etaMinutes);
          }
          setIsApproximate(false);
        } else {
          // Graceful fallback if polyline empty
          setPolyline([
            [defaultWorkerLat, defaultWorkerLng],
            [defaultCustLat, defaultCustLng],
          ]);
          setIsApproximate(true);
        }
      } catch {
        // Backend returned 404 or road graph absent -> fallback gracefully to straight dashed line
        if (!isMountedRef.current) return;
        setPolyline([
          [defaultWorkerLat, defaultWorkerLng],
          [defaultCustLat, defaultCustLng],
        ]);
        const dist = calcDistanceKm(defaultWorkerLat, defaultWorkerLng, defaultCustLat, defaultCustLng);
        setDistanceKm(Math.round(dist * 10) / 10);
        setEtaMinutes(Math.round(calcEtaMinutes(dist)));
        setIsApproximate(true);
      }
    };

    fetchRoute();

    const timer = setInterval(fetchRoute, pollInterval);

    return () => {
      isMountedRef.current = false;
      clearInterval(timer);
    };
  }, [jobId, workerId, defaultWorkerLat, defaultWorkerLng, defaultCustLat, defaultCustLng, pollInterval]);

  const bounds = [
    [defaultWorkerLat, defaultWorkerLng],
    [defaultCustLat, defaultCustLng],
  ];

  return (
    <div className="relative w-full rounded-2xl overflow-hidden border border-slate-200 shadow-sm" style={{ height }}>
      <MapContainer
        center={[defaultWorkerLat, defaultWorkerLng]}
        zoom={14}
        scrollWheelZoom={false}
        className="w-full h-full z-0"
        attributionControl={false}
      >
        <TileLayer
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          maxZoom={19}
        />

        <FitBoundsToRoute bounds={bounds} />

        {/* Worker Marker */}
        <Marker
          position={[defaultWorkerLat, defaultWorkerLng]}
          icon={createWorkerPin()}
        />

        {/* Customer Destination Marker */}
        <Marker
          position={[defaultCustLat, defaultCustLng]}
          icon={createCustomerPin()}
        />

        {/* Route Polyline (Solid for OSM road route, Dashed for approximate straight fallback) */}
        <Polyline
          positions={polyline}
          pathOptions={
            isApproximate
              ? { color: '#3b82f6', weight: 4, opacity: 0.8, dashArray: '6, 8' }
              : { color: '#2563eb', weight: 5, opacity: 0.9 }
          }
        />
      </MapContainer>

      {/* Floating ETA & Distance Pill */}
      <div className="absolute top-2.5 left-2.5 right-2.5 z-[1000] flex items-center justify-between pointer-events-none">
        <div className="bg-white/95 backdrop-blur-md px-3 py-1.5 rounded-full shadow-md border border-slate-200/80 flex items-center gap-2 text-xs font-bold text-slate-800">
          <span className="flex items-center gap-1 text-brand-600">
            <Clock className="w-3.5 h-3.5" />
            <span>~{etaMinutes} mins</span>
          </span>
          <span className="text-slate-300">•</span>
          <span className="text-slate-600 font-semibold">{distanceKm} km</span>
        </div>

        {isApproximate && (
          <div className="bg-amber-50/95 backdrop-blur-md px-2.5 py-1 rounded-full shadow-sm border border-amber-200 flex items-center gap-1 text-[10px] font-bold text-amber-800">
            <AlertCircle className="w-3 h-3 text-amber-600" />
            <span>Approximate route</span>
          </div>
        )}
      </div>

      {/* Legend at bottom */}
      <div className="absolute bottom-2 left-2 z-[1000] bg-white/90 backdrop-blur-sm px-2 py-1 rounded-lg shadow-sm border border-slate-200/60 text-[10px] font-semibold text-slate-600 flex items-center gap-3">
        <span className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-emerald-500 inline-block" /> Worker
        </span>
        <span className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-blue-600 inline-block" /> Customer
        </span>
      </div>
    </div>
  );
}
