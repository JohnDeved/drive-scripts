import React, { useEffect, useState } from 'react';
import { toolsApi } from '../api/client';
import type { Tool } from '../api/client';
import { 
  FileArchive, 
  CheckCircle, 
  Minimize2, 
  Tags, 
  Home,
  Loader2
} from 'lucide-react';

const iconMap: Record<string, any> = {
  'file-archive-o': FileArchive,
  'check-circle': CheckCircle,
  'compress': Minimize2,
  'tags': Tags,
};

const Sidebar: React.FC = () => {
  const [tools, setTools] = useState<Tool[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeId, setActiveId] = useState<string>('');

  useEffect(() => {
    toolsApi.list().then(data => {
      setTools(data);
      setLoading(false);
    });
    
    // Simple path tracking
    const path = window.location.hash.replace('#/', '');
    setActiveId(path);
    
    const handleHashChange = () => {
      const newPath = window.location.hash.replace('#/', '');
      setActiveId(newPath);
    };
    
    window.addEventListener('hashchange', handleHashChange);
    return () => window.removeEventListener('hashchange', handleHashChange);
  }, []);

  return (
    <aside className="w-64 bg-slate-800 border-r border-slate-700 flex flex-col">
      <div className="p-6 border-b border-slate-700">
        <h1 className="text-xl font-bold bg-gradient-to-r from-sky-400 to-indigo-400 bg-clip-text text-transparent">
          Drive Scripts
        </h1>
        <p className="text-xs text-slate-400 mt-1">Colab Web GUI</p>
      </div>
      
      <nav className="flex-1 p-4 space-y-2 overflow-y-auto">
        <a 
          href="#/"
          className={`flex items-center space-x-3 px-3 py-2 rounded-lg transition-colors ${
            activeId === '' ? 'bg-sky-600 text-white' : 'text-slate-300 hover:bg-slate-700'
          }`}
        >
          <Home size={20} />
          <span>Dashboard</span>
        </a>
        
        <div className="pt-4 pb-2 px-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">
          Tools
        </div>
        
        {loading ? (
          <div className="flex justify-center py-4">
            <Loader2 className="animate-spin text-slate-500" />
          </div>
        ) : (
          tools.map(tool => {
            const Icon = iconMap[tool.icon] || FileArchive;
            return (
              <a
                key={tool.id}
                href={`#/${tool.id}`}
                className={`flex items-center space-x-3 px-3 py-2 rounded-lg transition-colors ${
                  activeId === tool.id ? 'bg-sky-600 text-white' : 'text-slate-300 hover:bg-slate-700'
                }`}
              >
                <Icon size={20} />
                <span>{tool.title}</span>
              </a>
            );
          })
        )}
      </nav>
      
      <div className="p-4 border-t border-slate-700 text-xs text-slate-500">
        v2.0.0-web
      </div>
    </aside>
  );
};

export default Sidebar;
