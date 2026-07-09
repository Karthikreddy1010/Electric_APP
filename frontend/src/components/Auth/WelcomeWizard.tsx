import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useAuth } from '../../context/AuthContext.tsx';
import { useBill } from '../../context/BillContext.tsx';
import { useBillUpload } from '../../hooks/useBillUpload.ts';
import { 
  Building2, MapPin, Upload, ArrowRight, ArrowLeft, 
  Sparkles, CheckCircle2, ShieldCheck, RefreshCw 
} from 'lucide-react';

const UTILITIES = [
  { id: 'pseg', name: 'PSE&G (Public Service Electric & Gas)' },
  { id: 'jcpl', name: 'JCP&L (Jersey Central Power & Light)' },
  { id: 'ace', name: 'Atlantic City Electric' },
  { id: 'reco', name: 'Rockland Electric Company' }
];

export default function WelcomeWizard() {
  const { user, completeOnboarding } = useAuth();
  const { setBillData: _setBillData } = useBill();
  const upload = useBillUpload();
  const [step, setStep] = useState(1);
  const [utility, setUtility] = useState(user?.utility_provider || 'PSE&G');
  const [zipCode, setZipCode] = useState(user?.zip_code || '');
  const [zipError, setZipError] = useState('');

  if (!user) return null;

  const handleNext = () => {
    if (step === 2 && !utility) return;
    if (step === 3) {
      if (!/^\d{5}$/.test(zipCode)) {
        setZipError('Please enter a valid 5-digit New Jersey ZIP code.');
        return;
      }
      setZipError('');
    }
    setStep((prev) => prev + 1);
  };

  const handleBack = () => {
    setStep((prev) => prev - 1);
  };

  const handleFinish = () => {
    completeOnboarding(zipCode, utility);
  };

  const handleMockUpload = async () => {
    upload.selectExample();
    await upload.runAnalysis();
    setStep(5);
  };

  const wizardVariants = {
    initial: { opacity: 0, scale: 0.95, y: 15 },
    animate: { opacity: 1, scale: 1, y: 0, transition: { duration: 0.4, ease: 'easeOut' as const } },
    exit: { opacity: 0, scale: 0.95, y: -15, transition: { duration: 0.3 } }
  };

  const stepVariants = {
    initial: { opacity: 0, x: 50 },
    animate: { opacity: 1, x: 0, transition: { duration: 0.3 } },
    exit: { opacity: 0, x: -50, transition: { duration: 0.3 } }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-md p-4">
      <motion.div
        variants={wizardVariants}
        initial="initial"
        animate="animate"
        exit="exit"
        className="w-full max-w-xl bg-bg-surface border border-border-hairline rounded-lg shadow-2xl overflow-hidden flex flex-col justify-between min-h-[460px]"
      >
        {/* Header step tracker */}
        <div className="bg-bg-primary px-6 py-4 border-b border-border-hairline flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Sparkles size={16} className="text-primary-blue animate-pulse" />
            <span className="text-xs font-bold text-text-primary uppercase tracking-wider">Welcome to ElectricAI</span>
          </div>
          <span className="text-xs font-mono font-bold text-text-secondary">
            Step {step} of 5
          </span>
        </div>

        {/* Step indicator bar */}
        <div className="w-full h-1 bg-bg-primary">
          <motion.div 
            className="h-full bg-primary-blue"
            animate={{ width: `${(step / 5) * 100}%` }}
            transition={{ duration: 0.3 }}
          />
        </div>

        {/* Main Content Area */}
        <div className="flex-1 p-8 overflow-y-auto">
          <AnimatePresence mode="wait">
            {step === 1 && (
              <motion.div
                key="step1"
                variants={stepVariants}
                initial="initial"
                animate="animate"
                exit="exit"
                className="space-y-4"
              >
                <div className="w-12 h-12 bg-primary-blue/10 rounded-md flex items-center justify-center text-primary-blue mb-4">
                  <Sparkles size={24} />
                </div>
                <h2 className="text-2xl font-bold text-text-primary tracking-tight">Hey {user.first_name}, welcome!</h2>
                <p className="text-text-secondary text-sm leading-relaxed">
                  Let's personalize your energy intelligence workspace in just 30 seconds. We'll set up your utility provider and scan your first bill to calibrate your analysis models.
                </p>
                <div className="pt-4 grid grid-cols-1 md:grid-cols-2 gap-3 text-xs text-text-secondary">
                  <div className="flex items-center gap-2 border border-border-hairline p-3 rounded-md bg-bg-primary">
                    <CheckCircle2 size={14} className="text-savings-green" /> Personalized Rate Tracking
                  </div>
                  <div className="flex items-center gap-2 border border-border-hairline p-3 rounded-md bg-bg-primary">
                    <CheckCircle2 size={14} className="text-savings-green" /> Smart Bill Forecasts
                  </div>
                </div>
              </motion.div>
            )}

            {step === 2 && (
              <motion.div
                key="step2"
                variants={stepVariants}
                initial="initial"
                animate="animate"
                exit="exit"
                className="space-y-4"
              >
                <div className="w-12 h-12 bg-primary-blue/10 rounded-md flex items-center justify-center text-primary-blue mb-4">
                  <Building2 size={24} />
                </div>
                <h2 className="text-2xl font-bold text-text-primary tracking-tight">Who supplies your electricity?</h2>
                <p className="text-text-secondary text-sm">
                  We use your utility's specific rate schedule structures and historic tariffs to match your charges.
                </p>
                <div className="space-y-2 pt-2">
                  <label className="text-[10px] font-bold uppercase tracking-wider text-text-secondary block">Select Provider</label>
                  <select
                    value={utility}
                    onChange={(e) => setUtility(e.target.value)}
                    className="w-full bg-bg-primary border border-border-hairline hover:border-text-secondary text-text-primary px-3 py-2.5 rounded-md text-xs font-semibold focus:outline-none focus:border-primary-blue transition-all"
                  >
                    {UTILITIES.map((u) => (
                      <option key={u.id} value={u.name.split(' (')[0]}>
                        {u.name}
                      </option>
                    ))}
                  </select>
                </div>
              </motion.div>
            )}

            {step === 3 && (
              <motion.div
                key="step3"
                variants={stepVariants}
                initial="initial"
                animate="animate"
                exit="exit"
                className="space-y-4"
              >
                <div className="w-12 h-12 bg-primary-blue/10 rounded-md flex items-center justify-center text-primary-blue mb-4">
                  <MapPin size={24} />
                </div>
                <h2 className="text-2xl font-bold text-text-primary tracking-tight">What is your ZIP code?</h2>
                <p className="text-text-secondary text-sm">
                  We compare your rates against local grid averages and community solar programs in your regional territory.
                </p>
                <div className="space-y-2 pt-2">
                  <label className="text-[10px] font-bold uppercase tracking-wider text-text-secondary block">ZIP Code</label>
                  <input
                    type="text"
                    maxLength={5}
                    value={zipCode}
                    onChange={(e) => setZipCode(e.target.value.replace(/\D/g, ''))}
                    placeholder="e.g. 07102"
                    className="w-full bg-bg-primary border border-border-hairline hover:border-text-secondary text-text-primary px-3 py-2.5 rounded-md text-xs font-mono font-semibold focus:outline-none focus:border-primary-blue transition-all"
                  />
                  {zipError && <p className="text-xs text-energy-red font-semibold">{zipError}</p>}
                </div>
              </motion.div>
            )}

            {step === 4 && (
              <motion.div
                key="step4"
                variants={stepVariants}
                initial="initial"
                animate="animate"
                exit="exit"
                className="space-y-4"
              >
                <div className="w-12 h-12 bg-primary-blue/10 rounded-md flex items-center justify-center text-primary-blue mb-4">
                  <Upload size={24} />
                </div>
                <h2 className="text-2xl font-bold text-text-primary tracking-tight">Upload your first bill</h2>
                <p className="text-text-secondary text-sm">
                  Ingest a PDF bill to feed actual baseline telemetry to the simulator.
                </p>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
                  {/* File selector or Mock option */}
                  <div
                    onClick={() => upload.fileInputRef.current?.click()}
                    className="border-2 border-dashed border-border-hairline hover:border-primary-blue rounded-md p-6 text-center cursor-pointer transition-all bg-bg-primary flex flex-col items-center justify-center"
                  >
                    <input
                      type="file"
                      ref={upload.fileInputRef}
                      onChange={async (e) => {
                        upload.handleFileSelect(e);
                        if (e.target.files?.[0]) {
                          await upload.runAnalysis();
                          setStep(5);
                        }
                      }}
                      accept=".pdf"
                      className="hidden"
                    />
                    <Upload size={20} className="text-text-secondary mb-2" />
                    <span className="text-xs font-bold text-text-primary">Upload Bill PDF</span>
                    <span className="text-[9px] text-text-secondary mt-1">Supports PDF scans</span>
                  </div>

                  <div
                    onClick={handleMockUpload}
                    className="border border-border-hairline hover:border-primary-blue rounded-md p-6 text-center cursor-pointer transition-all bg-bg-primary flex flex-col items-center justify-center relative overflow-hidden group"
                  >
                    {upload.isScanning && (
                      <div className="absolute inset-0 bg-black/20 flex items-center justify-center z-10">
                        <RefreshCw size={18} className="animate-spin text-primary-blue" />
                      </div>
                    )}
                    <Sparkles size={20} className="text-primary-blue mb-2" />
                    <span className="text-xs font-bold text-text-primary">Use Demo Sample</span>
                    <span className="text-[9px] text-text-secondary mt-1">Calibrate with simulated PSE&G bill</span>
                  </div>
                </div>

                {upload.isScanning && (
                  <div className="bg-bg-primary border border-border-hairline p-3 rounded-md text-[10px] font-mono text-text-secondary animate-pulse mt-4">
                    👁️ Ingesting PDF layout structure...
                  </div>
                )}
              </motion.div>
            )}

            {step === 5 && (
              <motion.div
                key="step5"
                variants={stepVariants}
                initial="initial"
                animate="animate"
                exit="exit"
                className="space-y-4 text-center py-4"
              >
                <div className="w-16 h-16 bg-savings-green/10 rounded-full flex items-center justify-center text-savings-green mx-auto mb-4">
                  <CheckCircle2 size={36} />
                </div>
                <h2 className="text-2xl font-bold text-text-primary tracking-tight">You're all set!</h2>
                <p className="text-text-secondary text-sm max-w-md mx-auto">
                  Your ElectricAI workspace is configured for **{utility}** in zip **{zipCode}**. Models have been calibrated and are ready.
                </p>

                <div className="border border-border-hairline bg-bg-primary/50 p-4 rounded-md inline-flex items-center gap-3 text-xs text-text-primary max-w-sm mt-2">
                  <ShieldCheck size={16} className="text-savings-green" />
                  <span className="font-semibold text-left leading-tight">Mock Auth & Bill session loaded securely.</span>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Footer Actions */}
        <div className="bg-bg-primary px-6 py-4 border-t border-border-hairline flex items-center justify-between">
          {step > 1 && step < 5 ? (
            <button
              onClick={handleBack}
              disabled={upload.isScanning}
              className="bg-bg-surface hover:bg-bg-primary border border-border-hairline text-text-primary font-semibold px-4 py-2 rounded-md text-xs transition-all flex items-center gap-1.5 disabled:opacity-50"
            >
              <ArrowLeft size={13} /> Back
            </button>
          ) : (
            <div />
          )}

          {step < 4 ? (
            <button
              onClick={handleNext}
              className="bg-primary-blue text-white hover:bg-primary-blue/90 font-semibold px-5 py-2.5 rounded-md text-xs transition-all flex items-center gap-1.5"
            >
              Continue <ArrowRight size={13} />
            </button>
          ) : step === 4 ? (
            <button
              onClick={() => setStep(5)}
              className="text-text-secondary hover:text-text-primary font-semibold text-xs transition-all"
            >
              Skip upload for now
            </button>
          ) : (
            <button
              onClick={handleFinish}
              className="w-full bg-primary-blue text-white hover:bg-primary-blue/90 font-bold py-3 rounded-md text-xs transition-all flex items-center justify-center gap-1.5 shadow-sm"
            >
              Enter Dashboard <ArrowRight size={14} />
            </button>
          )}
        </div>
      </motion.div>
    </div>
  );
}
