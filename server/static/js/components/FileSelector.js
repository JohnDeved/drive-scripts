import { html, useState, useEffect } from '../lib.js';
import { filesApi } from '../api.js';

export default function FileSelector({ onSelect, multi = false, filter }) {
  const [currentPath, setCurrentPath] = useState('');
  const [items, setItems] = useState([]);
  const [selected, setSelected] = useState(new Set());
  const [loading, setLoading] = useState(false);
  const [config, setConfig] = useState(null);

  useEffect(() => {
    filesApi.getConfig().then(data => {
      setConfig(data);
      setCurrentPath(data.shared_drives);
    });
  }, []);

  useEffect(() => {
    if (currentPath) {
      setLoading(true);
      filesApi.list(currentPath)
        .then(data => {
          setItems(filter ? data.filter(filter) : data);
          setLoading(false);
        })
        .catch(() => setLoading(false));
    }
  }, [currentPath, filter]);

  useEffect(() => {
    if (typeof lucide !== 'undefined') {
        lucide.createIcons();
    }
  }, [items, loading, selected]);

  const toggleSelect = (path) => {
    if (multi) {
      const newSelected = new Set(selected);
      if (newSelected.has(path)) newSelected.delete(path);
      else newSelected.add(path);
      setSelected(newSelected);
      onSelect(Array.from(newSelected));
    } else {
      setSelected(new Set([path]));
      onSelect([path]);
    }
  };

  const selectAll = () => {
    const filesOnly = items.filter(i => !i.is_dir).map(i => i.path);
    setSelected(new Set(filesOnly));
    onSelect(filesOnly);
  };

  const selectNone = () => {
    setSelected(new Set());
    onSelect([]);
  };

  const goBack = () => {
    const parts = currentPath.split('/');
    parts.pop();
    setCurrentPath(parts.join('/'));
  };

  return html`
    <div class="bg-slate-800 rounded-xl border border-slate-700 flex flex-col h-96 shadow-lg overflow-hidden">
      <div class="px-4 py-3 border-b border-slate-700 bg-slate-800/50 flex items-center justify-between">
        <div class="flex items-center space-x-2 overflow-hidden mr-4">
          <button 
            onClick=${goBack}
            class="p-1 hover:bg-slate-700 rounded transition-colors"
            title="Go Back"
          >
            <i data-lucide="chevron-left" class="w-5 h-5"></i>
          </button>
          <div class="text-xs font-mono text-slate-400 truncate">
            ${currentPath.replace(config?.drive_root || '', 'Drive')}
          </div>
        </div>
        
        ${multi ? html`
          <div class="flex space-x-2">
            <button onClick=${selectAll} class="text-[10px] px-2 py-1 bg-slate-700 hover:bg-slate-600 rounded uppercase font-bold tracking-wider transition-colors">All</button>
            <button onClick=${selectNone} class="text-[10px] px-2 py-1 bg-slate-700 hover:bg-slate-600 rounded uppercase font-bold tracking-wider transition-colors">None</button>
          </div>
        ` : ''}
      </div>

      <div class="flex-1 overflow-y-auto">
        ${loading ? html`
          <div class="h-full flex items-center justify-center">
            <i data-lucide="loader-2" class="w-8 h-8 animate-spin text-slate-500"></i>
          </div>
        ` : html`
          <div class="divide-y divide-slate-700/50">
            ${items.map(item => html`
              <div 
                key=${item.path}
                class="flex items-center px-4 py-2 hover:bg-slate-700/50 transition-colors cursor-pointer ${selected.has(item.path) ? 'bg-sky-900/20' : ''}"
                onClick=${() => item.is_dir ? setCurrentPath(item.path) : toggleSelect(item.path)}
              >
                <div class="mr-3">
                  ${item.is_dir ? html`
                    <i data-lucide="folder" class="w-5 h-5 text-amber-400"></i>
                  ` : (
                    multi ? html`
                      <i data-lucide="${selected.has(item.path) ? 'check-square' : 'square'}" class="w-5 h-5 ${selected.has(item.path) ? 'text-sky-500' : 'text-slate-600'}"></i>
                    ` : html`
                      <i data-lucide="file" class="w-5 h-5 text-slate-400"></i>
                    `
                  )}
                </div>
                
                <div class="flex-1 min-w-0">
                  <div class="text-sm truncate ${selected.has(item.path) ? 'text-sky-300 font-medium' : 'text-slate-200'}">
                    ${item.name}
                  </div>
                  ${item.size_str ? html`
                    <div class="text-[10px] text-slate-500">${item.size_str}</div>
                  ` : ''}
                </div>

                ${!item.is_dir && !multi && selected.has(item.path) ? html`
                  <i data-lucide="check" class="w-4 h-4 text-sky-500"></i>
                ` : ''}
              </div>
            `)}
          </div>
        `}
      </div>
    </div>
  `;
}
