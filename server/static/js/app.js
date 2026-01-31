import { html, render, useState, useEffect } from './lib.js';
import Layout from './components/Layout.js';
import Dashboard from './pages/Dashboard.js';
import Extract from './pages/Extract.js';
import Verify from './pages/Verify.js';
import Compress from './pages/Compress.js';
import Organize from './pages/Organize.js';
import Demo from './pages/Demo.js';

function App() {
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
        return html`<${Dashboard} />`;
      case 'extract':
        return html`<${Extract} />`;
      case 'verify':
        return html`<${Verify} />`;
      case 'compress':
        return html`<${Compress} />`;
      case 'organize':
        return html`<${Organize} />`;
      case 'demo':
        return html`<${Demo} />`;
      default:
        return html`<${Dashboard} />`;
    }
  };

  return html`
    <${Layout}>
      ${renderPage()}
    <//>
  `;
}

// Render the app
render(html`<${App} />`, document.getElementById('root'));
