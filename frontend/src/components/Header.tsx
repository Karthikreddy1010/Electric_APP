import { useState, useRef, useEffect } from 'react';
import { Activity, ChevronDown, LogOut, User, Settings, Zap } from 'lucide-react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext.tsx';
import HeaderStatus from './shared/HeaderStatus.tsx';

/** Route path → tab label mapping (Rev 3 navigation order). */
const TABS: { label: string; path: string }[] = [
  { label: 'Overview', path: '/overview' },
  { label: 'Bill Analysis', path: '/bill-analysis' },
  { label: 'Impact & Simulation', path: '/impact' },
  { label: 'Regional Insights', path: '/regional-insights' },
  { label: 'Forecast', path: '/forecast' },

  { label: 'Settings', path: '/settings' },
];

const Header = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleLogout = () => {
    setMenuOpen(false);
    logout();
    navigate('/login');
  };

  // Derive the active tab from the current route path
  const activeTab = TABS.find((t) => location.pathname.startsWith(t.path))?.label ?? '';

  // Avatar initials from user name
  const initials = user
    ? `${user.first_name?.[0] ?? ''}${user.last_name?.[0] ?? ''}`.toUpperCase() || 'U'
    : 'U';

  return (
    <header className="bg-bg-surface border-b border-border-hairline text-text-primary sticky top-0 z-50 transition-colors duration-300">
      <div className="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between gap-4">

        {/* Brand & Logo */}
        <button
          onClick={() => navigate('/overview')}
          className="flex items-center gap-3 shrink-0 group focus:outline-none"
          aria-label="Go to Overview"
        >
          <div className="w-8 h-8 rounded-[6px] flex items-center justify-center bg-bg-primary border border-border-hairline text-primary-blue group-hover:border-primary-blue transition-colors">
            <Activity size={16} />
          </div>
          <div className="flex flex-col">
            <span className="text-base font-bold tracking-tight font-sans text-text-primary">ElectricAI</span>
            <span className="text-[8px] tracking-wider uppercase font-mono text-text-secondary">Operational Intelligence</span>
          </div>
        </button>

        {/* Persistent Bill Metadata Strip */}
        <HeaderStatus />

        {/* Tab Navigation */}
        <nav className="hidden md:flex items-center gap-1 overflow-x-auto py-1" aria-label="Main navigation">
          {TABS.map((tab) => {
            const isActive = activeTab === tab.label;
            return (
              <button
                key={tab.label}
                id={`nav-${tab.label.toLowerCase().replace(/[^a-z0-9]/g, '-')}`}
                onClick={() => navigate(tab.path)}
                aria-current={isActive ? 'page' : undefined}
                className={`px-3 py-1.5 rounded-[6px] text-xs font-semibold transition-all shrink-0 ${
                  isActive
                    ? 'bg-bg-primary text-primary-blue border border-border-hairline'
                    : 'text-text-secondary border border-transparent hover:text-text-primary hover:bg-bg-primary/50'
                }`}
              >
                {tab.label}
              </button>
            );
          })}
        </nav>

        {/* Right Section: User Avatar */}
        <div className="flex items-center gap-4 shrink-0">

          {/* User Avatar Dropdown */}
          {user && (
            <div className="relative" ref={menuRef}>
              <button
                id="header-user-avatar"
                onClick={() => setMenuOpen((prev) => !prev)}
                aria-haspopup="true"
                aria-expanded={menuOpen}
                className="flex items-center gap-2 rounded-[6px] border border-border-hairline bg-bg-primary px-2 py-1.5 hover:border-text-secondary transition-all focus:outline-none focus:ring-1 focus:ring-primary-blue group"
              >
                {/* Avatar circle */}
                <div className="w-6 h-6 rounded-full bg-primary-blue/15 border border-primary-blue/30 flex items-center justify-center text-[10px] font-bold text-primary-blue">
                  {initials}
                </div>
                <span className="text-[11px] font-semibold text-text-primary hidden sm:block max-w-[80px] truncate">
                  {user.first_name} {user.last_name}
                </span>
                <ChevronDown
                  size={12}
                  className={`text-text-secondary transition-transform duration-200 ${menuOpen ? 'rotate-180' : ''}`}
                />
              </button>

              {/* Dropdown Menu */}
              {menuOpen && (
                <div className="absolute right-0 top-full mt-1.5 w-52 bg-bg-surface border border-border-hairline rounded-[8px] shadow-xl z-50 overflow-hidden animate-in">
                  {/* User info header */}
                  <div className="px-4 py-3 border-b border-border-hairline bg-bg-primary/50">
                    <p className="text-xs font-bold text-text-primary truncate">{user.first_name} {user.last_name}</p>
                    <p className="text-[10px] text-text-secondary truncate">{user.email}</p>
                    <div className="flex items-center gap-1 mt-1.5">
                      <Zap size={9} className="text-primary-blue" />
                      <span className="text-[9px] text-text-secondary font-mono">{user.utility_provider} · {user.zip_code}</span>
                    </div>
                  </div>

                  {/* Menu items */}
                  <div className="py-1">
                    <button
                      id="header-menu-profile"
                      onClick={() => { setMenuOpen(false); navigate('/settings'); }}
                      className="w-full flex items-center gap-3 px-4 py-2.5 text-xs text-text-secondary hover:text-text-primary hover:bg-bg-primary transition-all"
                    >
                      <User size={13} />
                      Profile & Preferences
                    </button>
                    <button
                      id="header-menu-settings"
                      onClick={() => { setMenuOpen(false); navigate('/settings'); }}
                      className="w-full flex items-center gap-3 px-4 py-2.5 text-xs text-text-secondary hover:text-text-primary hover:bg-bg-primary transition-all"
                    >
                      <Settings size={13} />
                      System Settings
                    </button>
                  </div>

                  {/* Logout */}
                  <div className="border-t border-border-hairline py-1">
                    <button
                      id="header-menu-logout"
                      onClick={handleLogout}
                      className="w-full flex items-center gap-3 px-4 py-2.5 text-xs text-energy-red hover:bg-energy-red/5 transition-all"
                    >
                      <LogOut size={13} />
                      Sign Out
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

      </div>
    </header>
  );
};

export default Header;
