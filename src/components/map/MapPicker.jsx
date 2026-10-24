import React, { useState, useEffect } from 'react';
import { MapContainer, TileLayer, Marker, useMapEvents, useMap } from 'react-leaflet';
import L from 'leaflet';
import { MapPin, Navigation, Crosshair } from 'lucide-react';
import { DEFAULT_COORDINATES } from '../../types';

// Custom clean SVG pin for Leaflet
const createCustomPin = () => {
  return L.divIcon({
    className: 'custom-leaflet-pin',
    html: `
      <div style="
        display: flex;
        align-items: center;
        justify-content: center;
        width: 38px;
        height: 38px;
        background: #2563eb;
        color: white;
        border-radius: 50% 50% 50% 0;
        transform: rotate(-45deg) translate(-50%, -50%);
        box-shadow: 0 4px 12px rgba(37,99,235,0.4);
        border: 2px solid white;
      ">
        <svg style="transform: rotate(45deg); width: 18px; height: 18px;" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
          <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path>
          <circle cx="12" cy="10" r="3"></circle>
        </svg>
      </div>
    `,
    iconSize: [38, 38],
    iconAnchor: [19, 38],
  });
};

// Preset locations in Mira Road for rapid demo selection
const MIRA_ROAD_PRESETS = [
  { name: 'Shanti Park', lat: 19.2812, lng: 72.8697, address: 'B-402, Shanti Park, Mira Road East' },
  { name: 'Kanakia', lat: 19.2895, lng: 72.8720, address: 'Near Cinemax, Kanakia Road, Mira Road East' },
  { name: 'Poonam Sagar', lat: 19.2830, lng: 72.8640, address: 'Poonam Sagar Complex, Mira Road' },
  { name: 'Station East', lat: 19.2805, lng: 72.8600, address: 'Near Railway Station East, Mira Road' },
];

function LocationMarker({ position, setPosition, onAddressChange }) {
  const map = useMapEvents({
    click(e) {
      const newPos = { lat: e.latlng.lat, lng: e.latlng.lng };
      setPosition(newPos);
      map.flyTo(e.latlng, map.getZoom());
      if (onAddressChange) {
        onAddressChange(`Pin Location: Mira Road (${newPos.lat.toFixed(4)}, ${newPos.lng.toFixed(4)})`);
      }
    },
  });

  return position === null ? null : (
    <Marker
      position={[position.lat, position.lng]}
      icon={createCustomPin()}
      draggable={true}
      eventHandlers={{
        dragend(e) {
          const marker = e.target;
          const latlng = marker.getLatLng();
          const newPos = { lat: latlng.lat, lng: latlng.lng };
          setPosition(newPos);
          if (onAddressChange) {
            onAddressChange(`Pinned at (${newPos.lat.toFixed(4)}, ${newPos.lng.toFixed(4)})`);
          }
        },
      }}
    />
  );
}

function RecenterMap({ position }) {
  const map = useMap();
  useEffect(() => {
    if (position) {
      map.flyTo([position.lat, position.lng], 15);
    }
  }, [position, map]);
  return null;
}

export function MapPicker({ value, onChange, address, onAddressChange }) {
  const [position, setPosition] = useState(value || DEFAULT_COORDINATES);

  const handleSelectPreset = (preset) => {
    const newPos = { lat: preset.lat, lng: preset.lng };
    setPosition(newPos);
    if (onChange) onChange(newPos);
    if (onAddressChange) onAddressChange(preset.address);
  };

  const handlePosChange = (pos) => {
    setPosition(pos);
    if (onChange) onChange(pos);
  };

  return (
    <div className="space-y-2">
      {/* Quick preset selector for judges and presentation */}
      <div className="flex items-center gap-1.5 overflow-x-auto no-scrollbar py-1">
        <span className="text-[11px] font-bold text-slate-500 shrink-0">Quick presets:</span>
        {MIRA_ROAD_PRESETS.map((p) => (
          <button
            key={p.name}
            type="button"
            onClick={() => handleSelectPreset(p)}
            className="px-2.5 py-1 rounded-lg text-[11px] font-semibold bg-white border border-slate-200 text-slate-700 hover:bg-slate-50 shrink-0 active:scale-95 transition"
          >
            {p.name}
          </button>
        ))}
      </div>

      {/* Interactive Map Box */}
      <div className="relative w-full h-44 rounded-2xl overflow-hidden border-2 border-slate-200 shadow-inner">
        <MapContainer
          center={[position.lat, position.lng]}
          zoom={15}
          scrollWheelZoom={false}
          className="w-full h-full"
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          <LocationMarker
            position={position}
            setPosition={handlePosChange}
            onAddressChange={onAddressChange}
          />
          <RecenterMap position={position} />
        </MapContainer>

        {/* Floating guidance helper */}
        <div className="absolute bottom-2 left-2 right-2 pointer-events-none z-[1000] flex justify-between items-center">
          <div className="bg-slate-900/85 backdrop-blur-sm text-white px-2.5 py-1 rounded-full text-[10px] font-medium shadow">
            Tap map or drag pin to adjust location
          </div>
        </div>
      </div>
    </div>
  );
}
