import { motion } from 'framer-motion';

export default function LiveGridLoadCard() {
  return (
    <motion.div
      initial={{ opacity: 0, x: 40 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.8, delay: 0.4, ease: [0.16, 1, 0.3, 1] }}
      className="glass-panel w-[290px] p-5 rounded-2xl border border-slate-800 bg-[#0a0f1d]/70 backdrop-blur-md shadow-2xl flex flex-col gap-4 text-white"
    >
      {/* Header */}
      <div className="flex items-center justify-between text-xs font-semibold text-slate-300">
        <span>Live Grid Load</span>
        <span className="text-slate-500 cursor-pointer hover:text-slate-300 text-sm font-bold">•••</span>
      </div>

      {/* Grid Load Line/Area Chart */}
      <div className="h-20 relative mt-1">
        {/* Peak label indicator */}
        <div className="absolute left-[65%] -top-2.5 flex flex-col items-center">
          <span className="bg-[#00f2ff]/20 text-[#00f2ff] text-[8px] font-bold px-1.5 py-0.5 rounded-md border border-[#00f2ff]/30">
            Peak load: 84%
          </span>
          <div className="w-[1px] h-12 border-l border-dashed border-[#00f2ff]/50 mt-1" />
        </div>

        {/* Chart SVG */}
        <svg className="w-full h-full" viewBox="0 0 100 40" preserveAspectRatio="none">
          <defs>
            <linearGradient id="area-grad" x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stopColor="#06b6d4" stopOpacity="0.4" />
              <stop offset="100%" stopColor="#06b6d4" stopOpacity="0.0" />
            </linearGradient>
          </defs>

          {/* Area under curve */}
          <path
            d="M0,40 L0,30 Q15,25 30,35 T60,20 T80,10 L100,20 L100,40 Z"
            fill="url(#area-grad)"
          />

          {/* Sparkline curve */}
          <path
            d="M0,30 Q15,25 30,35 T60,20 T80,10 L100,20"
            fill="none"
            stroke="#00f2ff"
            strokeWidth="1.5"
          />

          {/* Peak point indicator dot */}
          <circle cx="80" cy="10" r="3.5" fill="#00f2ff" className="animate-ping" />
          <circle cx="80" cy="10" r="2.5" fill="#fff" />
        </svg>
      </div>

      {/* Footer details */}
      <div className="flex items-center justify-between border-t border-slate-800/80 pt-3 text-[11px] font-semibold text-slate-400">
        <span>Current Load: 84%</span>
        <div className="w-24 bg-slate-950/80 rounded-full h-1.5 overflow-hidden">
          <div className="bg-gradient-to-r from-blue-600 to-[#00f2ff] h-full w-[84%]" />
        </div>
      </div>
    </motion.div>
  );
}
