import { useNavigation } from '../../context/NavigationContext.tsx';
import EnergyNetworkSVG from './EnergyNetworkSVG.tsx';

// ─── Circuit Background Pattern ───────────────────────────────────────────────
const CircuitBackground = () => (
  <svg
    className="absolute inset-0 w-full h-full pointer-events-none"
    xmlns="http://www.w3.org/2000/svg"
    aria-hidden="true"
  >
    <defs>
      <pattern id="circuit-grid" x="0" y="0" width="60" height="60" patternUnits="userSpaceOnUse">
        {/* Horizontal traces */}
        <path d="M0,30 L15,30 L20,25 L40,25 L45,30 L60,30" fill="none" stroke="#2F6BFF" strokeWidth="0.6" />
        {/* Vertical traces */}
        <path d="M30,0 L30,12 L35,17 L35,43 L30,48 L30,60" fill="none" stroke="#2F6BFF" strokeWidth="0.6" />
        {/* Connection nodes */}
        <circle cx="20" cy="25" r="1.5" fill="#2F6BFF" />
        <circle cx="40" cy="25" r="1.5" fill="#2F6BFF" />
        <circle cx="30" cy="17" r="1.5" fill="#2F6BFF" />
        <circle cx="30" cy="43" r="1.5" fill="#2F6BFF" />
      </pattern>
    </defs>
    <rect width="100%" height="100%" fill="url(#circuit-grid)" opacity="0.030" />
  </svg>
);

// ─── Live Electricity Widget ───────────────────────────────────────────────────
const LiveWidget = () => {
  const stats = [
    { label: 'Grid Status',     value: 'NORMAL',      unit: '',          color: 'text-savings-green', dot: true },
    { label: 'Wholesale Price', value: '$42.30',       unit: '/MWh',      color: 'text-text-primary' },
    { label: 'Temperature',     value: '72°F',         unit: 'Newark NJ', color: 'text-text-primary' },
    { label: 'Today\'s Usage',   value: '24.5',         unit: 'kWh est.',  color: 'text-primary-blue' },
    { label: 'Peak Window',     value: '4-8 PM',       unit: 'avoid',     color: 'text-warning-amber' },
  ];

  return (
    <div
      className="bg-white/90 border border-border-hairline rounded-md shadow-md p-4 w-56 space-y-3"
      style={{ backdropFilter: 'blur(8px)' }}
    >
      <div className="flex items-center justify-between border-b border-border-hairline pb-2">
        <span className="text-[9px] font-bold uppercase tracking-widest text-text-secondary">Live Grid Status</span>
        <span className="flex items-center gap-1">
          <span className="w-1.5 h-1.5 rounded-full bg-savings-green animate-pulse" />
          <span className="text-[8px] text-savings-green font-bold">LIVE</span>
        </span>
      </div>
      {stats.map(({ label, value, unit, color, dot }) => (
        <div key={label} className="flex items-center justify-between">
          <span className="text-[9px] text-text-secondary font-medium">{label}</span>
          <div className="flex items-center gap-1">
            {dot && <span className="w-1.5 h-1.5 rounded-full bg-savings-green" />}
            <span className={`text-[10px] font-bold font-mono-numbers ${color}`}>{value}</span>
            {unit && <span className="text-[8px] text-text-secondary">{unit}</span>}
          </div>
        </div>
      ))}
    </div>
  );
};

// ─── Onboarding Timeline ───────────────────────────────────────────────────────
const TimelineStep = ({ step, label, desc, isLast }: {
  step: number; label: string; desc: string; isLast?: boolean;
}) => (
  <div className="flex items-start gap-0">
    <div className="flex flex-col items-center shrink-0">
      <div
        className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold border-2 bg-white text-primary-blue border-primary-blue shadow-sm z-10"
      >
        {step}
      </div>
      {!isLast && (
        <div className="w-0.5 h-12 bg-gradient-to-b from-primary-blue/40 to-primary-blue/5 mt-1" />
      )}
    </div>
    <div className="pl-4 pt-1 pb-3">
      <div className="text-xs font-bold text-text-primary">{label}</div>
      <div className="text-[10px] text-text-secondary mt-0.5">{desc}</div>
    </div>
  </div>
);

// ─── Feature Badge ─────────────────────────────────────────────────────────────
const FeatureBadge = ({ label }: { label: string }) => (
  <div className="flex items-center gap-2 text-xs text-text-secondary">
    <div className="w-4 h-4 rounded-full bg-savings-green/15 flex items-center justify-center shrink-0">
      <svg width="8" height="8" viewBox="0 0 8 8" fill="none">
        <path d="M1.5 4L3 5.5L6.5 2.5" stroke="#27AE60" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    </div>
    <span className="font-medium">{label}</span>
  </div>
);

// ─── Onboarding Hero ─────────────────────────────────────────────────────────
const OnboardingHero = () => {
  const navigate = useNavigation();

  const handleExploreDemo = () => {
    // hasBill is already true from defaults — just navigate to Overview
    navigate('Bill Analysis');
  };

  const TIMELINE_STEPS = [
    { label: 'Upload Your Bill',       desc: 'Drag & drop any PDF or scanned electricity bill' },
    { label: 'AI Analysis',            desc: 'OCR extraction + LLM explanation in seconds' },
    { label: 'Understand Charges',     desc: 'Every line item explained in plain language' },
    { label: 'Regional Comparison',    desc: 'See how your usage stacks up against neighbors' },
    { label: 'Forecast Bills',         desc: 'Predict next month\'s bill with ML models' },
    { label: 'Save Money',             desc: 'Discover plans and behaviors that cut costs' },
  ];

  const FEATURE_BADGES = [
    'AI Bill Analysis & OCR Extraction',
    'Ensemble Bill Forecasting',
    'Regional & Geo Insights',
    'Impact & Simulation Engine',
    'Energy Plan Recommendations',
  ];

  return (
    <div className="relative min-h-screen overflow-hidden bg-[#F7F9FC]">
      {/* Circuit background at 3% opacity */}
      <CircuitBackground />

      {/* ── Main Hero Section ───────────────────────────────────────── */}
      <div className="relative z-10 max-w-7xl mx-auto px-6 pt-8 pb-6">
        <div className="grid grid-cols-1 lg:grid-cols-[45fr_55fr] gap-12 items-center min-h-[540px]">

          {/* LEFT COLUMN ─────────────────────────────────────────────── */}
          <div className="space-y-8">
            {/* Brand badge */}
            <div className="inline-flex items-center gap-2 bg-primary-blue/8 border border-primary-blue/20 text-primary-blue text-[10px] font-bold uppercase tracking-widest px-3 py-1.5 rounded-full">
              <span className="w-1.5 h-1.5 rounded-full bg-primary-blue animate-pulse" />
              AI-Powered Electricity Intelligence
            </div>

            {/* Headline */}
            <div className="space-y-1">
              <h1 className="text-4xl xl:text-5xl font-bold text-text-primary tracking-tight leading-tight font-sans">
                Understand Your
                <br />
                <span className="text-primary-blue">Electricity.</span>
              </h1>
              <h2 className="text-4xl xl:text-5xl font-bold text-text-primary tracking-tight leading-tight font-sans">
                Reduce Your
                <br />
                <span className="text-energy-teal">Bills.</span>
              </h2>
              <h2 className="text-4xl xl:text-5xl font-bold tracking-tight leading-tight font-sans text-text-secondary">
                Power Smarter
                <br />
                Decisions.
              </h2>
            </div>

            {/* Subtitle */}
            <p className="text-sm text-text-secondary leading-relaxed max-w-md font-medium">
              ElectricAI transforms your utility bill into personalized electricity intelligence.
              Understand every charge, forecast future bills, compare your home with similar households,
              and discover opportunities to save money.
            </p>

            {/* CTAs */}
            <div className="flex flex-wrap items-center gap-3">
              <button
                id="hero-cta-upload"
                onClick={() => navigate('Bill Analysis')}
                className="flex items-center gap-2 bg-primary-blue hover:bg-primary-blue/90 text-white font-bold px-6 py-3.5 rounded-md shadow-md hover:shadow-lg transition-all duration-200 text-sm active:scale-[0.98]"
              >
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                  <polyline points="17 8 12 3 7 8" />
                  <line x1="12" y1="3" x2="12" y2="15" />
                </svg>
                Upload Your First Bill
              </button>
              <button
                id="hero-cta-demo"
                onClick={handleExploreDemo}
                className="flex items-center gap-2 bg-white hover:bg-bg-primary text-text-primary font-bold px-6 py-3.5 rounded-md shadow-sm border border-border-hairline hover:border-text-secondary transition-all duration-200 text-sm"
              >
                Explore Demo →
              </button>
            </div>

            {/* Feature badges */}
            <div className="grid grid-cols-1 gap-2 pt-2">
              {FEATURE_BADGES.map(f => <FeatureBadge key={f} label={f} />)}
            </div>
          </div>

          {/* RIGHT COLUMN ────────────────────────────────────────────── */}
          <div className="relative flex flex-col gap-6">
            {/* Main illustration */}
            <div className="relative">
              <div
                className="rounded-xl border border-border-hairline overflow-hidden"
                style={{
                  background: 'linear-gradient(135deg, #EEF3FB 0%, #F4F7FC 100%)',
                  boxShadow: '0 8px 40px rgba(47,107,255,0.08), 0 2px 8px rgba(0,0,0,0.06)',
                }}
              >
                <EnergyNetworkSVG />
              </div>

              {/* Live Widget — positioned over illustration bottom-right */}
              <div className="absolute bottom-4 right-4">
                <LiveWidget />
              </div>

              {/* "Hover to explore" hint */}
              <div className="absolute top-3 left-3 flex items-center gap-1.5 bg-white/80 border border-border-hairline text-[9px] text-text-secondary font-semibold px-2.5 py-1.5 rounded-full"
                style={{ backdropFilter: 'blur(4px)' }}>
                <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                </svg>
                Hover elements to explore
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* ── Onboarding Timeline ─────────────────────────────────────── */}
      <div className="relative z-10 max-w-7xl mx-auto px-6 pb-16">
        <div
          className="rounded-xl border border-border-hairline bg-white/80 p-8"
          style={{ backdropFilter: 'blur(8px)', boxShadow: '0 2px 16px rgba(0,0,0,0.04)' }}
        >
          <div className="flex items-center gap-3 mb-8">
            <div className="w-px h-6 bg-primary-blue rounded-full" />
            <h3 className="text-xs font-bold text-text-secondary uppercase tracking-widest">
              Your journey from bill to intelligence
            </h3>
          </div>

          {/* Desktop: horizontal timeline */}
          <div className="hidden md:flex items-start justify-between gap-2">
            {TIMELINE_STEPS.map((s, i) => (
              <div key={s.label} className="flex items-start gap-0 flex-1">
                <div className="flex flex-col items-center w-full">
                  {/* Step circle */}
                  <div className="flex items-center w-full">
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold border-2 shrink-0 z-10 ${
                      i === 0 ? 'bg-primary-blue text-white border-primary-blue shadow-md shadow-primary-blue/30'
                              : 'bg-white text-primary-blue border-primary-blue/40'
                    }`}>
                      {i + 1}
                    </div>
                    {/* Connector line */}
                    {i < TIMELINE_STEPS.length - 1 && (
                      <div className="flex-1 h-0.5 bg-gradient-to-r from-primary-blue/30 to-primary-blue/10 mx-2" />
                    )}
                  </div>
                  {/* Label */}
                  <div className="mt-3 pr-4 w-full">
                    <div className="text-xs font-bold text-text-primary">{s.label}</div>
                    <div className="text-[10px] text-text-secondary mt-1 leading-tight">{s.desc}</div>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Mobile: vertical timeline */}
          <div className="flex md:hidden flex-col pl-2">
            {TIMELINE_STEPS.map((s, i) => (
              <TimelineStep
                key={s.label}
                step={i + 1}
                label={s.label}
                desc={s.desc}
                isLast={i === TIMELINE_STEPS.length - 1}
              />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default OnboardingHero;
