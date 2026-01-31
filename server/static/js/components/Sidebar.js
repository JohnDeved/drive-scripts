import { html, useState, useEffect } from '../lib.js';
import { toolsApi } from '../api/client.js';

const iconMap = {
  'file-archive-o': 'archive',
  'check-circle': 'check-circle',
  'compress': 'minimize-2',
  'tags': 'tags',
};

export default function Sidebar() {
  const [tools, setTools] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeId, setActiveId] = useState('');

  useEffect(() => {
    toolsApi.list().then(data => {
      setTools(data);
      setLoading(false);
    });
    
    const handleHashChange = () => {
      const path = window.location.hash.replace('#/', '');
      setActiveId(path);
    };
    
    handleHashChange();
    window.addEventListener('hashchange', handleHashChange);
    return () => window.removeEventListener('hashchange', handleHashChange);
  }, []);

  useEffect(() => {
    if (typeof lucide !== 'undefined') {
        lucide.createIcons();
    }
  }, [tools, activeId, loading]);

  return html`
    <aside class="w-64 bg-slate-800 border-r border-slate-700 flex flex-col h-full">
      <div class="p-6 border-b border-slate-700">
        <h1 class="text-xl font-bold bg-gradient-to-r from-sky-400 to-indigo-400 bg-clip-text text-transparent">
          Drive Scripts
        </h1>
        <p class="text-xs text-slate-400 mt-1">Colab Web GUI</p>
      </div>
      
      <nav class="flex-1 p-4 space-y-2 overflow-y-auto">
        <a 
          href="#/"
          class="flex items-center space-x-3 px-3 py-2 rounded-lg transition-colors ${activeId === '' ? 'bg-sky-600 text-white' : 'text-slate-300 hover:bg-slate-700'}"
        >
          <i data-lucide="home" class="w-5 h-5"></i>
          <span>Dashboard</span>
        </a>
        
        <div class="pt-4 pb-2 px-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">
          Tools
        </div>
        
        ${loading ? html`
          <div class="flex justify-center py-4">
            <i data-lucide="loader-2" class="w-6 h-6 animate-spin text-slate-500"></i>
          </div>
        ` : tools.map(tool => {
            const iconName = iconMap[tool.icon] || 'archive';
            return html`
              <a
                key=${tool.id}
                href="#/${tool.id}"
                class="flex items-center space-x-3 px-3 py-2 rounded-lg transition-colors ${activeId === tool.id ? 'bg-sky-600 text-white' : 'text-slate-300 hover:bg-slate-700'}"
              >
                <i data-lucide="${iconName}" class="w-5 h-5"></i>
                <span>${tool.title}</span>
              </a>
            `;
        })}
      </nav>
      
      <div class="p-4 border-t border-slate-700 text-xs text-slate-500">
        v2.1.0-preact
      </div>
    </aside>
  `;
}
