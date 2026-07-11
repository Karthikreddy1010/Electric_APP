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
    const routeMap: Record<string, string> = {
      'Overview': '/overview',
      'Bill Analysis': '/bill-analysis',
      'Impact & Simulation': '/impact',
      'Regional Insights': '/regional-insights',
      'Forecast': '/forecast',

      'Settings': '/settings',
    };
    const target = routeMap[tab] ?? '/overview';
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
