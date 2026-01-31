import React, { useEffect, useState } from 'react';
import { toolsApi } from '../api/client';
import type { Tool } from '../api/client';
import { 
  FileArchive, 
  CheckCircle, 
  Minimize2, 
  Tags,
  ArrowRight,
  Loader2
} from 'lucide-react';

const iconMap: Record<string, any> = {
  'file-archive-o': FileArchive,
  'check-circle': CheckCircle,
  'compress': Minimize2,
  'tags': Tags,
};

const Dashboard: React.FC = () => {
  const [tools, setTools] = useState<Tool[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    toolsApi.list().then(data => {
      setTools(data);
      setLoading(false);
    });
  }, []);

  return (
    <div className="space-y-8 animate-in fade-in duration-700">
      <div>
        <h1 className="text-4xl font-black text-white tracking-tight">Dashboard</h1>
        <p className="text-slate-400 mt-2 text-lg">Welcome to Drive Scripts Web. Select a tool to begin.</p>
      </div>

      {loading ? (
        <div className="flex justify-center py-20">
          <Loader2 className="animate-spin text-sky-500" size={48} />
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {tools.map(tool => {
            const Icon = iconMap[tool.icon] || FileArchive;
            return (
              <a 
                key={tool.id}
                href={`#/${tool.id}`}
                className="group bg-slate-800 rounded-3xl p-8 border border-slate-700 hover:border-sky-500/50 hover:bg-slate-800/80 transition-all duration-300 shadow-xl hover:shadow-sky-500/10 relative overflow-hidden"
              >
                <div className="absolute top-0 right-0 p-8 opacity-5 group-hover:opacity-10 transition-opacity">
                  <Icon size={120} />
                </div>
                
                <div className="relative z-10">
                  <div className={`inline-flex p-4 rounded-2xl mb-6 shadow-lg ${
                    tool.id === 'extract' ? 'bg-sky-500/20 text-sky-400' :
                    tool.id === 'verify' ? 'bg-indigo-500/20 text-indigo-400' :
                    tool.id === 'compress' ? 'bg-amber-500/20 text-amber-400' :
                    'bg-emerald-500/20 text-emerald-400'
                  }`}>
                    <Icon size={32} />
                  </div>
                  
                  <h3 className="text-2xl font-bold text-white mb-3 group-hover:text-sky-400 transition-colors">
                    {tool.title}
                  </h3>
                  <p className="text-slate-400 leading-relaxed mb-6">
                    {tool.description}
                  </p>
                  
                  <div className="flex items-center text-sm font-bold text-sky-500">
                    Open Tool <ArrowRight size={16} className="ml-2 group-hover:translate-x-1 transition-transform" />
                  </div>
                </div>
              </a>
            );
          })}
        </div>
      )}
      
      <div className="bg-slate-800/50 rounded-3xl p-8 border border-slate-700/50">
        <h3 className="text-xl font-bold text-white mb-4">Quick Stats</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
          <div className="p-4 rounded-2xl bg-slate-900/50">
            <div className="text-2xl font-black text-white">4</div>
            <div className="text-xs text-slate-500 uppercase tracking-widest mt-1">Tools</div>
          </div>
          <div className="p-4 rounded-2xl bg-slate-900/50">
            <div className="text-2xl font-black text-white">Ready</div>
            <div className="text-xs text-slate-500 uppercase tracking-widest mt-1">Drive Status</div>
          </div>
          <div className="p-4 rounded-2xl bg-slate-900/50">
            <div className="text-2xl font-black text-white">Local</div>
            <div className="text-xs text-slate-500 uppercase tracking-widest mt-1">Storage</div>
          </div>
          <div className="p-4 rounded-2xl bg-slate-900/50">
            <div className="text-2xl font-black text-white">v2.0</div>
            <div className="text-xs text-slate-500 uppercase tracking-widest mt-1">Version</div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
