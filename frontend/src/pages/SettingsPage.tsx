import React, { useState } from 'react';
import { Save, User, Zap, MapPin, CheckCircle2, AlertCircle } from 'lucide-react';
import { useAuth } from '../context/AuthContext.tsx';

const SettingsPage = () => {
  const { user, updateProfile } = useAuth();

  // ── Profile form state ────────────────────────────────────────────────────
  const [profile, setProfile] = useState(() => ({
    first_name: user?.first_name ?? '',
    last_name: user?.last_name ?? '',
    zip_code: user?.zip_code ?? '',
    utility_provider: user?.utility_provider ?? '',
  }));

  // ── Preferences state ────────────────────────────────────────────────────
  const [preferences, setPreferences] = useState(() => {
    const prefs = user?.preferences as Record<string, any> ?? {};
    return {
      dml_enabled: prefs.dml_enabled ?? true,
      llm_enabled: prefs.llm_enabled ?? true,
      ocr_animation_enabled: prefs.ocr_animation_enabled ?? true,
      notifications_enabled: prefs.notifications_enabled ?? true,
      theme: prefs.theme ?? 'dark',
    };
  });

  const [isSaving, setIsSaving] = useState(false);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' } | null>(null);

  const handleProfileChange = (key: keyof typeof profile, value: string) => {
    setProfile((prev) => ({ ...prev, [key]: value }));
  };

  const handlePrefToggle = (key: keyof typeof preferences) => {
    setPreferences((prev) => ({ ...prev, [key]: !(prev[key]) }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSaving(true);
    setMessage(null);
    try {
      await updateProfile({ ...profile, preferences });
      setMessage({ text: 'Settings saved successfully!', type: 'success' });
    } catch {
      setMessage({ text: 'Failed to save settings. Please try again.', type: 'error' });
    } finally {
      setIsSaving(false);
      setTimeout(() => setMessage(null), 4000);
    }
  };

  return (
    <div key={user?.id || 'guest'} className="max-w-4xl mx-auto space-y-8 animate-in fade-in duration-500 pb-16 font-sans">
      <div>
        <span className="bg-primary-blue/10 text-primary-blue text-xs font-semibold uppercase tracking-wider px-3 py-1 rounded-[6px]">
          Account Settings
        </span>
        <h1 className="text-3xl font-bold text-text-primary tracking-tight mt-2">
          Manage Account & Preferences
        </h1>
        <p className="text-text-secondary text-sm mt-1">
          Configure your personal energy dashboard, billing settings, and UI preferences.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">

        {/* ── Profile Section ─────────────────────────────────────────────── */}
        <div className="panel-operational space-y-5 bg-bg-surface border border-border-hairline shadow-sm p-6">
          <h3 className="text-sm font-bold text-text-primary border-b border-border-hairline pb-3 flex items-center gap-2">
            <User size={14} className="text-primary-blue" /> Profile Information
          </h3>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {[
              { key: 'first_name' as const, label: 'First Name', icon: null },
              { key: 'last_name' as const,  label: 'Last Name',  icon: null },
            ].map(({ key, label }) => (
              <div key={key} className="space-y-1.5">
                <label className="text-[10px] font-bold uppercase tracking-wider text-text-secondary block">
                  {label}
                </label>
                <input
                  type="text"
                  value={profile[key]}
                  onChange={(e) => handleProfileChange(key, e.target.value)}
                  className="w-full bg-bg-primary border border-border-hairline hover:border-text-secondary px-3 py-2.5 rounded-md focus:outline-none focus:border-primary-blue transition-all text-xs text-text-primary"
                />
              </div>
            ))}
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label className="text-[10px] font-bold uppercase tracking-wider text-text-secondary flex items-center gap-1">
                <MapPin size={10} /> ZIP Code
              </label>
              <input
                type="text"
                value={profile.zip_code}
                onChange={(e) => handleProfileChange('zip_code', e.target.value)}
                placeholder="e.g. 07102"
                className="w-full bg-bg-primary border border-border-hairline hover:border-text-secondary px-3 py-2.5 rounded-md focus:outline-none focus:border-primary-blue transition-all text-xs text-text-primary"
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-[10px] font-bold uppercase tracking-wider text-text-secondary flex items-center gap-1">
                <Zap size={10} /> Utility Provider
              </label>
              <select
                value={profile.utility_provider}
                onChange={(e) => handleProfileChange('utility_provider', e.target.value)}
                className="w-full bg-bg-primary border border-border-hairline hover:border-text-secondary px-3 py-2.5 rounded-md focus:outline-none focus:border-primary-blue transition-all text-xs text-text-primary"
              >
                <option value="">Select utility…</option>
                <option value="PSE&G">PSE&G (Public Service Electric & Gas)</option>
                <option value="JCP&L">JCP&L (Jersey Central Power & Light)</option>
                <option value="Atlantic City Electric">Atlantic City Electric</option>
                <option value="Rockland Electric">Rockland Electric Company</option>
              </select>
            </div>
          </div>

          {user && (
            <p className="text-[10px] text-text-secondary font-mono">
              Account: {user.email} · Role: {user.role} · Member since {user.created_at?.slice(0, 10) ?? '—'}
            </p>
          )}
        </div>

        {/* ── Assistant & UI Preferences ───────────────────────────────────── */}
        <div className="panel-operational space-y-6 bg-bg-surface border border-border-hairline shadow-sm p-6">
          <h3 className="text-sm font-bold text-text-primary border-b border-border-hairline pb-3">
            Assistant & UI Preferences
          </h3>

          <div className="space-y-4">
            {[
              {
                key: 'dml_enabled' as const,
                title: 'Double Machine Learning (DML)',
                desc: 'Enable causal impact modeling using EconML/DoWhy estimators.',
              },
              {
                key: 'llm_enabled' as const,
                title: 'Local LLM Explanations',
                desc: 'Run plain-language bill explanations on local Ollama server.',
              },
              {
                key: 'ocr_animation_enabled' as const,
                title: 'OCR Scanning Sweeps',
                desc: 'Show real-time sweep scanline animations on bill uploads.',
              },
              {
                key: 'notifications_enabled' as const,
                title: 'In-App Notifications',
                desc: 'Get notified of weather alerts, cheaper pricing tiers, and new bills.',
              },
            ].map((pref) => (
              <div
                key={pref.key}
                className="flex items-center justify-between p-3 bg-bg-primary rounded-md border border-border-hairline shadow-sm"
              >
                <div>
                  <h4 className="text-xs font-bold text-text-primary">{pref.title}</h4>
                  <p className="text-[10px] text-text-secondary mt-0.5">{pref.desc}</p>
                </div>
                <input
                  type="checkbox"
                  checked={preferences[pref.key] as boolean}
                  onChange={() => handlePrefToggle(pref.key)}
                  className="w-4 h-4 accent-primary-blue rounded bg-bg-surface border-border-hairline cursor-pointer"
                  aria-label={`Toggle ${pref.title}`}
                />
              </div>
            ))}

            <div className="flex items-center justify-between p-3 bg-bg-primary rounded-md border border-border-hairline shadow-sm">
              <div>
                <h4 className="text-xs font-bold text-text-primary">Theme Selection</h4>
                <p className="text-[10px] text-text-secondary mt-0.5">Toggle between dark mode and light theme options.</p>
              </div>
              <select
                value={preferences.theme}
                onChange={(e) =>
                  setPreferences((prev) => ({ ...prev, theme: e.target.value }))
                }
                className="bg-bg-surface border border-border-hairline px-3 py-1 rounded text-xs text-text-primary outline-none"
                aria-label="Theme Selection"
              >
                <option value="dark">Dark Theme</option>
                <option value="light">Light Theme</option>
              </select>
            </div>
          </div>
        </div>

        {/* ── Save Bar ─────────────────────────────────────────────────────── */}
        <div className="flex items-center justify-between">
          <div>
            {message && (
              <span
                className={`flex items-center gap-1.5 text-xs font-bold ${
                  message.type === 'success' ? 'text-savings-green' : 'text-energy-red'
                }`}
              >
                {message.type === 'success' ? (
                  <CheckCircle2 size={13} />
                ) : (
                  <AlertCircle size={13} />
                )}
                {message.text}
              </span>
            )}
          </div>
          <button
            type="submit"
            disabled={isSaving}
            className="flex items-center gap-1.5 bg-primary-blue hover:bg-primary-blue/90 disabled:opacity-60 text-white font-bold px-5 py-2.5 rounded-[6px] text-xs transition-colors shadow-sm cursor-pointer"
          >
            <Save size={14} />
            {isSaving ? 'Saving…' : 'Save Settings'}
          </button>
        </div>
      </form>
    </div>
  );
};

export default SettingsPage;
