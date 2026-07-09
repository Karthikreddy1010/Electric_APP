import { useState, useEffect } from 'react';

interface TooltipData {
  label: string;
  sub: string;
  value: string;
}

const TOOLTIPS: Record<string, TooltipData> = {
  plant:      { label: 'Generation Source',     sub: 'PSE&G Fossil Fuel Plant',        value: '12,400 MW capacity' },
  tower:      { label: 'Power Delivery',         sub: '138 kV Transmission Line',       value: 'PJM Interconnection' },
  substation: { label: 'Distribution Network',   sub: 'Zone NJ-2 Substation',           value: '3 transformers active' },
  solar:      { label: 'Solar Generation',       sub: 'Rooftop PV System',              value: '4.2 kWh generated today' },
  meter:      { label: 'Current Consumption',    sub: 'Smart Meter · PSEG-9876543',     value: '750 kWh / month · $0.1852/kWh' },
  weather:    { label: 'Weather Impact',         sub: 'CDD Analysis · NJ Zone',         value: 'CDD +12 vs. seasonal baseline' },
};

interface HoverZone { id: string; x: number; y: number; w: number; h: number; }
const HOVER_ZONES: HoverZone[] = [
  { id: 'plant',      x: 10,  y: 185, w: 115, h: 140 },
  { id: 'tower',      x: 155, y: 100, w: 155, h: 225 },
  { id: 'substation', x: 330, y: 210, w: 100, h: 100 },
  { id: 'solar',      x: 498, y: 198, w: 75,  h: 60  },
  { id: 'meter',      x: 603, y: 272, w: 22,  h: 28  },
];

/** Main SVG illustration: Power Plant → Transmission → Substation → Distribution → Smart Home */
const EnergyNetworkSVG = () => {
  const [hovered, setHovered] = useState<string | null>(null);
  const [energized, setEnergized] = useState(false);

  // Staggered energize on mount
  useEffect(() => {
    const t = setTimeout(() => setEnergized(true), 400);
    return () => clearTimeout(t);
  }, []);

  const tip = hovered ? TOOLTIPS[hovered] : null;

  return (
    <div className="relative w-full select-none" style={{ aspectRatio: '640/370' }}>
      {/* Floating tooltip */}
      {tip && (
        <div
          className="absolute top-2 left-1/2 -translate-x-1/2 z-30 pointer-events-none"
          style={{ filter: 'drop-shadow(0 4px 12px rgba(0,0,0,0.15))' }}
        >
          <div className="bg-[#18212F] text-white rounded-md px-3 py-2 text-xs whitespace-nowrap">
            <div className="font-bold text-[11px]">{tip.label}</div>
            <div className="text-[9px] text-slate-400 mt-0.5">{tip.sub}</div>
            <div className="text-primary-blue font-mono font-bold text-[10px] mt-1">{tip.value}</div>
          </div>
        </div>
      )}

      <svg
        viewBox="0 0 640 370"
        xmlns="http://www.w3.org/2000/svg"
        className="w-full h-full"
        aria-label="Energy network: power plant through transmission lines to your smart home and ElectricAI"
        role="img"
      >
        <defs>
          <linearGradient id="env-sky" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#E9F0FB" />
            <stop offset="100%" stopColor="#F4F7FC" />
          </linearGradient>
          <linearGradient id="env-ground" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#DDE3EC" />
            <stop offset="100%" stopColor="#C8D0DD" />
          </linearGradient>
          <linearGradient id="env-house-wall" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#FFFFFF" />
            <stop offset="100%" stopColor="#F0F4FA" />
          </linearGradient>
          <linearGradient id="env-meter-screen" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#0EA5E9" />
            <stop offset="100%" stopColor="#2563EB" />
          </linearGradient>
          <linearGradient id="env-roof" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="#1E293B" />
            <stop offset="100%" stopColor="#0F172A" />
          </linearGradient>
          <filter id="env-glow" x="-30%" y="-30%" width="160%" height="160%">
            <feGaussianBlur in="SourceGraphic" stdDeviation="2.5" result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
          </filter>
          <filter id="env-subtle-shadow" x="-10%" y="-10%" width="120%" height="130%">
            <feDropShadow dx="0" dy="2" stdDeviation="3" floodColor="#00000018" />
          </filter>
          <style>{`
            .env-energy { animation: env-particle-flow 2s linear infinite; }
            .env-energy-d1 { animation-delay: 0.4s; }
            .env-energy-d2 { animation-delay: 0.8s; }
            .env-energy-d3 { animation-delay: 1.2s; }
            .env-energy-d4 { animation-delay: 1.6s; }
            @keyframes env-particle-flow {
              0%   { stroke-dashoffset: 80; opacity: 0; }
              8%   { opacity: 1; }
              88%  { opacity: 1; }
              100% { stroke-dashoffset: 0; opacity: 0; }
            }
            @keyframes env-steam {
              0%   { transform: translateY(0px) scale(1);   opacity: 0.55; }
              60%  { transform: translateY(-14px) scale(1.5); opacity: 0.2; }
              100% { transform: translateY(-26px) scale(0.7); opacity: 0; }
            }
            .env-steam-a { animation: env-steam 3.6s ease-out infinite; }
            .env-steam-b { animation: env-steam 3.6s ease-out infinite; animation-delay: 1.2s; }
            .env-steam-c { animation: env-steam 3.6s ease-out infinite; animation-delay: 2.4s; }
            @keyframes env-meter-led {
              0%, 100% { r: 3; opacity: 1; }
              50%       { r: 4.5; opacity: 0.6; }
            }
            .env-meter-led { animation: env-meter-led 1.8s ease-in-out infinite; }
            @keyframes env-solar-shimmer {
              0%, 100% { opacity: 0.75; }
              50%       { opacity: 1; }
            }
            .env-solar-panel { animation: env-solar-shimmer 2.8s ease-in-out infinite; }
            .env-solar-panel-b { animation: env-solar-shimmer 2.8s ease-in-out infinite; animation-delay: 0.7s; }
            .env-solar-panel-c { animation: env-solar-shimmer 2.8s ease-in-out infinite; animation-delay: 1.4s; }
            @keyframes env-data-pulse {
              0%, 100% { opacity: 0.4; }
              50%       { opacity: 1; }
            }
            .env-data-dot { animation: env-data-pulse 2s ease-in-out infinite; }
          `}</style>
        </defs>

        {/* ── Background ───────────────────────────────────────────── */}
        <rect width="640" height="370" fill="url(#env-sky)" />

        {/* Ground plane */}
        <rect x="0" y="322" width="640" height="48" fill="url(#env-ground)" />
        <line x1="0" y1="322" x2="640" y2="322" stroke="#C8D0DD" strokeWidth="1" />

        {/* ── Power Plant ──────────────────────────────────────────── */}
        {/* Base building */}
        <rect x="18" y="252" width="98" height="72" fill="#536171" rx="2" filter="url(#env-subtle-shadow)" />
        {/* Building windows (3 rows) */}
        <rect x="24" y="258" width="18" height="12" fill="#6B7E94" rx="1" opacity="0.7" />
        <rect x="47" y="258" width="18" height="12" fill="#6B7E94" rx="1" opacity="0.7" />
        <rect x="70" y="258" width="18" height="12" fill="#6B7E94" rx="1" opacity="0.7" />
        <rect x="24" y="277" width="18" height="12" fill="#6B7E94" rx="1" opacity="0.5" />
        <rect x="47" y="277" width="18" height="12" fill="#6B7E94" rx="1" opacity="0.5" />
        <rect x="70" y="277" width="18" height="12" fill="#6B7E94" rx="1" opacity="0.5" />
        {/* Plant top strip */}
        <rect x="18" y="248" width="98" height="6" fill="#3D4F60" rx="1" />
        {/* Main chimney */}
        <rect x="85" y="192" width="11" height="62" fill="#374151" rx="1" />
        <rect x="83" y="190" width="15" height="5" fill="#2E3A47" rx="1" />

        {/* Cooling tower 1 */}
        <path d="M 21,322 L 37,212 L 54,212 L 66,322 Z" fill="#4B5E6E" stroke="#5E7385" strokeWidth="0.8" />
        <path d="M 28,322 Q 43,268 55,322" fill="#3D4E5E" opacity="0.5" />
        {/* Rim at top */}
        <ellipse cx="43" cy="212" rx="8.5" ry="3" fill="#3D4E5E" stroke="#6B7E94" strokeWidth="0.6" />

        {/* Cooling tower 2 */}
        <path d="M 55,322 L 67,217 L 84,217 L 98,322 Z" fill="#4B5E6E" stroke="#5E7385" strokeWidth="0.8" />
        <path d="M 62,322 Q 75,272 88,322" fill="#3D4E5E" opacity="0.5" />
        <ellipse cx="76" cy="217" rx="8.5" ry="3" fill="#3D4E5E" stroke="#6B7E94" strokeWidth="0.6" />

        {/* Steam wisps */}
        <g className="env-steam-a" style={{ transformOrigin: '43px 210px' }}>
          <ellipse cx="43" cy="208" rx="7" ry="3.5" fill="white" opacity="0.55" />
        </g>
        <g className="env-steam-b" style={{ transformOrigin: '76px 215px' }}>
          <ellipse cx="76" cy="213" rx="6" ry="3" fill="white" opacity="0.45" />
        </g>
        <g className="env-steam-c" style={{ transformOrigin: '91px 189px' }}>
          <ellipse cx="91" cy="187" rx="4.5" ry="2.5" fill="white" opacity="0.4" />
        </g>

        {/* Ground shadow */}
        <ellipse cx="68" cy="324" rx="56" ry="4" fill="#9DADC0" opacity="0.35" />

        {/* ── Cable: Plant → Tower 1 ───────────────────────────────── */}
        {/* Two conductor lines */}
        <path d="M 112,240 Q 148,256 165,245" fill="none" stroke="#94A3B8" strokeWidth="0.9" />
        <path d="M 112,248 Q 148,263 165,252" fill="none" stroke="#94A3B8" strokeWidth="0.9" />
        {energized && (
          <>
            <path d="M 112,240 Q 148,256 165,245" fill="none" stroke="#2F6BFF" strokeWidth="2"
              strokeDasharray="10 14" className="env-energy" filter="url(#env-glow)" />
            <path d="M 112,248 Q 148,263 165,252" fill="none" stroke="#2CA6FF" strokeWidth="1.5"
              strokeDasharray="10 14" className="env-energy env-energy-d2" filter="url(#env-glow)" />
          </>
        )}

        {/* ── Transmission Tower 1 ─────────────────────────────────── */}
        {/* Legs splayed at base */}
        <line x1="188" y1="272" x2="168" y2="322" stroke="#475569" strokeWidth="3" strokeLinecap="round" />
        <line x1="188" y1="272" x2="208" y2="322" stroke="#475569" strokeWidth="3" strokeLinecap="round" />
        {/* Body */}
        <line x1="188" y1="140" x2="188" y2="272" stroke="#475569" strokeWidth="2.5" strokeLinecap="round" />
        {/* Lateral braces */}
        <line x1="172" y1="220" x2="188" y2="185" stroke="#475569" strokeWidth="1.8" />
        <line x1="204" y1="220" x2="188" y2="185" stroke="#475569" strokeWidth="1.8" />
        <line x1="172" y1="272" x2="188" y2="220" stroke="#475569" strokeWidth="1.8" />
        <line x1="204" y1="272" x2="188" y2="220" stroke="#475569" strokeWidth="1.8" />
        {/* Upper cross arm */}
        <line x1="158" y1="155" x2="218" y2="155" stroke="#475569" strokeWidth="2.2" strokeLinecap="round" />
        {/* Lower cross arm */}
        <line x1="163" y1="180" x2="213" y2="180" stroke="#475569" strokeWidth="2" strokeLinecap="round" />
        {/* Insulator chains */}
        <line x1="158" y1="155" x2="162" y2="168" stroke="#94A3B8" strokeWidth="1" />
        <line x1="188" y1="155" x2="188" y2="168" stroke="#94A3B8" strokeWidth="1" />
        <line x1="218" y1="155" x2="214" y2="168" stroke="#94A3B8" strokeWidth="1" />
        {/* Peak */}
        <line x1="182" y1="140" x2="194" y2="140" stroke="#475569" strokeWidth="2" />
        <line x1="188" y1="128" x2="188" y2="140" stroke="#475569" strokeWidth="2" />
        {/* Ground shadow */}
        <ellipse cx="188" cy="324" rx="22" ry="3" fill="#9DADC0" opacity="0.3" />

        {/* ── HV Lines: Tower 1 → Tower 2 ─────────────────────────── */}
        <path d="M 158,168 Q 225,178 260,168" fill="none" stroke="#94A3B8" strokeWidth="0.9" />
        <path d="M 188,168 Q 225,181 278,168" fill="none" stroke="#94A3B8" strokeWidth="0.9" />
        <path d="M 218,168 Q 225,178 260,168" fill="none" stroke="#94A3B8" strokeWidth="0.9" />
        {energized && (
          <>
            <path d="M 158,168 Q 225,178 260,168" fill="none" stroke="#2F6BFF" strokeWidth="2"
              strokeDasharray="10 14" className="env-energy env-energy-d1" filter="url(#env-glow)" />
            <path d="M 218,168 Q 225,178 260,168" fill="none" stroke="#2CA6FF" strokeWidth="1.5"
              strokeDasharray="10 14" className="env-energy env-energy-d3" filter="url(#env-glow)" />
          </>
        )}

        {/* ── Transmission Tower 2 ─────────────────────────────────── */}
        <line x1="288" y1="272" x2="268" y2="322" stroke="#475569" strokeWidth="3" strokeLinecap="round" />
        <line x1="288" y1="272" x2="308" y2="322" stroke="#475569" strokeWidth="3" strokeLinecap="round" />
        <line x1="288" y1="143" x2="288" y2="272" stroke="#475569" strokeWidth="2.5" strokeLinecap="round" />
        <line x1="272" y1="220" x2="288" y2="185" stroke="#475569" strokeWidth="1.8" />
        <line x1="304" y1="220" x2="288" y2="185" stroke="#475569" strokeWidth="1.8" />
        <line x1="272" y1="272" x2="288" y2="220" stroke="#475569" strokeWidth="1.8" />
        <line x1="304" y1="272" x2="288" y2="220" stroke="#475569" strokeWidth="1.8" />
        <line x1="258" y1="158" x2="318" y2="158" stroke="#475569" strokeWidth="2.2" strokeLinecap="round" />
        <line x1="263" y1="182" x2="313" y2="182" stroke="#475569" strokeWidth="2" strokeLinecap="round" />
        <line x1="258" y1="158" x2="262" y2="172" stroke="#94A3B8" strokeWidth="1" />
        <line x1="288" y1="158" x2="288" y2="172" stroke="#94A3B8" strokeWidth="1" />
        <line x1="318" y1="158" x2="314" y2="172" stroke="#94A3B8" strokeWidth="1" />
        <line x1="282" y1="143" x2="294" y2="143" stroke="#475569" strokeWidth="2" />
        <line x1="288" y1="131" x2="288" y2="143" stroke="#475569" strokeWidth="2" />
        <ellipse cx="288" cy="324" rx="22" ry="3" fill="#9DADC0" opacity="0.3" />

        {/* ── Lines: Tower 2 → Substation ─────────────────────────── */}
        <path d="M 258,172 Q 318,188 352,218" fill="none" stroke="#94A3B8" strokeWidth="0.9" />
        <path d="M 288,172 Q 320,190 352,224" fill="none" stroke="#94A3B8" strokeWidth="0.9" />
        {energized && (
          <path d="M 258,172 Q 318,188 352,218" fill="none" stroke="#2F6BFF" strokeWidth="2"
            strokeDasharray="10 14" className="env-energy env-energy-d2" filter="url(#env-glow)" />
        )}

        {/* ── Substation ───────────────────────────────────────────── */}
        <rect x="344" y="215" width="96" height="78" fill="#EFF2F8" stroke="#94A3B8" strokeWidth="1" rx="3"
          filter="url(#env-subtle-shadow)" />
        {/* Internal equipment row */}
        <rect x="350" y="220" width="84" height="6" fill="#CBD5E1" rx="1" />
        {/* Transformer 1 */}
        <ellipse cx="368" cy="234" rx="9" ry="5" fill="#536171" stroke="#475569" strokeWidth="0.8" />
        <rect x="359" y="234" width="18" height="28" fill="#536171" stroke="#475569" strokeWidth="0.8" />
        <ellipse cx="368" cy="262" rx="9" ry="5" fill="#3D4E5E" stroke="#475569" strokeWidth="0.8" />
        {/* Transformer 2 */}
        <ellipse cx="393" cy="234" rx="9" ry="5" fill="#536171" stroke="#475569" strokeWidth="0.8" />
        <rect x="384" y="234" width="18" height="28" fill="#536171" stroke="#475569" strokeWidth="0.8" />
        <ellipse cx="393" cy="262" rx="9" ry="5" fill="#3D4E5E" stroke="#475569" strokeWidth="0.8" />
        {/* Bus bar and switchgear */}
        <rect x="350" y="272" width="84" height="8" fill="#94A3B8" rx="1" />
        <line x1="360" y1="265" x2="360" y2="280" stroke="#475569" strokeWidth="1.5" />
        <line x1="380" y1="265" x2="380" y2="280" stroke="#475569" strokeWidth="1.5" />
        <line x1="400" y1="265" x2="400" y2="280" stroke="#475569" strokeWidth="1.5" />
        {/* Ground shadow */}
        <ellipse cx="392" cy="325" rx="52" ry="4" fill="#9DADC0" opacity="0.28" />

        {/* ── Line: Substation → Distribution Pole ─────────────────── */}
        <path d="M 430,232 L 454,198" fill="none" stroke="#94A3B8" strokeWidth="1" />
        {energized && (
          <path d="M 430,232 L 454,198" fill="none" stroke="#2F6BFF" strokeWidth="2"
            strokeDasharray="10 14" className="env-energy env-energy-d3" filter="url(#env-glow)" />
        )}

        {/* ── Distribution Pole ─────────────────────────────────────── */}
        <line x1="456" y1="322" x2="456" y2="172" stroke="#6B7280" strokeWidth="3.5" strokeLinecap="round" />
        {/* Cross arm */}
        <line x1="434" y1="188" x2="478" y2="188" stroke="#4B5563" strokeWidth="2.8" strokeLinecap="round" />
        {/* Transformer drum */}
        <ellipse cx="456" cy="213" rx="9" ry="5" fill="#4B5563" stroke="#374151" strokeWidth="0.8" />
        <rect x="447" y="213" width="18" height="20" fill="#4B5563" stroke="#374151" strokeWidth="0.8" />
        <ellipse cx="456" cy="233" rx="9" ry="5" fill="#374151" stroke="#374151" strokeWidth="0.8" />
        {/* Insulators */}
        <line x1="434" y1="188" x2="434" y2="200" stroke="#94A3B8" strokeWidth="1" />
        <line x1="456" y1="188" x2="456" y2="200" stroke="#94A3B8" strokeWidth="1" />
        <line x1="478" y1="188" x2="478" y2="200" stroke="#94A3B8" strokeWidth="1" />
        <ellipse cx="456" cy="324" rx="18" ry="3" fill="#9DADC0" opacity="0.3" />

        {/* Small decorative tree */}
        <line x1="148" y1="322" x2="148" y2="292" stroke="#94A3B8" strokeWidth="1.8" />
        <circle cx="148" cy="283" r="11" fill="#34D399" opacity="0.28" />
        <circle cx="148" cy="283" r="7" fill="#10B981" opacity="0.36" />

        {/* ── Line: Pole → House ────────────────────────────────────── */}
        <path d="M 470,194 L 510,242" fill="none" stroke="#94A3B8" strokeWidth="1" />
        {energized && (
          <path d="M 470,194 L 510,242" fill="none" stroke="#2F6BFF" strokeWidth="2"
            strokeDasharray="10 14" className="env-energy env-energy-d4" filter="url(#env-glow)" />
        )}

        {/* ── Smart Home ────────────────────────────────────────────── */}
        {/* House roof */}
        <polygon points="500,264 558,210 616,264" fill="url(#env-roof)" filter="url(#env-subtle-shadow)" />
        {/* Roof ridge shadow */}
        <polygon points="500,264 558,210 558,264" fill="#0A0F1A" opacity="0.18" />

        {/* Solar panels on left roof slope */}
        <g className="env-solar-panel" onMouseEnter={() => setHovered('solar')} onMouseLeave={() => setHovered(null)}
           style={{ cursor: 'pointer' }}>
          {/* Panel 1 */}
          <polygon points="507,254 522,238 537,248 522,264" fill="#1D4ED8" stroke="#3B82F6" strokeWidth="0.6" opacity="0.92" />
          <line x1="514" y1="246" x2="529" y2="256" stroke="#93C5FD" strokeWidth="0.5" opacity="0.7" />
          <line x1="517" y1="242" x2="532" y2="252" stroke="#93C5FD" strokeWidth="0.5" opacity="0.7" />
          <line x1="515" y1="252" x2="522" y2="246" stroke="#93C5FD" strokeWidth="0.4" opacity="0.5" />
        </g>
        <g className="env-solar-panel-b" onMouseEnter={() => setHovered('solar')} onMouseLeave={() => setHovered(null)}
           style={{ cursor: 'pointer' }}>
          {/* Panel 2 */}
          <polygon points="522,258 537,242 552,252 537,268" fill="#1D4ED8" stroke="#3B82F6" strokeWidth="0.6" opacity="0.92" />
          <line x1="529" y1="250" x2="544" y2="260" stroke="#93C5FD" strokeWidth="0.5" opacity="0.7" />
          <line x1="532" y1="246" x2="547" y2="256" stroke="#93C5FD" strokeWidth="0.5" opacity="0.7" />
          <line x1="530" y1="256" x2="537" y2="250" stroke="#93C5FD" strokeWidth="0.4" opacity="0.5" />
        </g>
        <g className="env-solar-panel-c" onMouseEnter={() => setHovered('solar')} onMouseLeave={() => setHovered(null)}
           style={{ cursor: 'pointer' }}>
          {/* Panel 3 */}
          <polygon points="537,262 552,246 567,256 552,272" fill="#1D4ED8" stroke="#3B82F6" strokeWidth="0.6" opacity="0.92" />
          <line x1="544" y1="254" x2="559" y2="264" stroke="#93C5FD" strokeWidth="0.5" opacity="0.7" />
          <line x1="547" y1="250" x2="562" y2="260" stroke="#93C5FD" strokeWidth="0.5" opacity="0.7" />
        </g>

        {/* Walls */}
        <rect x="503" y="264" width="110" height="60" fill="url(#env-house-wall)" stroke="#CBD5E1" strokeWidth="1"
          filter="url(#env-subtle-shadow)" />

        {/* Left window */}
        <rect x="511" y="273" width="24" height="20" fill="#BFDBFE" stroke="#94A3B8" strokeWidth="0.6" rx="1" />
        <line x1="523" y1="273" x2="523" y2="293" stroke="#94A3B8" strokeWidth="0.5" />
        <line x1="511" y1="283" x2="535" y2="283" stroke="#94A3B8" strokeWidth="0.5" />

        {/* Right window */}
        <rect x="574" y="273" width="24" height="20" fill="#BFDBFE" stroke="#94A3B8" strokeWidth="0.6" rx="1" />
        <line x1="586" y1="273" x2="586" y2="293" stroke="#94A3B8" strokeWidth="0.5" />
        <line x1="574" y1="283" x2="598" y2="283" stroke="#94A3B8" strokeWidth="0.5" />

        {/* Door */}
        <rect x="547" y="294" width="22" height="30" fill="#D1D5DB" stroke="#9CA3AF" strokeWidth="0.6" rx="1" />
        <circle cx="566" cy="309" r="1.8" fill="#9CA3AF" />

        {/* Smart Meter box */}
        <rect x="605" y="272" width="14" height="24" fill="#1E293B" stroke="#334155" strokeWidth="0.6" rx="1"
          onMouseEnter={() => setHovered('meter')} onMouseLeave={() => setHovered(null)}
          style={{ cursor: 'pointer' }} />
        <rect x="606" y="274" width="12" height="11" fill="url(#env-meter-screen)" rx="1" opacity="0.9" />
        {/* Meter LED */}
        <circle
          className="env-meter-led"
          cx="612" cy="291" r="3" fill="#2F6BFF"
          filter="url(#env-glow)"
          onMouseEnter={() => setHovered('meter')}
          onMouseLeave={() => setHovered(null)}
          style={{ cursor: 'pointer' }}
        />

        {/* Ground shadow house */}
        <ellipse cx="558" cy="326" rx="60" ry="5" fill="#9DADC0" opacity="0.4" />

        {/* Small tree beside house */}
        <line x1="494" y1="322" x2="494" y2="295" stroke="#94A3B8" strokeWidth="1.8" />
        <circle cx="494" cy="286" r="10" fill="#34D399" opacity="0.28" />
        <circle cx="494" cy="286" r="6.5" fill="#10B981" opacity="0.35" />

        {/* ── Data connection to ElectricAI ─────────────────────────── */}
        <line x1="612" y1="297" x2="612" y2="318" stroke="#2F6BFF" strokeWidth="1.2" strokeDasharray="3 4" opacity="0.7" />
        <circle className="env-data-dot" cx="612" cy="322" r="3.5" fill="#2F6BFF" opacity="0.5" />

        {/* ── Invisible hover zones ─────────────────────────────────── */}
        {HOVER_ZONES.filter(z => z.id !== 'solar' && z.id !== 'meter').map(z => (
          <rect key={z.id} x={z.x} y={z.y} width={z.w} height={z.h} fill="transparent"
            className="cursor-pointer"
            onMouseEnter={() => setHovered(z.id)}
            onMouseLeave={() => setHovered(null)}
          />
        ))}

        {/* ── Scene labels ─────────────────────────────────────────── */}
        {[
          { x: 67, label: 'Power Plant' },
          { x: 228, label: 'Transmission' },
          { x: 392, label: 'Substation' },
          { x: 456, label: 'Distribution' },
          { x: 558, label: 'Smart Home' },
        ].map(({ x, label }) => (
          <text key={label} x={x} y="343" fontSize="7.5" fill="#94A3B8" textAnchor="middle"
            fontFamily="Inter, sans-serif" fontWeight="500" letterSpacing="0.3">
            {label}
          </text>
        ))}

        {/* Flow arrows between labels */}
        {[137, 318, 435, 505].map(ax => (
          <text key={ax} x={ax} y="342" fontSize="7" fill="#CBD5E1" textAnchor="middle"
            fontFamily="Inter, sans-serif">→</text>
        ))}
      </svg>
    </div>
  );
};

export default EnergyNetworkSVG;
