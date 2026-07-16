import { motion } from 'framer-motion';

export default function SystemHealthCard() {
  return (
    <motion.div
      initial={{ opacity: 0, x: -40 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.8, delay: 0.3, ease: [0.16, 1, 0.3, 1] }}
      className="glass-panel w-[280px] p-5 rounded-2xl border border-slate-800 bg-[#0a0f1d]/70 backdrop-blur-md shadow-2xl flex flex-col gap-4 text-white"
    >
      {/* Header */}
      <div className="flex items-center justify-between text-xs font-semibold text-slate-300">
        <span>System Health</span>
        <span className="text-slate-500 cursor-pointer hover:text-slate-300 text-sm font-bold">•••</span>
      </div>

      {/* Main Body Grid */}
      <div className="flex gap-4">
        {/* Radial Status Indicator (Left) */}
        <div className="flex flex-col items-center justify-center shrink-0 w-24">
          <div className="relative w-20 h-20 flex items-center justify-center">
            {/* SVG circle track */}
            <svg className="absolute w-full h-full transform -rotate-90" viewBox="0 0 36 36">
              <circle cx="18" cy="18" r="16" fill="none" stroke="#121826" strokeWidth="2.5" />
              <circle
                cx="18"
                cy="18"
                r="16"
                fill="none"
                stroke="#10b981"
                strokeWidth="2.5"
                strokeDasharray="100"
                strokeDashoffset="15"
                strokeLinecap="round"
                className="shadow-[0_0_8px_#10b981]"
              />
            </svg>
            <div className="text-[11px] font-bold text-emerald-400">Status</div>
          </div>
        </div>

        {/* Sparklines Area (Right) */}
        <div className="flex-1 flex flex-col justify-between h-20 py-0.5">
          {/* Sparkline 1 */}
          <div className="h-8 relative">
            <svg className="w-full h-full" viewBox="0 0 100 30" preserveAspectRatio="none">
              <path
                d="M0,15 Q15,5 30,20 T60,10 T80,25 T100,15"
                fill="none"
                stroke="#06b6d4"
                strokeWidth="1.5"
              />
            </svg>
          </div>
          {/* Sparkline 2 */}
          <div className="h-8 relative">
            <svg className="w-full h-full" viewBox="0 0 100 30" preserveAspectRatio="none">
              <path
                d="M0,10 Q20,25 40,10 T70,20 T100,5"
                fill="none"
                stroke="#3b82f6"
                strokeWidth="1.5"
              />
            </svg>
          </div>
        </div>
      </div>

      {/* Footer with status label and progress bar */}
      <div className="flex items-center justify-between border-t border-slate-800/80 pt-3 text-[11px] font-semibold text-slate-400">
        <div className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse shadow-[0_0_6px_#10b981]" />
          <span>Status: Optimal</span>
        </div>
        <div className="w-20 bg-slate-950/80 rounded-full h-1.5 overflow-hidden">
          <div className="bg-emerald-500 h-full w-[85%]" />
        </div>
      </div>
    </motion.div>
  );
}
