import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { 
  Sparkles, ShieldCheck, BarChart3, LineChart, 
  MapPin, ArrowRight, Activity, CloudSun, 
  Zap, FileText, Compass
} from 'lucide-react';

// ─── Live Energy Panel Component ──────────────────────────────────────────────
function LiveEnergyPanel() {
  const [data, setData] = useState({
    gridStatus: 'Optimal',
    wholesalePrice: 42.15,
    estimatedUsage: 14.8,
    temperature: 78,
    weather: 'Sunny',
    frequency: 60.02
  });

  useEffect(() => {
    const interval = setInterval(() => {
      setData((prev) => ({
        ...prev,
        wholesalePrice: Number((42.15 + (Math.random() - 0.5) * 4).toFixed(2)),
        estimatedUsage: Number((14.8 + (Math.random() - 0.5) * 1.5).toFixed(1)),
        frequency: Number((60.00 + (Math.random() - 0.5) * 0.05).toFixed(2)),
        temperature: prev.temperature + (Math.random() > 0.5 ? 1 : -1)
      }));
    }, 3000);
    return () => clearInterval(interval);
  }, []);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, delay: 0.2 }}
      className="p-5 rounded-lg border border-border-hairline bg-bg-surface/85 backdrop-blur-md shadow-lg max-w-sm w-full space-y-4 font-mono-numbers text-xs"
    >
      <div className="flex items-center justify-between border-b border-border-hairline pb-2.5">
        <span className="flex items-center gap-1.5 font-bold font-sans text-text-primary uppercase tracking-wider text-[10px]">
          <Activity size={12} className="text-primary-blue animate-pulse" /> Grid Telemetry Loop
        </span>
        <span className="bg-savings-green/10 text-savings-green border border-savings-green/20 px-2 py-0.5 rounded-[4px] text-[10px] font-bold">
          {data.gridStatus}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <p className="text-[9px] text-text-secondary uppercase font-sans font-bold tracking-wider mb-1">Wholesale Price</p>
          <h4 className="text-base font-bold text-text-primary">${data.wholesalePrice} <span className="text-[10px] font-normal text-text-secondary">/MWh</span></h4>
        </div>
        <div>
          <p className="text-[9px] text-text-secondary uppercase font-sans font-bold tracking-wider mb-1">Estimated Load</p>
          <h4 className="text-base font-bold text-text-primary">{data.estimatedUsage} <span className="text-[10px] font-normal text-text-secondary">kW</span></h4>
        </div>
        <div>
          <p className="text-[9px] text-text-secondary uppercase font-sans font-bold tracking-wider mb-1">Grid Frequency</p>
          <h4 className="text-base font-bold text-text-primary">{data.frequency} <span className="text-[10px] font-normal text-text-secondary">Hz</span></h4>
        </div>
        <div>
          <p className="text-[9px] text-text-secondary uppercase font-sans font-bold tracking-wider mb-1">Local Temperature</p>
          <h4 className="text-base font-bold text-text-primary flex items-center gap-1">
            <CloudSun size={13} className="text-amber-500 font-sans" /> {data.temperature}°F
          </h4>
        </div>
      </div>
      <div className="bg-bg-primary/50 p-2.5 rounded-[4px] border border-border-hairline flex items-center gap-2 text-[9px] text-text-secondary leading-normal font-sans">
        <ShieldCheck size={14} className="text-primary-blue shrink-0" />
        <span>Real-time EIA state metrics integrated. Regional average model loaded.</span>
      </div>
    </motion.div>
  );
}

// ─── Animated Energy Grid SVG ──────────────────────────────────────────────────
function AnimatedGridSVG() {
  return (
    <svg className="w-full h-full min-h-[380px] md:min-h-[460px]" viewBox="0 0 800 500" fill="none" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <linearGradient id="grid-grad" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#2F6BFF" stopOpacity="0.8" />
          <stop offset="50%" stopColor="#16A085" stopOpacity="0.6" />
          <stop offset="100%" stopColor="#2F6BFF" stopOpacity="0.2" />
        </linearGradient>
        <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
          <feGaussianBlur stdDeviation="6" result="blur" />
          <feComposite in="SourceGraphic" in2="blur" operator="over" />
        </filter>
      </defs>

      {/* Grid Mesh Layout Nodes */}
      {/* Power Plant */}
      <rect x="50" y="180" width="100" height="80" rx="6" fill="#1C2833" stroke="var(--border-hairline)" strokeWidth="1.5" />
      <path d="M70 180 L70 140 L90 140 L90 180" fill="none" stroke="var(--border-hairline)" strokeWidth="2" />
      <path d="M110 180 L110 130 L130 130 L130 180" fill="none" stroke="var(--border-hairline)" strokeWidth="2" />
      <text x="100" y="225" fill="#AEB6BF" fontSize="10" fontWeight="bold" fontFamily="sans-serif" textAnchor="middle">Generation</text>

      {/* Transmission Lines Paths */}
      <path d="M150 220 L270 220" stroke="var(--border-hairline)" strokeWidth="2" strokeDasharray="5 5" />
      
      {/* Transmission Tower */}
      <path d="M270 260 L290 140 L310 260 M270 180 L310 180 M280 220 L300 220" fill="none" stroke="#5D6D7E" strokeWidth="2" />
      <text x="290" y="280" fill="#AEB6BF" fontSize="10" fontWeight="bold" fontFamily="sans-serif" textAnchor="middle">Transmission</text>

      {/* Substation */}
      <path d="M310 220 L450 220" stroke="var(--border-hairline)" strokeWidth="2" strokeDasharray="5 5" />
      <rect x="450" y="180" width="80" height="80" rx="6" fill="#1C2833" stroke="var(--border-hairline)" strokeWidth="1.5" />
      <circle cx="490" cy="220" r="16" fill="none" stroke="#2CA6FF" strokeWidth="2" />
      <path d="M480 220 L500 220 M490 210 L490 230" stroke="#2CA6FF" strokeWidth="2" />
      <text x="490" y="280" fill="#AEB6BF" fontSize="10" fontWeight="bold" fontFamily="sans-serif" textAnchor="middle">Substation</text>

      {/* Distribution Line Path */}
      <path d="M530 220 L650 220" stroke="var(--border-hairline)" strokeWidth="2" />

      {/* Smart Home */}
      <rect x="650" y="170" width="90" height="90" rx="8" fill="#1C2833" stroke="var(--border-hairline)" strokeWidth="1.5" />
      <polygon points="650,170 695,130 740,170" fill="#2C3E50" stroke="var(--border-hairline)" strokeWidth="1.5" />
      <rect x="685" y="210" width="20" height="50" fill="#5D6D7E" />
      <circle cx="695" cy="155" r="8" fill="#F5B041" opacity="0.6" filter="url(#glow)" />
      <text x="695" y="280" fill="#AEB6BF" fontSize="10" fontWeight="bold" fontFamily="sans-serif" textAnchor="middle">Smart Home</text>

      {/* Pulsing Energy flow lines along the grid */}
      <motion.path
        d="M150 220 L290 220 L450 220 L650 220"
        fill="none"
        stroke="url(#grid-grad)"
        strokeWidth="3.5"
        strokeDasharray="40 180"
        animate={{ strokeDashoffset: [-220, 220] }}
        transition={{ repeat: Infinity, duration: 4, ease: 'linear' }}
        filter="url(#glow)"
      />
    </svg>
  );
}

// ─── Landing Page Main ────────────────────────────────────────────────────────
export default function LandingPage() {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 20);
    };
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const featureCards = [
    {
      title: 'AI Ingestion & Analysis',
      desc: 'Scan bills instantly. Extract delivery items, public service adjustments, and trace hidden grid taxes.',
      icon: <FileText className="text-primary-blue" size={20} />,
      link: '/bill-analysis'
    },
    {
      title: 'ML Bill Forecasting',
      desc: 'Calculate seasonal usage spikes using neural ensemble models and actual weather history.',
      icon: <LineChart className="text-energy-teal" size={20} />,
      link: '/forecast'
    },
    {
      title: 'Sensitivity & What-If Simulation',
      desc: 'Simulate rates changes, load shifts, and EV additions under clean Monte Carlo projections.',
      icon: <BarChart3 className="text-amber-500" size={20} />,
      link: '/impact'
    },
    {
      title: 'GIS Regional Insights',
      desc: 'Verify spatial pricing spreads across state lines, utilities service zones, and postal codes.',
      icon: <MapPin className="text-primary-blue" size={20} />,
      link: '/regional-insights'
    },
    {
      title: 'BGS Plan Matcher',
      desc: 'Filter current retail tariffs against utility auctions to discover optimal plans.',
      icon: <Compass className="text-savings-green" size={20} />,
      link: '/plans'
    },
    {
      title: 'Custom AI Reports',
      desc: 'Generate concise executive summaries and action items in clean plain-English text.',
      icon: <Sparkles className="text-purple-500" size={20} />,
      link: '/settings'
    }
  ];

  return (
    <div className="min-h-screen bg-bg-primary text-text-primary selection:bg-primary-blue/20 flex flex-col justify-between">
      
      {/* 1. Sticky Navigation Bar */}
      <header className={`fixed top-0 left-0 w-full z-40 transition-all duration-300 ${
        scrolled 
          ? 'bg-bg-surface/80 backdrop-blur-md border-b border-border-hairline py-3 shadow-md' 
          : 'bg-transparent py-5'
      }`}>
        <div className="max-w-7xl mx-auto px-6 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-[4px] bg-primary-blue flex items-center justify-center font-bold text-white text-sm shadow-md shadow-primary-blue/20">E</div>
            <span className="font-sans font-bold text-base tracking-tight text-text-primary">ElectricAI</span>
          </Link>

          <nav className="hidden md:flex items-center gap-6 text-xs font-semibold text-text-secondary font-sans">
            <a href="#features" className="hover:text-text-primary transition-colors">Features</a>
            <a href="#how-it-works" className="hover:text-text-primary transition-colors">How It Works</a>
            <a href="#why-us" className="hover:text-text-primary transition-colors">Why ElectricAI</a>
            <span className="opacity-40 cursor-not-allowed">Pricing (Soon)</span>
            <a href="https://github.com" target="_blank" rel="noreferrer" className="hover:text-text-primary transition-colors">Docs</a>
          </nav>

          <div className="flex items-center gap-3">
            <Link to="/login" className="px-3.5 py-1.5 hover:text-text-primary text-xs font-semibold text-text-secondary transition-colors">
              Login
            </Link>
            <Link to="/signup" className="bg-primary-blue hover:bg-primary-blue/95 text-white font-semibold text-xs px-4 py-2 rounded-md transition-all shadow-sm">
              Get Started
            </Link>
          </div>
        </div>
      </header>

      {/* 2. Hero Section */}
      <section className="pt-28 md:pt-36 pb-20 max-w-7xl mx-auto w-full px-6 grid grid-cols-1 lg:grid-cols-12 gap-12 items-center">
        <div className="lg:col-span-6 space-y-6">
          <span className="bg-primary-blue/10 text-primary-blue text-xs font-semibold uppercase tracking-wider px-3 py-1 rounded-[6px] inline-flex items-center gap-1.5">
            <Zap size={12} className="animate-pulse" /> Operational Electricity Intelligence
          </span>

          <h1 className="text-3xl sm:text-4xl md:text-5xl font-extrabold tracking-tight text-text-primary font-sans leading-tight">
            Understand Your Electricity. <br />
            <span className="text-primary-blue">Reduce Your Bills.</span> <br />
            Power Smarter Decisions.
          </h1>

          <p className="text-text-secondary text-sm md:text-base leading-relaxed max-w-xl">
            ElectricAI transforms your raw utility billing PDF into personalized operational energy intelligence. Expose hidden components, run load simulations, and map regional rate disparities in seconds.
          </p>

          {/* Buttons */}
          <div className="flex flex-wrap gap-4 pt-2">
            <Link 
              to="/signup" 
              className="bg-primary-blue hover:bg-primary-blue/95 text-white font-bold px-6 py-3 rounded-md text-xs shadow-md transition-all flex items-center gap-1.5"
            >
              Get Started <ArrowRight size={14} />
            </Link>
            <Link 
              to="/demo" 
              className="bg-bg-surface hover:bg-bg-primary border border-border-hairline font-bold px-6 py-3 rounded-md text-xs transition-all shadow-sm"
            >
              Explore Demo
            </Link>
          </div>

          {/* Badges */}
          <div className="flex flex-wrap gap-3 text-[10px] font-bold text-text-secondary pt-6 font-sans">
            <span className="flex items-center gap-1 bg-bg-surface px-2.5 py-1 rounded-full border border-border-hairline">
              <ShieldCheck size={12} className="text-primary-blue" /> AI Bill Analysis
            </span>
            <span className="flex items-center gap-1 bg-bg-surface px-2.5 py-1 rounded-full border border-border-hairline">
              <ShieldCheck size={12} className="text-primary-blue" /> Bill Forecasting
            </span>
            <span className="flex items-center gap-1 bg-bg-surface px-2.5 py-1 rounded-full border border-border-hairline">
              <ShieldCheck size={12} className="text-primary-blue" /> Regional Insights
            </span>
            <span className="flex items-center gap-1 bg-bg-surface px-2.5 py-1 rounded-full border border-border-hairline">
              <ShieldCheck size={12} className="text-primary-blue" /> Savings Simulator
            </span>
            <span className="flex items-center gap-1 bg-bg-surface px-2.5 py-1 rounded-full border border-border-hairline">
              <ShieldCheck size={12} className="text-primary-blue" /> Energy Plans
            </span>
          </div>
        </div>

        {/* Right Side Illustration + Telemetry */}
        <div className="lg:col-span-6 flex flex-col items-center justify-center gap-6">
          <div className="w-full bg-bg-surface/50 border border-border-hairline rounded-lg overflow-hidden shadow-xl p-4">
            <AnimatedGridSVG />
          </div>
          <LiveEnergyPanel />
        </div>
      </section>

      {/* 3. Features Section */}
      <section id="features" className="py-20 max-w-7xl mx-auto w-full px-6 border-t border-border-hairline">
        <div className="text-center max-w-3xl mx-auto space-y-3 mb-16">
          <span className="text-[10px] font-bold uppercase tracking-wider text-primary-blue bg-primary-blue/10 px-3 py-1 rounded-[6px]">
            Core Modules
          </span>
          <h2 className="text-2xl md:text-3xl font-extrabold text-text-primary tracking-tight font-sans">
            Personalized Energy Intelligence Workspace
          </h2>
          <p className="text-text-secondary text-xs md:text-sm">
            Everything you need to analyze charges, predict costs, and optimize your rates in one platform.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {featureCards.map((f, idx) => (
            <motion.div
              key={idx}
              whileHover={{ y: -4, boxShadow: '0 8px 30px rgba(0,0,0,0.06)' }}
              className="bg-bg-surface border border-border-hairline hover:border-primary-blue/30 p-6 rounded-lg shadow-sm flex flex-col justify-between"
            >
              <div className="space-y-3">
                <div className="w-10 h-10 bg-bg-primary rounded-[6px] border border-border-hairline flex items-center justify-center">
                  {f.icon}
                </div>
                <h3 className="text-sm font-bold text-text-primary leading-tight font-sans">{f.title}</h3>
                <p className="text-text-secondary text-xs leading-normal">{f.desc}</p>
              </div>
              <div className="pt-4 border-t border-border-hairline/50 mt-4 flex justify-between items-center text-xs font-semibold text-primary-blue">
                <Link to="/signup" className="hover:underline flex items-center gap-1">
                  Learn More <ArrowRight size={12} />
                </Link>
              </div>
            </motion.div>
          ))}
        </div>
      </section>

      {/* 4. How It Works (Timeline) */}
      <section id="how-it-works" className="py-20 bg-bg-surface/50 border-t border-b border-border-hairline w-full">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center max-w-3xl mx-auto space-y-3 mb-16">
            <span className="text-[10px] font-bold uppercase tracking-wider text-primary-blue bg-primary-blue/10 px-3 py-1 rounded-[6px]">
              How it works
            </span>
            <h2 className="text-2xl md:text-3xl font-extrabold text-text-primary tracking-tight font-sans">
              From Raw PDF to Measurable Energy Savings
            </h2>
            <p className="text-text-secondary text-xs md:text-sm">
              We process, estimate, and analyze your bill details across six granular steps.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-6 gap-6 relative">
            {/* Timeline cards */}
            {[
              { num: '1', title: 'Upload Bill', desc: 'Select any electricity bill PDF or image file' },
              { num: '2', title: 'OCR Scan', desc: 'Auto-extract text tokens and numeric tables' },
              { num: '3', title: 'AI Explanation', desc: 'Plain-language summaries of charges' },
              { num: '4', title: 'Regional Comp', desc: 'Compare rates to neighborhood baselines' },
              { num: '5', title: 'ML Forecasting', desc: 'Predict future usage patterns' },
              { num: '6', title: 'Optimize Costs', desc: 'Compare other energy tariffs to save' }
            ].map((s, idx) => (
              <div key={idx} className="bg-bg-surface border border-border-hairline p-5 rounded-lg flex flex-col justify-between min-h-[140px] text-xs">
                <div>
                  <div className="w-6 h-6 bg-primary-blue text-white rounded-full font-bold flex items-center justify-center font-mono-numbers mb-3">
                    {s.num}
                  </div>
                  <h4 className="font-bold text-text-primary leading-tight font-sans mb-1">{s.title}</h4>
                </div>
                <p className="text-[11px] text-text-secondary font-medium">{s.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* 5. Why ElectricAI (Detailed Points) */}
      <section id="why-us" className="py-20 max-w-7xl mx-auto w-full px-6">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-center">
          <div className="lg:col-span-5 space-y-6">
            <span className="text-[10px] font-bold uppercase tracking-wider text-primary-blue bg-primary-blue/10 px-3 py-1 rounded-[6px]">
              Platform Value
            </span>
            <h2 className="text-3xl font-extrabold text-text-primary tracking-tight font-sans">
              Why use ElectricAI?
            </h2>
            <p className="text-text-secondary text-sm leading-relaxed">
              Managing electricity costs shouldn't involve spreadsheets. We do the math so you can make informed decisions.
            </p>
            <div className="pt-2">
              <Link 
                to="/signup" 
                className="bg-primary-blue hover:bg-primary-blue/95 text-white font-bold px-5 py-2.5 rounded-md text-xs transition-all shadow-sm inline-flex items-center gap-1.5"
              >
                Create Account <ArrowRight size={13} />
              </Link>
            </div>
          </div>

          <div className="lg:col-span-7 grid grid-cols-1 sm:grid-cols-2 gap-6 text-xs">
            <div className="border border-border-hairline p-5 rounded-lg space-y-2 bg-bg-surface">
              <h4 className="font-bold text-text-primary font-sans">Understand Every Bill</h4>
              <p className="text-text-secondary leading-relaxed font-semibold">Expose service fees, transmission charges, and state taxes that utilities leave unexplained.</p>
            </div>
            <div className="border border-border-hairline p-5 rounded-lg space-y-2 bg-bg-surface">
              <h4 className="font-bold text-text-primary font-sans">AI-Powered Insights</h4>
              <p className="text-text-secondary leading-relaxed font-semibold">Get actionable notifications explaining month-over-month usage anomalies and savings tips.</p>
            </div>
            <div className="border border-border-hairline p-5 rounded-lg space-y-2 bg-bg-surface">
              <h4 className="font-bold text-text-primary font-sans">Forecast Future Costs</h4>
              <p className="text-text-secondary leading-relaxed font-semibold">Our ML forecaster utilizes temperature averages to project bills before they arrive.</p>
            </div>
            <div className="border border-border-hairline p-5 rounded-lg space-y-2 bg-bg-surface">
              <h4 className="font-bold text-text-primary font-sans">Plan Comparison</h4>
              <p className="text-text-secondary leading-relaxed font-semibold">Check standard fixed plans against floating BGS hourly options to optimize costs.</p>
            </div>
          </div>
        </div>
      </section>

      {/* 6. Call to Action (CTA) */}
      <section className="py-20 w-full bg-primary-blue text-white relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-r from-primary-blue to-primary-blue/80 opacity-50 z-0" />
        <div className="max-w-4xl mx-auto px-6 text-center space-y-6 relative z-10">
          <h2 className="text-2xl md:text-4xl font-extrabold tracking-tight font-sans leading-tight">
            Ready to understand your electricity?
          </h2>
          <p className="text-white/80 text-sm max-w-xl mx-auto">
            Upload your electricity bill PDF anonymously today. No credit cards or complex setups required.
          </p>
          <div className="flex justify-center gap-4 pt-2">
            <Link 
              to="/signup" 
              className="bg-white text-primary-blue hover:bg-white/95 font-bold px-6 py-3 rounded-md text-xs transition-all shadow-md"
            >
              Get Started
            </Link>
            <Link 
              to="/demo" 
              className="bg-transparent border border-white/30 hover:bg-white/10 font-bold px-6 py-3 rounded-md text-xs transition-all"
            >
              Try Demo
            </Link>
          </div>
        </div>
      </section>

      {/* 7. Footer */}
      <footer className="bg-bg-primary border-t border-border-hairline py-12 w-full text-xs">
        <div className="max-w-7xl mx-auto px-6 grid grid-cols-1 md:grid-cols-4 gap-8 mb-8 text-text-secondary">
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <div className="w-6 h-6 rounded-[3px] bg-primary-blue flex items-center justify-center font-bold text-white text-xs">E</div>
              <span className="font-sans font-bold text-sm tracking-tight text-text-primary">ElectricAI</span>
            </div>
            <p className="text-[11px] leading-relaxed">
              Operational utility bill intelligence and plan matching platform.
            </p>
          </div>
          <div className="space-y-3">
            <h4 className="font-bold text-text-primary uppercase tracking-wider text-[10px]">Product</h4>
            <ul className="space-y-2 text-[11px]">
              <li><Link to="/demo" className="hover:text-text-primary transition-colors">Interactive Demo</Link></li>
              <li><a href="#features" className="hover:text-text-primary transition-colors">Features</a></li>
              <li><a href="#how-it-works" className="hover:text-text-primary transition-colors">How It Works</a></li>
            </ul>
          </div>
          <div className="space-y-3">
            <h4 className="font-bold text-text-primary uppercase tracking-wider text-[10px]">Resources</h4>
            <ul className="space-y-2 text-[11px]">
              <li><a href="https://github.com" target="_blank" rel="noreferrer" className="hover:text-text-primary transition-colors">GitHub Repository</a></li>
              <li><a href="https://open-meteo.com" target="_blank" rel="noreferrer" className="hover:text-text-primary transition-colors">Open-Meteo Weather</a></li>
            </ul>
          </div>
          <div className="space-y-3">
            <h4 className="font-bold text-text-primary uppercase tracking-wider text-[10px]">Contact</h4>
            <ul className="space-y-2 text-[11px] font-mono-numbers">
              <li>support@electricai.dev</li>
              <li>NJ GIS Ingestion workspace</li>
            </ul>
          </div>
        </div>
        <div className="max-w-7xl mx-auto px-6 border-t border-border-hairline pt-6 flex flex-col md:flex-row items-center justify-between text-text-secondary text-[10px] font-semibold font-sans">
          <span>© {new Date().getFullYear()} ElectricAI. All rights reserved.</span>
          <div className="flex gap-4 mt-2 md:mt-0">
            <span className="cursor-not-allowed opacity-50">Privacy Policy</span>
            <span className="cursor-not-allowed opacity-50">Terms of Service</span>
          </div>
        </div>
      </footer>

    </div>
  );
}
