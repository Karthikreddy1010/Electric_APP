import { useState, useEffect } from 'react';
import { useBill } from '../../context/BillContext.tsx';
import { useNavigate } from 'react-router-dom';
import { 
  Sparkles, X, Brain, ChevronRight, 
  Send, Activity, TrendingUp 
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

interface AIAssistantDrawerProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function AIAssistantDrawer({ isOpen, onClose }: AIAssistantDrawerProps) {
  const navigate = useNavigate();
  const { uploadedBill, billExplanation, hasBill } = useBill();
  const [activeTab, setActiveTab] = useState<'explanation' | 'recommendations'>('explanation');
  const [messages, setMessages] = useState<{ role: 'user' | 'assistant'; content: string }[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isThinking, setIsThinking] = useState(false);

  // Generate welcome message when bill changes
  useEffect(() => {
    if (uploadedBill) {
      setMessages([
        {
          role: 'assistant',
          content: `Hi! I have analyzed your **${uploadedBill.utility}** bill for the period ending **${uploadedBill.bill_date || uploadedBill.billing_period}**.\n\nYour total cost is **$${uploadedBill.total_bill?.toFixed(2)}** with an effective rate of **$${uploadedBill.effective_rate?.toFixed(4)}/kWh**.\n\nHow can I help you optimize your energy consumption today?`
        }
      ]);
    } else {
      setMessages([
        {
          role: 'assistant',
          content: "Welcome to ElectricAI Assistant. Please upload or persist a utility bill so I can provide contextual energy recommendations."
        }
      ]);
    }
  }, [uploadedBill]);

  const handleSendMessage = () => {
    if (!inputValue.trim()) return;
    const userMsg = inputValue;
    setMessages(prev => [...prev, { role: 'user', content: userMsg }]);
    setInputValue('');
    setIsThinking(true);

    // Simulate AI response stream
    setTimeout(() => {
      setIsThinking(false);
      let response = "I'm parsing your demand patterns. Can you clarify if you want to run a tariff Monte Carlo simulation or view peak demand timelines?";
      if (userMsg.toLowerCase().includes('save') || userMsg.toLowerCase().includes('reduce')) {
        response = `To reduce your cost, I recommend simulating a **Green Conservation** program in the **Impact Simulator** tab. A 10% usage shave cuts your volumetric delivery and generation costs by approx. **$${((uploadedBill?.total_bill || 100) * 0.1).toFixed(2)}** monthly.`;
      } else if (userMsg.toLowerCase().includes('forecast') || userMsg.toLowerCase().includes('future')) {
        response = "The demand forecasting engine projects a 7-day peak load load factor of 82%. You can drill down into confidence intervals on the Forecast tab.";
      }
      setMessages(prev => [...prev, { role: 'assistant', content: response }]);
    }, 1200);
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-50 flex justify-end">
          {/* Backdrop */}
          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/40 backdrop-blur-sm"
            onClick={onClose}
          />

          {/* Drawer Container */}
          <motion.div 
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', damping: 25, stiffness: 200 }}
            className="relative w-full max-w-[420px] h-full bg-bg-surface border-l border-border-hairline shadow-floating z-10 flex flex-col"
          >
            {/* Header */}
            <div className="flex items-center justify-between px-5 py-4 border-b border-border-hairline bg-bg-primary/20">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-lg bg-primary-blue/15 flex items-center justify-center border border-primary-blue/30 text-primary-blue animate-pulse">
                  <Brain size={16} />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-text-primary flex items-center gap-1.5">
                    ElectricAI Assistant <Sparkles size={12} className="text-warning-amber" />
                  </h3>
                  <span className="text-[10px] text-text-secondary flex items-center gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-savings-green" /> Contextual Ingestion Online
                  </span>
                </div>
              </div>
              <button 
                onClick={onClose} 
                className="p-1.5 rounded-md hover:bg-col-hover text-text-secondary hover:text-text-primary transition-all active:scale-95"
              >
                <X size={16} />
              </button>
            </div>

            {/* Ingestion & Analysis Sub tabs */}
            {hasBill && (
              <div className="flex border-b border-border-hairline px-3 bg-bg-primary/10">
                <button
                  onClick={() => setActiveTab('explanation')}
                  className={`flex-1 py-2 text-center text-xs font-semibold border-b-2 transition-all ${
                    activeTab === 'explanation' 
                      ? 'border-primary-blue text-primary-blue' 
                      : 'border-transparent text-text-secondary hover:text-text-primary'
                  }`}
                >
                  OCR Narrative
                </button>
                <button
                  onClick={() => setActiveTab('recommendations')}
                  className={`flex-1 py-2 text-center text-xs font-semibold border-b-2 transition-all ${
                    activeTab === 'recommendations' 
                      ? 'border-primary-blue text-primary-blue' 
                      : 'border-transparent text-text-secondary hover:text-text-primary'
                  }`}
                >
                  Causal Advisor
                </button>
              </div>
            )}

            {/* Content Body */}
            <div className="flex-1 overflow-y-auto p-5 space-y-5">
              {activeTab === 'explanation' ? (
                <>
                  {/* OCR narrative output */}
                  {hasBill && billExplanation ? (
                    <div className="space-y-4">
                      <div className="p-4 bg-primary-blue/5 border border-primary-blue/10 rounded-xl space-y-2">
                        <span className="text-[10px] uppercase font-bold text-primary-blue tracking-wide block">Executive Summary</span>
                        <div className="text-xs text-text-primary/90 leading-relaxed font-sans whitespace-pre-wrap">
                          {billExplanation}
                        </div>
                      </div>

                      {/* Bill quick highlights */}
                      <div className="space-y-2">
                        <span className="text-[10px] uppercase font-bold text-text-secondary tracking-wide block">Telemetry Metrics</span>
                        <div className="grid grid-cols-2 gap-2">
                          <div className="bg-bg-primary/50 border border-border-hairline p-3 rounded-lg">
                            <span className="text-[9px] text-text-secondary block">Supply Charges</span>
                            <span className="text-xs font-bold font-mono-numbers text-text-primary">${uploadedBill?.supply_charge?.toFixed(2)}</span>
                          </div>
                          <div className="bg-bg-primary/50 border border-border-hairline p-3 rounded-lg">
                            <span className="text-[9px] text-text-secondary block">Delivery Charges</span>
                            <span className="text-xs font-bold font-mono-numbers text-text-primary">${uploadedBill?.delivery_charge?.toFixed(2)}</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="h-48 flex flex-col items-center justify-center text-center space-y-3">
                      <Brain className="text-text-secondary" size={32} />
                      <p className="text-xs text-text-secondary">No utility bill loaded. Ingest a bill to generate OCR narratives.</p>
                      <button 
                        onClick={() => { navigate('/bill-analysis'); onClose(); }} 
                        className="bg-primary-blue text-white px-3 py-1.5 rounded-md text-[11px] font-semibold hover:bg-primary-blue/90"
                      >
                        Go to Ingestion
                      </button>
                    </div>
                  )}
                </>
              ) : (
                <div className="flex flex-col h-full">
                  {/* Chat Assistant interface */}
                  <div className="flex-1 space-y-4 overflow-y-auto mb-4 pr-1">
                    {messages.map((msg, i) => (
                      <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                        <div className={`max-w-[85%] rounded-xl px-3.5 py-2.5 text-xs ${
                          msg.role === 'user'
                            ? 'bg-primary-blue text-white'
                            : 'bg-bg-primary/60 border border-border-hairline text-text-primary/95'
                        }`}>
                          <p className="whitespace-pre-wrap leading-relaxed">{msg.content}</p>
                        </div>
                      </div>
                    ))}
                    {isThinking && (
                      <div className="flex justify-start">
                        <div className="bg-bg-primary/60 border border-border-hairline rounded-xl px-3.5 py-2.5 flex items-center gap-1.5">
                          <span className="w-1.5 h-1.5 rounded-full bg-primary-blue animate-bounce" style={{ animationDelay: '0ms' }} />
                          <span className="w-1.5 h-1.5 rounded-full bg-primary-blue animate-bounce" style={{ animationDelay: '150ms' }} />
                          <span className="w-1.5 h-1.5 rounded-full bg-primary-blue animate-bounce" style={{ animationDelay: '300ms' }} />
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Recommendations Actions Panel */}
                  {hasBill && messages.length <= 2 && (
                    <div className="border-t border-border-hairline pt-3 mb-3 space-y-2">
                      <span className="text-[9px] uppercase font-bold text-text-secondary block">Suggested Actions</span>
                      <button
                        onClick={() => { navigate('/impact'); onClose(); }}
                        className="w-full flex items-center justify-between p-2 rounded-lg bg-bg-primary/40 hover:bg-bg-primary border border-border-hairline text-left text-xs text-text-primary transition-all group"
                      >
                        <span className="flex items-center gap-2"><TrendingUp size={12} className="text-energy-teal" /> Simulate conservation scenario</span>
                        <ChevronRight size={12} className="text-text-secondary group-hover:translate-x-0.5 transition-transform" />
                      </button>
                      <button
                        onClick={() => { navigate('/forecast'); onClose(); }}
                        className="w-full flex items-center justify-between p-2 rounded-lg bg-bg-primary/40 hover:bg-bg-primary border border-border-hairline text-left text-xs text-text-primary transition-all group"
                      >
                        <span className="flex items-center gap-2"><Activity size={12} className="text-primary-blue" /> Check peak demand cycles</span>
                        <ChevronRight size={12} className="text-text-secondary group-hover:translate-x-0.5 transition-transform" />
                      </button>
                    </div>
                  )}

                  {/* Input area */}
                  <div className="flex gap-2">
                    <input
                      type="text"
                      placeholder="Ask about rate simulation or BGS supply..."
                      value={inputValue}
                      onChange={e => setInputValue(e.target.value)}
                      onKeyDown={e => e.key === 'Enter' && handleSendMessage()}
                      className="flex-1 bg-bg-primary border border-border-hairline rounded-lg px-3 py-2 text-xs text-text-primary focus:outline-none focus:border-primary-blue"
                    />
                    <button 
                      onClick={handleSendMessage}
                      className="p-2 rounded-lg bg-primary-blue text-white hover:bg-primary-blue/90 active:scale-95 transition-all flex items-center justify-center shrink-0"
                    >
                      <Send size={14} />
                    </button>
                  </div>
                </div>
              )}
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
