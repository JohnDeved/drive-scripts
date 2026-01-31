import React, { useState, useEffect } from 'react';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import Extract from './pages/Extract';
import Verify from './pages/Verify';
import Compress from './pages/Compress';
import Organize from './pages/Organize';

const App: React.FC = () => {
  const [currentPath, setCurrentPath] = useState(window.location.hash.replace('#/', ''));

  useEffect(() => {
    const handleHashChange = () => {
      setCurrentPath(window.location.hash.replace('#/', ''));
    };
    window.addEventListener('hashchange', handleHashChange);
    return () => window.removeEventListener('hashchange', handleHashChange);
  }, []);

  const renderPage = () => {
    switch (currentPath) {
      case '':
        return <Dashboard />;
      case 'extract':
        return <Extract />;
      case 'verify':
        return <Verify />;
      case 'compress':
        return <Compress />;
      case 'organize':
        return <Organize />;
      default:
        return <Dashboard />;
    }
  };

  return (
    <Layout>
      {renderPage()}
    </Layout>
  );
};

export default App;
