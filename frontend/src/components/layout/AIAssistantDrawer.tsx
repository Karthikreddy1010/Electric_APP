import { useState, useEffect, useRef } from 'react';
import { useBill } from '../../context/BillContext.tsx';
import { useNavigate } from 'react-router-dom';
import { 
  Sparkles, X, Brain, 
  Send, HelpCircle 
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import apiClient from '../../lib/apiClient.ts';

interface AIAssistantDrawerProps {
  isOpen: boolean;
  onClose: () => void;
}

const SUGGESTED_QUESTION_CHIPS = [
  "Why is my bill higher this month?",
  "Explain my bill",
  "Why are delivery charges increasing?",
  "What does customer charge mean?",
  "How can I reduce my bill?",
  "Explain my bill like I'm five",
  "Which bill component increased the most?",
  "Explain weather impact",
  "Explain my tariff"
];

export default function AIAssistantDrawer({ isOpen, onClose }: AIAssistantDrawerProps) {
  const navigate = useNavigate();
  const { uploadedBill, billExplanation, hasBill } = useBill();
  const [activeTab, setActiveTab] = useState<'explanation' | 'recommendations'>('explanation');
  const [messages, setMessages] = useState<{ role: 'user' | 'assistant'; content: string }[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isThinking, setIsThinking] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll chat history
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isThinking]);

  // Generate initial greeting message when bill changes
  useEffect(() => {
    if (uploadedBill) {
      setMessages([
        {
          role: 'assistant',
          content: `Hi! I have analyzed your **${uploadedBill.utility}** bill for the period ending **${uploadedBill.bill_date || uploadedBill.billing_period}**.\n\nYour total cost is **$${uploadedBill.total_bill?.toFixed(2)}** (${uploadedBill.usage_kwh?.toFixed(1)} kWh) with an effective rate of **$${uploadedBill.effective_rate?.toFixed(4)}/kWh**.\n\nAsk me any question about your electricity bill, rates, or savings opportunities!`
        }
      ]);
    } else {
      setMessages([
        {
          role: 'assistant',
          content: "Welcome to ElectricAI Copilot! I am specialized in analyzing electricity bills, tariffs, and energy cost optimization. Upload or select a utility bill to get started, or ask any electricity-related question!"
        }
      ]);
    }
  }, [uploadedBill]);

  const handleSendMessage = async (textToSend?: string) => {
    const question = (textToSend || inputValue).trim();
    if (!question || isThinking) return;

    // Append user message
    const updatedHistory = [...messages, { role: 'user' as const, content: question }];
    setMessages(updatedHistory);
    setInputValue('');
    setIsThinking(true);

    try {
      // Execute true conversational backend AI pipeline call
      const res = await apiClient.post('/llm/chat', {
        message: question,
        current_tab: activeTab,
        history: updatedHistory.map(m => ({ role: m.role, content: m.content })),
        context_data: uploadedBill ? { ...uploadedBill } : {}
      });

      const responseText = res.data?.answer || res.data?.text || res.data?.explanation || 
        "I've processed your query. Let me know if you need further bill analysis!";

      setMessages(prev => [...prev, { role: 'assistant', content: responseText }]);
    } catch (err: any) {
      console.error("AI Chat Assistant Error:", err);
      // Fallback response if network or server encounters issue
      const fallbackText = "I am specialized specifically for electricity bill analysis, utility tariffs, energy conservation, and cost optimization. Please ask me any question about your electricity bill!";
      setMessages(prev => [...prev, { role: 'assistant', content: fallbackText }]);
    } finally {
      setIsThinking(false);
    }
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
            className="relative w-full max-w-[440px] h-full bg-bg-surface border-l border-border-hairline shadow-floating z-10 flex flex-col"
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
                    <span className="w-1.5 h-1.5 rounded-full bg-savings-green" /> Conversational AI Active
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
                  AI Copilot Chat
                </button>
              </div>
            )}

            {/* Content Body */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4 flex flex-col justify-between">
              {activeTab === 'explanation' ? (
                <div className="space-y-4">
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
                </div>
              ) : (
                <div className="flex flex-col h-full justify-between space-y-3">
                  {/* Chat Assistant Messages Window */}
                  <div className="flex-1 space-y-3 overflow-y-auto pr-1">
                    {messages.map((msg, i) => (
                      <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                        <div className={`max-w-[88%] rounded-xl px-3.5 py-2.5 text-xs ${
                          msg.role === 'user'
                            ? 'bg-primary-blue text-white shadow-sm'
                            : 'bg-bg-primary/60 border border-border-hairline text-text-primary/95 shadow-sm'
                        }`}>
                          <p className="whitespace-pre-wrap leading-relaxed">{msg.content}</p>
                        </div>
                      </div>
                    ))}
                    {isThinking && (
                      <div className="flex justify-start">
                        <div className="bg-bg-primary/60 border border-border-hairline rounded-xl px-3.5 py-2.5 flex items-center gap-1.5">
                          <span className="text-[11px] text-text-secondary mr-1">AI Copilot is thinking</span>
                          <span className="w-1.5 h-1.5 rounded-full bg-primary-blue animate-bounce" style={{ animationDelay: '0ms' }} />
                          <span className="w-1.5 h-1.5 rounded-full bg-primary-blue animate-bounce" style={{ animationDelay: '150ms' }} />
                          <span className="w-1.5 h-1.5 rounded-full bg-primary-blue animate-bounce" style={{ animationDelay: '300ms' }} />
                        </div>
                      </div>
                    )}
                    <div ref={messagesEndRef} />
                  </div>

                  {/* Suggested Question Chips Shortcuts */}
                  <div className="border-t border-border-hairline pt-2.5 space-y-2">
                    <span className="text-[10px] font-semibold text-text-secondary flex items-center gap-1">
                      <HelpCircle size={11} className="text-primary-blue" /> Suggested Question Shortcuts
                    </span>
                    <div className="flex flex-wrap gap-1.5 max-h-24 overflow-y-auto pr-1">
                      {SUGGESTED_QUESTION_CHIPS.map((chip, idx) => (
                        <button
                          key={idx}
                          onClick={() => handleSendMessage(chip)}
                          className="text-[10px] px-2.5 py-1 rounded-full bg-primary-blue/10 hover:bg-primary-blue/20 text-primary-blue border border-primary-blue/20 transition-all text-left"
                        >
                          {chip}
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Input area */}
                  <div className="flex gap-2 pt-1">
                    <input
                      type="text"
                      placeholder="Ask any question about your electricity bill..."
                      value={inputValue}
                      onChange={e => setInputValue(e.target.value)}
                      onKeyDown={e => {
                        if (e.key === 'Enter') {
                          e.preventDefault();
                          handleSendMessage();
                        }
                      }}
                      className="flex-1 bg-bg-primary border border-border-hairline rounded-lg px-3 py-2 text-xs text-text-primary focus:outline-none focus:border-primary-blue"
                    />
                    <button 
                      onClick={() => handleSendMessage()}
                      disabled={isThinking || !inputValue.trim()}
                      className="p-2 rounded-lg bg-primary-blue text-white hover:bg-primary-blue/90 disabled:opacity-50 active:scale-95 transition-all flex items-center justify-center shrink-0"
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
