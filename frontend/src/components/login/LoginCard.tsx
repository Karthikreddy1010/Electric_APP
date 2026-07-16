import { motion } from 'framer-motion';
import { Zap, AlertCircle } from 'lucide-react';

interface LoginCardProps {
  children: React.ReactNode;
  error?: string | null;
}

export default function LoginCard({ children, error }: LoginCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 40, scale: 0.96 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
      className="relative z-10 w-full max-w-[460px] rounded-3xl border border-[#00f2ff]/30 bg-[#0a0f1d]/75 backdrop-blur-2xl shadow-[0_30px_90px_rgba(0,0,0,0.8),0_0_60px_rgba(0,242,255,0.12)] p-8 sm:p-10 text-white flex flex-col gap-6"
    >
      {/* Centered Brand Logo & Title */}
      <div className="flex flex-col items-center gap-3.5 text-center mt-2">
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-blue-600 to-[#00f2ff] flex items-center justify-center text-white shadow-lg shadow-blue-500/20">
            <Zap size={20} className="fill-white text-white" />
          </div>
          <span className="text-xl font-bold tracking-tight text-white">ElectricAI</span>
        </div>
        
        <h2 className="text-2xl sm:text-[26px] font-bold tracking-tight text-white leading-tight mt-1 px-4">
          Sign in to ElectricAI <br />
          <span className="text-slate-100 font-semibold">Command Center</span>
        </h2>
      </div>

      {/* Error Message Box */}
      {error && (
        <motion.div
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          className="p-3.5 rounded-xl bg-red-500/10 border border-red-500/30 flex items-start gap-2.5 text-red-300 text-xs font-medium"
          role="alert"
        >
          <AlertCircle size={16} className="shrink-0 text-red-400 mt-0.5" />
          <span>{error}</span>
        </motion.div>
      )}

      {/* Children Form */}
      {children}
    </motion.div>
  );
}
