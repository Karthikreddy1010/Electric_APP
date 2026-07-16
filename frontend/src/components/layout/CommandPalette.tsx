import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Search, Sun, Moon, Layout, FileText, 
  TrendingUp, Activity, Map, Settings, Globe, Play 
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

interface CommandItem {
  id: string;
  title: string;
  category: string;
  shortcut?: string[];
  icon: React.ReactNode;
  action: () => void;
}

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
  onThemeToggle: () => void;
  currentTheme: string;
}

export default function CommandPalette({ isOpen, onClose, onThemeToggle, currentTheme }: CommandPaletteProps) {
  const navigate = useNavigate();
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const commands: CommandItem[] = [
    {
      id: 'nav-overview',
      title: 'Navigate to Overview Dashboard',
      category: 'Navigation',
      shortcut: ['G', 'O'],
      icon: <Layout size={16} />,
      action: () => { navigate('/overview'); onClose(); }
    },
    {
      id: 'nav-bill',
      title: 'Navigate to Bill Ingestion & Analysis',
      category: 'Navigation',
      shortcut: ['G', 'B'],
      icon: <FileText size={16} />,
      action: () => { navigate('/bill-analysis'); onClose(); }
    },
    {
      id: 'nav-impact',
      title: 'Navigate to Impact Simulator',
      category: 'Navigation',
      shortcut: ['G', 'I'],
      icon: <TrendingUp size={16} />,
      action: () => { navigate('/impact'); onClose(); }
    },
    {
      id: 'nav-forecast',
      title: 'Navigate to Demand Forecast',
      category: 'Navigation',
      shortcut: ['G', 'F'],
      icon: <Activity size={16} />,
      action: () => { navigate('/forecast'); onClose(); }
    },
    {
      id: 'nav-regional',
      title: 'Navigate to Regional Insights',
      category: 'Navigation',
      shortcut: ['G', 'R'],
      icon: <Map size={16} />,
      action: () => { navigate('/regional-insights'); onClose(); }
    },
    {
      id: 'nav-settings',
      title: 'Navigate to Workspace Settings',
      category: 'Navigation',
      shortcut: ['G', 'S'],
      icon: <Settings size={16} />,
      action: () => { navigate('/settings'); onClose(); }
    },
    {
      id: 'theme-toggle',
      title: `Switch to ${currentTheme === 'dark' ? 'Light' : 'Dark'} Mode`,
      category: 'Preferences',
      shortcut: ['T', 'T'],
      icon: currentTheme === 'dark' ? <Sun size={16} /> : <Moon size={16} />,
      action: () => { onThemeToggle(); onClose(); }
    },
    {
      id: 'action-export',
      title: 'Export Active Bill to CSV / Parquet',
      category: 'Actions',
      shortcut: ['E', 'X'],
      icon: <Globe size={16} />,
      action: () => {
        // Trigger simulated export click by locating the export button
        const btn = document.getElementById('export-bill-btn') || document.getElementById('forecast-export-btn');
        if (btn) (btn as HTMLButtonElement).click();
        onClose();
      }
    },
    {
      id: 'action-sim-summer',
      title: 'Trigger Simulation Preset: Hot Summer',
      category: 'Simulator',
      shortcut: ['S', 'S'],
      icon: <Play size={16} />,
      action: () => {
        navigate('/impact');
        setTimeout(() => {
          const btn = document.getElementById('preset-hot_summer');
          if (btn) (btn as HTMLButtonElement).click();
        }, 150);
        onClose();
      }
    },
    {
      id: 'action-sim-winter',
      title: 'Trigger Simulation Preset: Cold Winter',
      category: 'Simulator',
      shortcut: ['S', 'W'],
      icon: <Play size={16} />,
      action: () => {
        navigate('/impact');
        setTimeout(() => {
          const btn = document.getElementById('preset-cold_winter');
          if (btn) (btn as HTMLButtonElement).click();
        }, 150);
        onClose();
      }
    }
  ];

  // Filter commands by query
  const filtered = commands.filter(cmd => 
    cmd.title.toLowerCase().includes(query.toLowerCase()) ||
    cmd.category.toLowerCase().includes(query.toLowerCase())
  );

  // Reset selected index when query changes
  useEffect(() => {
    setSelectedIndex(0);
  }, [query]);

  // Handle outside click
  useEffect(() => {
    const handleOutsideClick = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        onClose();
      }
    };
    if (isOpen) {
      document.addEventListener('mousedown', handleOutsideClick);
      inputRef.current?.focus();
    }
    return () => document.removeEventListener('mousedown', handleOutsideClick);
  }, [isOpen, onClose]);

  // Keyboard navigation inside the palette
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!isOpen) return;

      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSelectedIndex(prev => (prev + 1) % Math.max(1, filtered.length));
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSelectedIndex(prev => (prev - 1 + filtered.length) % Math.max(1, filtered.length));
      } else if (e.key === 'Enter') {
        e.preventDefault();
        if (filtered[selectedIndex]) {
          filtered[selectedIndex].action();
        }
      } else if (e.key === 'Escape') {
        e.preventDefault();
        onClose();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, filtered, selectedIndex, onClose]);

  // Prevent scroll when open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = 'unset';
    }
    return () => { document.body.style.overflow = 'unset'; };
  }, [isOpen]);

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-[100] flex items-start justify-center pt-[12vh] px-4">
          {/* Backdrop Blur */}
          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/60 backdrop-blur-md"
            onClick={onClose}
          />

          {/* Palette Dialog */}
          <motion.div 
            initial={{ opacity: 0, scale: 0.96, y: -8 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.96, y: -8 }}
            transition={{ duration: 0.15, ease: 'easeOut' }}
            ref={containerRef}
            className="relative w-full max-w-[600px] bg-bg-surface border border-border-hairline rounded-xl shadow-floating overflow-hidden z-10"
          >
            {/* Search Input Area */}
            <div className="flex items-center px-4 border-b border-border-hairline bg-bg-primary/30">
              <Search className="text-text-secondary shrink-0" size={18} />
              <input
                ref={inputRef}
                type="text"
                placeholder="Type a command or navigate..."
                value={query}
                onChange={e => setQuery(e.target.value)}
                className="w-full h-12 px-3 bg-transparent border-none outline-none text-text-primary text-sm placeholder:text-text-secondary/70 focus:ring-0 focus:outline-none"
              />
              <kbd className="hidden sm:inline-flex items-center h-5 px-1.5 rounded border border-border-hairline bg-bg-primary text-[10px] font-mono text-text-secondary font-bold gap-0.5">
                ESC
              </kbd>
            </div>

            {/* Results List */}
            <div className="max-h-[340px] overflow-y-auto p-2 space-y-1">
              {filtered.length === 0 ? (
                <div className="py-8 text-center text-xs text-text-secondary">
                  No commands found matching "{query}"
                </div>
              ) : (
                filtered.map((cmd, idx) => {
                  const isSelected = idx === selectedIndex;
                  return (
                    <button
                      key={cmd.id}
                      onClick={cmd.action}
                      className={`w-full flex items-center justify-between px-3.5 py-3 rounded-lg text-left transition-colors ${
                        isSelected 
                          ? 'bg-col-primary/10 text-primary-blue border border-col-primary/20' 
                          : 'text-text-secondary hover:bg-col-hover/40 border border-transparent'
                      }`}
                    >
                      <div className="flex items-center gap-3">
                        <div className={`p-1.5 rounded-md ${
                          isSelected ? 'bg-primary-blue/20 text-primary-blue' : 'bg-bg-primary text-text-secondary'
                        }`}>
                          {cmd.icon}
                        </div>
                        <div className="flex flex-col">
                          <span className={`text-xs font-semibold ${isSelected ? 'text-text-primary' : 'text-text-primary/90'}`}>
                            {cmd.title}
                          </span>
                          <span className="text-[9px] text-text-secondary uppercase tracking-wider mt-0.5">
                            {cmd.category}
                          </span>
                        </div>
                      </div>

                      {cmd.shortcut && (
                        <div className="flex items-center gap-1">
                          {cmd.shortcut.map(key => (
                            <kbd 
                              key={key} 
                              className={`inline-flex items-center justify-center min-w-[16px] h-5 px-1 rounded text-[10px] font-mono font-bold border ${
                                isSelected 
                                  ? 'border-primary-blue/30 bg-primary-blue/10 text-primary-blue' 
                                  : 'border-border-hairline bg-bg-primary text-text-secondary'
                              }`}
                            >
                              {key}
                            </kbd>
                          ))}
                        </div>
                      )}
                    </button>
                  );
                })
              )}
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
