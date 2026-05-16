import { useState } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import Header from './components/Header.tsx';
import Dashboard from './components/Dashboard.tsx';

const queryClient = new QueryClient();

function App() {
  const [activeTab, setActiveTab] = useState('Overview');

  return (
    <QueryClientProvider client={queryClient}>
      <div className="min-h-screen bg-background flex flex-col">
        <Header activeTab={activeTab} setActiveTab={setActiveTab} />
        <main className="flex-1 max-w-7xl mx-auto w-full px-4 py-8">
          <Dashboard activeTab={activeTab} />
        </main>
      </div>
    </QueryClientProvider>
  );
}

export default App;
