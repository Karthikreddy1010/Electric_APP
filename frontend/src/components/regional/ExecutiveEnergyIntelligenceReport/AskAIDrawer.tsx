import React, { useState } from 'react';
import { X, Send, Bot, User, Sparkles, HelpCircle } from 'lucide-react';
import type { ExecutiveReportData } from './types';

interface Message {
  id: string;
  sender: 'user' | 'ai';
  text: string;
  timestamp: string;
}

interface AskAIDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  reportContext?: ExecutiveReportData | any;
  stateCode?: string;
}

export const AskAIDrawer: React.FC<AskAIDrawerProps> = ({
  isOpen,
  onClose,
  reportContext,
  stateCode = 'NJ',
}) => {
  const summaryFinding = reportContext?.summaryData?.primaryFinding;
  const [messages, setMessages] = useState<Message[]>(() => [
    {
      id: 'welcome',
      sender: 'ai',
      text: summaryFinding
        ? `Hello! I am your AI Energy Analyst Assistant. I have analyzed your Executive Energy Intelligence Report for ${stateCode}. Key Finding: "${summaryFinding}"\n\nHow can I assist you with cost optimization, risk mitigations, or tariff questions?`
        : `Hello! I am your AI Energy Analyst Assistant. I have analyzed the Executive Energy Intelligence Report for ${stateCode}. How can I assist you with cost optimization, risk mitigations, or tariff questions?`,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    },
  ]);
  const [input, setInput] = useState('');
  const [isThinking, setIsThinking] = useState(false);

  if (!isOpen) return null;

  const quickQuestions = [
    'Summarize key cost drivers',
    'Why is price volatility medium risk?',
    'What can we do to reduce transmission costs?',
    'Explain the 90-day forecast assumptions',
  ];

  const handleSend = (textToSend?: string) => {
    const query = textToSend || input;
    if (!query.trim()) return;

    const userMsg: Message = {
      id: Date.now().toString(),
      sender: 'user',
      text: query,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, userMsg]);
    if (!textToSend) setInput('');
    setIsThinking(true);

    // Simulate AI Analyst response using context telemetry
    setTimeout(() => {
      let aiResponseText = `Based on the generated executive telemetry for ${stateCode}:\n\n`;

      const qLower = query.toLowerCase();
      if (qLower.includes('cost driver') || qLower.includes('transmission') || qLower.includes('reduce')) {
        aiResponseText += `Generation comprises 42.5% of total costs while Transmission represents 21.0%. Peak demand coincidental charge mitigation during PJM 5CP (5 Coincident Peak) hours is the primary operational strategy to lower transmission tariffs.`;
      } else if (qLower.includes('risk') || qLower.includes('volatility')) {
        aiResponseText += `Price Volatility is rated as Medium Risk due to natural gas pipeline congestion and clearing auction capacity price shifts across high-density urban nodes in ${stateCode}. Grid Reliability remains Low Risk with high baseload stability.`;
      } else if (qLower.includes('forecast') || qLower.includes('90-day')) {
        aiResponseText += `The 90-day forecast assumes steady grid baseload stability (+0.00% expected tariff deviation) with high confidence (100%) grounded in regional ZIP cluster telemetry and seasonality smoothing models.`;
      } else {
        aiResponseText += `The primary executive finding indicates that regional electricity rates averaged $0.3126/kWh across analyzed ZIP clusters with +0.00% MoM trajectory. All tariff metrics remain within normal standard deviations.`;
      }

      const aiMsg: Message = {
        id: (Date.now() + 1).toString(),
        sender: 'ai',
        text: aiResponseText,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };

      setMessages((prev) => [...prev, aiMsg]);
      setIsThinking(false);
    }, 1000);
  };

  return (
    <div className="fixed inset-0 z-50 overflow-hidden bg-black/40 backdrop-blur-xs flex justify-end transition-opacity">
      <div className="w-full max-w-md bg-white h-full shadow-2xl flex flex-col font-sans border-l border-gray-200 animate-in slide-in-from-right duration-300">
        {/* Drawer Header */}
        <div className="p-4 bg-[#1B365D] text-white flex items-center justify-between shadow-md">
          <div className="flex items-center gap-2.5">
            <div className="p-1.5 rounded-lg bg-white/10 backdrop-blur-xs text-amber-300">
              <Bot size={20} />
            </div>
            <div>
              <h3 className="text-sm font-bold text-white flex items-center gap-1.5">
                <span>AI Energy Analyst Assistant</span>
                <Sparkles size={13} className="text-amber-400 fill-amber-400" />
              </h3>
              <span className="text-[11px] text-blue-200">Context: Executive Energy Intelligence Report ({stateCode})</span>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1 rounded-md text-gray-300 hover:text-white hover:bg-white/10 transition-colors cursor-pointer"
          >
            <X size={18} />
          </button>
        </div>

        {/* Quick Questions Suggestions */}
        <div className="bg-blue-50/70 p-3 border-b border-blue-100 space-y-1.5">
          <span className="text-[11px] font-bold text-[#2a4b7c] uppercase tracking-wider flex items-center gap-1">
            <HelpCircle size={12} />
            <span>Suggested Context Questions:</span>
          </span>
          <div className="flex flex-wrap gap-1.5">
            {quickQuestions.map((q, idx) => (
              <button
                key={idx}
                onClick={() => handleSend(q)}
                className="text-[11px] bg-white border border-blue-200 hover:border-blue-400 text-gray-800 px-2.5 py-1 rounded-full transition-colors cursor-pointer text-left hover:bg-blue-50"
              >
                {q}
              </button>
            ))}
          </div>
        </div>

        {/* Message Log */}
        <div className="flex-1 p-4 overflow-y-auto space-y-3.5 bg-gray-50/50">
          {messages.map((msg) => {
            const isAI = msg.sender === 'ai';
            return (
              <div
                key={msg.id}
                className={`flex items-start gap-2.5 ${isAI ? '' : 'flex-row-reverse'}`}
              >
                <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs shrink-0 font-bold ${isAI ? 'bg-[#1B365D] text-amber-300' : 'bg-amber-400 text-gray-950'}`}>
                  {isAI ? <Bot size={14} /> : <User size={14} />}
                </div>

                <div
                  className={`max-w-[80%] rounded-xl p-3 text-xs leading-relaxed ${
                    isAI
                      ? 'bg-white text-gray-800 border border-gray-200 shadow-xs'
                      : 'bg-[#1B365D] text-white'
                  }`}
                >
                  <p className="whitespace-pre-line">{msg.text}</p>
                  <span className={`text-[10px] block mt-1 text-right ${isAI ? 'text-gray-400' : 'text-blue-200'}`}>
                    {msg.timestamp}
                  </span>
                </div>
              </div>
            );
          })}

          {isThinking && (
            <div className="flex items-center gap-2 text-xs text-gray-500 bg-white p-2.5 rounded-lg border border-gray-200 w-fit animate-pulse">
              <Bot size={14} className="text-[#1B365D]" />
              <span>Analyzing report telemetry...</span>
            </div>
          )}
        </div>

        {/* Input Bar */}
        <div className="p-3 bg-white border-t border-gray-200">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSend();
            }}
            className="flex items-center gap-2"
          >
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask AI about this executive report..."
              className="flex-1 bg-gray-50 border border-gray-300 rounded-lg px-3 py-2 text-xs text-gray-900 focus:outline-none focus:ring-1 focus:ring-[#1B365D]"
            />
            <button
              type="submit"
              disabled={!input.trim() || isThinking}
              className="p-2 bg-[#1B365D] hover:bg-[#0F2942] disabled:opacity-50 text-white rounded-lg transition-colors cursor-pointer shrink-0"
            >
              <Send size={15} />
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};

export default AskAIDrawer;
