import { useState, useEffect } from 'react';
import { useNavigate, useLocation, Link, Outlet } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext.tsx';
import { useBill } from '../../context/BillContext.tsx';
import { 
  ChevronLeft, ChevronRight, Search, Sun, Moon, 
  Brain, Layout, FileText, TrendingUp, Activity, Map, 
  Settings, LogOut, Sparkles 
} from 'lucide-react';
import CommandPalette from './CommandPalette.tsx';
import AIAssistantDrawer from './AIAssistantDrawer.tsx';

export default function WorkspaceShell() {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout } = useAuth();
  const { uploadedBill, hasBill } = useBill();
  
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [isCommandOpen, setIsCommandOpen] = useState(false);
  const [isAssistantOpen, setIsAssistantOpen] = useState(false);
  const [theme, setTheme] = useState<'dark' | 'light'>(() => {
    return (localStorage.getItem('workspace-theme') as 'dark' | 'light') || 'dark';
  });
  const [profileOpen, setProfileOpen] = useState(false);

  // Sync theme to body element
  useEffect(() => {
    const root = document.documentElement;
    const body = document.body;
    if (theme === 'light') {
      body.classList.add('light-theme');
      root.style.setProperty('color-scheme', 'light');
    } else {
      body.classList.remove('light-theme');
      root.style.setProperty('color-scheme', 'dark');
    }
    localStorage.setItem('workspace-theme', theme);
  }, [theme]);

  // Keyboard shortcut listener for Ctrl+K
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        setIsCommandOpen(prev => !prev);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const toggleTheme = () => {
    setTheme(prev => prev === 'dark' ? 'light' : 'dark');
  };

  const navItems = [
    { label: 'Overview', path: '/overview', icon: <Layout size={16} /> },
    { label: 'Bill Analysis', path: '/bill-analysis', icon: <FileText size={16} /> },
    { label: 'Impact Simulator', path: '/impact', icon: <TrendingUp size={16} /> },
    { label: 'Demand Forecast', path: '/forecast', icon: <Activity size={16} /> },
    { label: 'Regional Insights', path: '/regional-insights', icon: <Map size={16} /> },
    { label: 'Benchmark & Ranks', path: '/advanced-analysis', icon: <Sparkles size={16} /> },
    { label: 'Settings', path: '/settings', icon: <Settings size={16} /> },
  ];

  // Derive page breadcrumb
  const currentNav = navItems.find(item => location.pathname.startsWith(item.path));
  const breadcrumb = currentNav ? currentNav.label : 'Workspace';

  // Compute initials
  const initials = user
    ? `${user.first_name?.[0] ?? ''}${user.last_name?.[0] ?? ''}`.toUpperCase() || 'U'
    : 'U';

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="flex min-h-screen bg-bg-primary text-text-primary overflow-hidden font-sans">
      {/* ─── FLOATING SIDEBAR ─── */}
      <aside 
        className={`workspace-glass border-r border-border-hairline shrink-0 flex flex-col transition-all duration-300 relative z-30 ${
          sidebarCollapsed ? 'w-16' : 'w-64'
        }`}
      >
        {/* Sidebar Header */}
        <div className="h-16 flex items-center justify-between px-4 border-b border-border-hairline bg-bg-primary/20">
          <Link to="/overview" className="flex items-center gap-3 shrink-0 group focus:outline-none cursor-pointer">
            <div className="w-8 h-8 rounded-lg flex items-center justify-center bg-bg-primary border border-border-hairline text-primary-blue group-hover:border-primary-blue transition-colors">
              <Activity size={16} />
            </div>
            {!sidebarCollapsed && (
              <div className="flex flex-col">
                <span className="text-sm font-bold tracking-tight text-text-primary">ElectricAI</span>
                <span className="text-[8px] tracking-wider uppercase font-mono text-text-secondary">Enterprise</span>
              </div>
            )}
          </Link>
          {!sidebarCollapsed && (
            <button 
              onClick={() => setSidebarCollapsed(true)}
              className="p-1 rounded-md text-text-secondary hover:text-text-primary hover:bg-col-hover transition-colors cursor-pointer"
              title="Collapse Sidebar"
            >
              <ChevronLeft size={16} />
            </button>
          )}
        </div>

        {/* Workspace Selector */}
        {!sidebarCollapsed && (
          <div className="px-3 py-4 border-b border-border-hairline bg-bg-primary/10">
            <div className="flex items-center justify-between p-2 rounded-lg bg-bg-surface/50 border border-border-hairline">
              <div className="flex items-center gap-2">
                <div className="w-2.5 h-2.5 rounded-full bg-primary-blue animate-pulse" />
                <span className="text-xs font-bold text-text-primary truncate max-w-[140px]">
                  {user?.utility_provider || 'Main Workspace'}
                </span>
              </div>
              <Sparkles size={11} className="text-warning-amber shrink-0" />
            </div>
          </div>
        )}

        {/* Navigation items */}
        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
          {navItems.map(item => {
            const isActive = location.pathname.startsWith(item.path);
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-xs font-semibold relative transition-all cursor-pointer ${
                  isActive 
                    ? 'text-primary-blue bg-primary-blue/10 border border-primary-blue/20 shadow-sm' 
                    : 'text-text-secondary hover:text-text-primary hover:bg-col-hover border border-transparent'
                }`}
              >
                <span className={isActive ? 'text-primary-blue' : 'text-text-secondary'}>
                  {item.icon}
                </span>
                {!sidebarCollapsed && <span>{item.label}</span>}
              </Link>
            );
          })}
        </nav>

        {/* Sidebar Footer / Collapse Expand Trigger */}
        <div className="p-3 border-t border-border-hairline bg-bg-primary/20 flex flex-col gap-2">
          {sidebarCollapsed && (
            <button 
              onClick={() => setSidebarCollapsed(false)}
              className="w-full p-2 rounded-lg text-text-secondary hover:text-text-primary hover:bg-col-hover flex items-center justify-center transition-colors cursor-pointer"
              title="Expand Sidebar"
            >
              <ChevronRight size={16} />
            </button>
          )}
          
          {/* Theme switcher inside sidebar footer if collapsed */}
          {!sidebarCollapsed && (
            <div className="flex items-center justify-between px-2 py-1.5 rounded-lg bg-bg-surface/50 border border-border-hairline">
              <span className="text-[10px] text-text-secondary font-semibold">Theme</span>
              <button 
                onClick={toggleTheme}
                className="p-1 rounded-md text-text-secondary hover:text-text-primary transition-all cursor-pointer"
                title="Toggle Theme"
              >
                {theme === 'dark' ? <Sun size={14} /> : <Moon size={14} />}
              </button>
            </div>
          )}
        </div>
      </aside>

      {/* ─── MAIN APP CANVAS ─── */}
      <div className="flex-1 flex flex-col overflow-hidden relative">
        {/* ─── WORKSPACE HEADER ─── */}
        <header className="h-16 border-b border-border-hairline workspace-glass shrink-0 flex items-center justify-between px-6 z-20">
          {/* Left: Breadcrumbs */}
          <div className="flex items-center gap-2 text-xs font-semibold text-text-secondary">
            <span>ElectricAI</span>
            <span>/</span>
            <span className="text-text-primary font-bold">{breadcrumb}</span>
          </div>

          {/* Center: Command Palette Trigger */}
          <button 
            onClick={() => setIsCommandOpen(true)}
            className="hidden md:flex items-center justify-between w-64 px-3 py-1.5 rounded-lg border border-border-hairline bg-bg-primary/50 hover:bg-bg-primary/95 text-text-secondary transition-all cursor-pointer"
          >
            <span className="flex items-center gap-2 text-[11px] font-semibold">
              <Search size={13} />
              Search workspace...
            </span>
            <kbd className="inline-flex items-center h-5 px-1.5 rounded border border-border-hairline bg-bg-surface text-[9px] font-mono font-bold text-text-secondary">
              Ctrl K
            </kbd>
          </button>

          {/* Right: Telemetry strip + User + AI status */}
          <div className="flex items-center gap-4 shrink-0">
            {/* Header Metadata */}
            {hasBill && uploadedBill && (
              <div className="hidden lg:flex items-center gap-4 border-r border-border-hairline pr-4 text-xs font-semibold">
                <div className="flex flex-col text-right">
                  <span className="text-[8px] text-text-secondary uppercase">Utility</span>
                  <span className="text-text-primary font-bold truncate max-w-[80px]">{uploadedBill.utility}</span>
                </div>
                <div className="flex flex-col text-right border-l border-border-hairline pl-4">
                  <span className="text-[8px] text-text-secondary uppercase">Cycle</span>
                  <span className="text-text-primary">{uploadedBill.bill_date || uploadedBill.billing_period}</span>
                </div>
                <div className="flex flex-col text-right border-l border-border-hairline pl-4">
                  <span className="text-[8px] text-text-secondary uppercase">Effective Rate</span>
                  <span className="text-primary-blue font-bold">${uploadedBill.effective_rate?.toFixed(4)}/kWh</span>
                </div>
              </div>
            )}

            {/* AI Assistant Status Trigger */}
            <button 
              onClick={() => setIsAssistantOpen(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-primary-blue/30 bg-primary-blue/10 hover:bg-primary-blue/20 text-primary-blue text-xs font-bold transition-all shrink-0 active:scale-95 cursor-pointer"
            >
              <Brain size={13} className="animate-pulse" />
              <span>AI Assistant</span>
            </button>

            {/* Profile Dropdown */}
            {user && (
              <div className="relative">
                <button
                  onClick={() => setProfileOpen(prev => !prev)}
                  className="w-7 h-7 rounded-full bg-primary-blue/15 border border-primary-blue/30 flex items-center justify-center text-[10px] font-bold text-primary-blue hover:border-primary-blue/80 transition-all cursor-pointer focus:outline-none"
                >
                  {initials}
                </button>

                {profileOpen && (
                  <>
                    <div className="fixed inset-0 z-40" onClick={() => setProfileOpen(false)} />
                    <div className="absolute right-0 top-full mt-2 w-52 bg-bg-surface border border-border-hairline rounded-lg shadow-elevation z-50 overflow-hidden">
                      <div className="px-4 py-3 border-b border-border-hairline bg-bg-primary/50">
                        <p className="text-xs font-bold text-text-primary truncate">{user.first_name} {user.last_name}</p>
                        <p className="text-[9px] text-text-secondary truncate">{user.email}</p>
                      </div>
                      <div className="py-1">
                        <Link 
                          to="/settings" 
                          onClick={() => setProfileOpen(false)}
                          className="w-full flex items-center gap-3 px-4 py-2 text-xs text-text-secondary hover:text-text-primary hover:bg-col-hover transition-all"
                        >
                          <Settings size={13} />
                          Settings
                        </Link>
                        <button
                          onClick={handleLogout}
                          className="w-full flex items-center gap-3 px-4 py-2 text-xs text-alert-red hover:bg-alert-red/5 transition-all text-left"
                        >
                          <LogOut size={13} />
                          Sign Out
                        </button>
                      </div>
                    </div>
                  </>
                )}
              </div>
            )}
          </div>
        </header>

        {/* ─── PAGE ROUTING PORT ─── */}
        <main className="flex-1 overflow-y-auto p-6 md:p-8 max-w-7xl w-full mx-auto">
          {sessionStorage.getItem('is_demo_mode') === 'true' && (
            <div className="mb-4 bg-amber-500/10 border border-amber-500/20 text-amber-500 text-[10px] px-4 py-2 rounded-lg flex items-center gap-2 font-semibold">
              <span className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-ping" />
              <span>Demo Workspace — Read Only Mode. Sign up to save configurations.</span>
            </div>
          )}
          <Outlet />
        </main>
      </div>

      {/* ─── COMMAND PALETTE DIALOG ─── */}
      <CommandPalette 
        isOpen={isCommandOpen} 
        onClose={() => setIsCommandOpen(false)} 
        onThemeToggle={toggleTheme}
        currentTheme={theme}
      />

      {/* ─── AI ASSISTANT DRAWER ─── */}
      <AIAssistantDrawer 
        isOpen={isAssistantOpen} 
        onClose={() => setIsAssistantOpen(false)} 
      />
    </div>
  );
}
