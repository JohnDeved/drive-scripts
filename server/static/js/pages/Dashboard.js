import { html, useState, useEffect } from '../lib.js';
import { toolsApi } from '../api.js';

const iconMap = {
  'file-archive-o': 'archive',
  'check-circle': 'check-circle',
  'compress': 'minimize-2',
  'tags': 'tags',
};

export default function Dashboard() {
  const [tools, setTools] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    toolsApi.list().then(data => {
      setTools(data);
      setLoading(false);
    });
  }, []);

  useEffect(() => {
    if (typeof lucide !== 'undefined') {
        lucide.createIcons();
    }
  }, [tools, loading]);

  return html`
    <div class="space-y-8 animate-fade-in">
      <div>
        <h1 class="text-4xl font-black text-white tracking-tight">Dashboard</h1>
        <p class="text-slate-400 mt-2 text-lg">Welcome to Drive Scripts Web. Select a tool to begin.</p>
      </div>

      ${loading ? html`
        <div class="flex justify-center py-20">
          <i data-lucide="loader-2" class="w-12 h-12 animate-spin text-sky-500"></i>
        </div>
      ` : html`
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          ${tools.map(tool => {
            const iconName = iconMap[tool.icon] || 'archive';
            return html`
              <a 
                key=${tool.id}
                href="#/${tool.id}"
                class="group bg-slate-800 rounded-3xl p-8 border border-slate-700 hover:border-sky-500/50 hover:bg-slate-800/80 transition-all duration-300 shadow-xl hover:shadow-sky-500/10 relative overflow-hidden"
              >
                <div class="absolute top-0 right-0 p-8 opacity-5 group-hover:opacity-10 transition-opacity">
                  <i data-lucide="${iconName}" class="w-32 h-32"></i>
                </div>
                
                <div class="relative z-10">
                  <div class="inline-flex p-4 rounded-2xl mb-6 shadow-lg ${
                    tool.id === 'extract' ? 'bg-sky-500/20 text-sky-400' :
                    tool.id === 'verify' ? 'bg-indigo-500/20 text-indigo-400' :
                    tool.id === 'compress' ? 'bg-amber-500/20 text-amber-400' :
                    'bg-emerald-500/20 text-emerald-400'
                  }">
                    <i data-lucide="${iconName}" class="w-8 h-8"></i>
                  </div>
                  
                  <h3 class="text-2xl font-bold text-white mb-3 group-hover:text-sky-400 transition-colors">
                    ${tool.title}
                  </h3>
                  <p class="text-slate-400 leading-relaxed mb-6">
                    ${tool.description}
                  </p>
                  
                  <div class="flex items-center text-sm font-bold text-sky-500">
                    Open Tool <i data-lucide="arrow-right" class="w-4 h-4 ml-2 group-hover:translate-x-1 transition-transform"></i>
                  </div>
                </div>
              </a>
            `;
          })}
        </div>
      `}
      
      <div class="bg-slate-800/50 rounded-3xl p-8 border border-slate-700/50">
        <h3 class="text-xl font-bold text-white mb-4">Quick Stats</h3>
        <div class="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
          <div class="p-4 rounded-2xl bg-slate-900/50">
            <div class="text-2xl font-black text-white">4</div>
            <div class="text-xs text-slate-500 uppercase tracking-widest mt-1">Tools</div>
          </div>
          <div class="p-4 rounded-2xl bg-slate-900/50">
            <div class="text-2xl font-black text-white">Ready</div>
            <div class="text-xs text-slate-500 uppercase tracking-widest mt-1">Drive Status</div>
          </div>
          <div class="p-4 rounded-2xl bg-slate-900/50">
            <div class="text-2xl font-black text-white">Local</div>
            <div class="text-xs text-slate-500 uppercase tracking-widest mt-1">Storage</div>
          </div>
          <div class="p-4 rounded-2xl bg-slate-900/50">
            <div class="text-2xl font-black text-white">v2.1</div>
            <div class="text-xs text-slate-500 uppercase tracking-widest mt-1">Version</div>
          </div>
        </div>
      </div>
    </div>
  `;
}
