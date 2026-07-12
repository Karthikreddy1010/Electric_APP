import { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { 
  ArrowRight, Zap, FileText, Compass,
  Activity, CloudSun, MapPin, Cpu
} from 'lucide-react';

export default function LandingPage() {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 10);
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const features = [
    {
      title: 'Neural Bill OCR',
      desc: 'Instant extraction of complex delivery items, public service adjustments, and hidden grid taxes from raw PDF uploads.',
      icon: <FileText size={18} className="text-primary-blue" />
    },
    {
      title: 'Weather-Adjusted Forecasting',
      desc: 'Predict your next 6 months of bills based on 10-year localized historical climate data and household elasticity models.',
      icon: <CloudSun size={18} className="text-text-secondary" />
    },
    {
      title: 'Real-time Market Telemetry',
      desc: 'Live PJM wholesale market ingestion mapped directly against your retail rate structure to calculate real markups.',
      icon: <Activity size={18} className="text-primary-blue" />
    },
    {
      title: 'BGS Plan Matcher',
      desc: 'Stop guessing. We filter every retail tariff against utility baseline auctions to prove mathematical savings paths.',
      icon: <Compass size={18} className="text-text-secondary" />
    },
    {
      title: 'Spatial Grid Insights',
      desc: 'Visualize rate disparities across state lines and utility service zones to understand your regional positioning.',
      icon: <MapPin size={18} className="text-text-secondary" />
    },
    {
      title: 'What-If Simulation Engine',
      desc: 'Calculate the exact ROI of buying an EV or switching to a time-of-use (TOU) plan before making the leap.',
      icon: <Cpu size={18} className="text-primary-blue" />
    }
  ];

  return (
    <div className="min-h-screen bg-bg-primary text-text-primary font-sans selection:bg-primary-blue/30 flex flex-col">
      {/* ── Navbar ── */}
      <header className={`fixed top-0 left-0 w-full z-50 transition-colors duration-200 border-b ${scrolled ? 'bg-bg-primary/90 backdrop-blur-md border-border-hairline' : 'bg-transparent border-transparent'}`}>
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-3 group focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-blue rounded-md">
            <div className="w-8 h-8 rounded-md bg-bg-surface border border-border-hairline flex items-center justify-center text-primary-blue transition-colors group-hover:border-primary-blue">
              <Zap size={16} />
            </div>
            <div className="flex flex-col">
              <span className="text-sm font-bold tracking-tight text-text-primary leading-tight">ElectricAI</span>
              <span className="text-[10px] tracking-wider uppercase font-mono text-text-secondary leading-tight">Operational Intelligence</span>
            </div>
          </Link>
          <div className="flex items-center gap-4">
            <Link to="/login" className="text-sm font-medium text-text-secondary hover:text-text-primary transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-blue rounded-md px-2 py-1">
              Sign In
            </Link>
            <Link to="/signup" className="px-4 py-2 bg-text-primary text-bg-primary text-sm font-semibold rounded-md hover:bg-text-secondary transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-blue focus-visible:ring-offset-2 focus-visible:ring-offset-bg-primary">
              Get Started
            </Link>
          </div>
        </div>
      </header>

      <main className="flex-1 flex flex-col mt-16">
        {/* ── Hero Section ── */}
        <section className="px-6 py-24 md:py-32 max-w-7xl mx-auto w-full">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-16 items-center">
            <div className="flex flex-col items-start">
              <motion.div 
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, ease: "easeOut" }}
                className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-border-hairline bg-bg-surface text-text-secondary text-xs font-mono mb-6"
              >
                <span className="w-2 h-2 rounded-full bg-energy-teal"></span> System Operational
              </motion.div>

              <motion.h1 
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, delay: 0.1, ease: "easeOut" }}
                className="text-4xl md:text-5xl lg:text-6xl font-bold tracking-tight text-text-primary leading-[1.1]"
              >
                Operational intelligence for your energy spend.
              </motion.h1>

              <motion.p 
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, delay: 0.2, ease: "easeOut" }}
                className="mt-6 text-lg text-text-secondary max-w-lg leading-relaxed"
              >
                A high-fidelity analysis platform that ingests raw utility bills, runs deterministic models against live wholesale markets, and surfaces mathematically proven cost optimizations.
              </motion.p>

              <motion.div 
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, delay: 0.3, ease: "easeOut" }}
                className="flex flex-col sm:flex-row gap-4 mt-10 w-full sm:w-auto"
              >
                <Link to="/signup" className="px-5 py-2.5 bg-primary-blue text-white text-sm font-medium rounded-md hover:bg-blue-600 transition-colors flex items-center justify-center gap-2 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-blue focus-visible:ring-offset-2 focus-visible:ring-offset-bg-primary">
                  Start Analysis <ArrowRight size={16} />
                </Link>
                <Link to="/demo" className="px-5 py-2.5 bg-bg-surface border border-border-hairline text-text-primary text-sm font-medium rounded-md hover:border-text-secondary transition-colors flex items-center justify-center focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-blue focus-visible:ring-offset-2 focus-visible:ring-offset-bg-primary">
                  View Demo Workspace
                </Link>
              </motion.div>
            </div>
            
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.8, delay: 0.4 }}
              className="hidden lg:block h-full relative"
            >
               {/* Abstract geometric representation of data instead of a fake dashboard */}
               <div className="absolute inset-0 bg-gradient-to-br from-bg-surface to-bg-primary border border-border-hairline rounded-lg overflow-hidden flex flex-col p-6">
                 <div className="flex justify-between items-center mb-8 border-b border-border-hairline pb-4">
                   <div className="text-xs font-mono text-text-secondary">SYSTEM LOG</div>
                   <div className="flex gap-2">
                     <div className="w-2 h-2 rounded-full bg-border-hairline"></div>
                     <div className="w-2 h-2 rounded-full bg-border-hairline"></div>
                     <div className="w-2 h-2 rounded-full bg-border-hairline"></div>
                   </div>
                 </div>
                 <div className="space-y-4 font-mono text-[11px] text-text-secondary">
                   <div className="flex gap-4"><span className="text-primary-blue">01</span><span>[INGEST] Parsed PDF structure. 22 blocks identified.</span></div>
                   <div className="flex gap-4"><span className="text-primary-blue">02</span><span>[MATCH] Tariff PSEG 15477 confirmed.</span></div>
                   <div className="flex gap-4"><span className="text-primary-blue">03</span><span>[MODEL] Calculating deterministic variance...</span></div>
                   <div className="flex gap-4"><span className="text-primary-blue">04</span><span>[TELEMETRY] Fetching PJM wholesale locational marginal prices.</span></div>
                   <div className="flex gap-4"><span className="text-energy-teal">05</span><span className="text-text-primary">Analysis complete. 3 optimization paths identified.</span></div>
                 </div>
                 <div className="mt-auto pt-8 flex gap-4">
                   <div className="h-16 flex-1 bg-bg-secondary border border-border-hairline rounded-md flex items-end p-2">
                     <div className="w-full h-1/3 bg-primary-blue/20 border-t border-primary-blue/50"></div>
                   </div>
                   <div className="h-16 flex-1 bg-bg-secondary border border-border-hairline rounded-md flex items-end p-2">
                     <div className="w-full h-2/3 bg-energy-teal/20 border-t border-energy-teal/50"></div>
                   </div>
                   <div className="h-16 flex-1 bg-bg-secondary border border-border-hairline rounded-md flex items-end p-2">
                     <div className="w-full h-1/2 bg-warning-amber/20 border-t border-warning-amber/50"></div>
                   </div>
                 </div>
               </div>
            </motion.div>
          </div>
        </section>

        {/* ── Features Grid ── */}
        <section className="px-6 py-24 border-t border-border-hairline bg-bg-surface w-full">
          <div className="max-w-7xl mx-auto">
            <div className="mb-12">
              <h2 className="text-2xl font-bold text-text-primary tracking-tight">Core Capabilities</h2>
              <p className="text-text-secondary mt-2 text-sm">Deterministic analysis and predictive modeling.</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-x-8 gap-y-12">
              {features.map((f, idx) => (
                <div key={idx} className="flex flex-col items-start group">
                  <div className="w-10 h-10 rounded-md border border-border-hairline bg-bg-primary flex items-center justify-center mb-4 transition-colors group-hover:border-text-secondary">
                    {f.icon}
                  </div>
                  <h3 className="text-sm font-semibold text-text-primary mb-2">{f.title}</h3>
                  <p className="text-sm text-text-secondary leading-relaxed">{f.desc}</p>
                </div>
              ))}
            </div>
          </div>
        </section>
      </main>

      {/* ── Footer ── */}
      <footer className="border-t border-border-hairline bg-bg-primary py-8 px-6 mt-auto">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row justify-between items-center gap-4">
          <div className="flex items-center gap-2">
            <Zap size={14} className="text-text-secondary" />
            <span className="font-semibold text-text-secondary text-xs tracking-tight">ElectricAI</span>
          </div>
          <div className="flex gap-6 text-xs text-text-secondary font-medium">
            <Link to="/demo" className="hover:text-text-primary transition-colors">Demo</Link>
            <a href="#" className="hover:text-text-primary transition-colors">Documentation</a>
            <a href="#" className="hover:text-text-primary transition-colors">Terms</a>
          </div>
        </div>
      </footer>
    </div>
  );
}
