import { createContext, useContext } from 'react';
import { useNavigate } from 'react-router-dom';

const NavigationContext = createContext<(tab: string) => void>(null!);

export const NavigationProvider = ({
  children,
}: {
  children: React.ReactNode;
}) => {
  const navigate = useNavigate();

  const navigateTab = (tab: string) => {
    if (!tab) return;
    if (tab.startsWith('/')) {
      navigate(tab);
      return;
    }
    const cleanTab = tab.trim().toLowerCase();
    const routeMap: Record<string, string> = {
      'overview': '/overview',
      'dashboard': '/overview',
      'bill analysis': '/bill-analysis',
      'bill': '/bill-analysis',
      'bill-analysis': '/bill-analysis',
      'billing': '/bill-analysis',
      'impact & simulation': '/impact',
      'impact simulator': '/impact',
      'impact': '/impact',
      'simulation': '/impact',
      'simulator': '/impact',
      'regional insights': '/regional-insights',
      'regional': '/regional-insights',
      'regional-insights': '/regional-insights',
      'forecast': '/forecast',
      'forecaste': '/forecast',
      'demand forecast': '/forecast',
      'demand forecasting': '/forecast',
      'load forecasting': '/forecast',
      'forecasting': '/forecast',
      'settings': '/settings',
    };
    const target = routeMap[cleanTab] ?? '/overview';
    navigate(target);
  };

  return (
    <NavigationContext.Provider value={navigateTab}>
      {children}
    </NavigationContext.Provider>
  );
};

export const useNavigation = () => {
  const ctx = useContext(NavigationContext);
  if (!ctx) throw new Error('useNavigation must be used within NavigationProvider');
  return ctx;
};
