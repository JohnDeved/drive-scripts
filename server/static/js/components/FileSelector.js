import { html, useState, useEffect, useRef } from '../lib.js';
import { filesApi } from '../api.js';

export default function FileSelector({ onSelect, multi = false, filter }) {
  const [currentPath, setCurrentPath] = useState('');
  const [items, setItems] = useState([]);
  const [selected, setSelected] = useState(new Set());
  const [loading, setLoading] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);
  const [config, setConfig] = useState(null);

  useEffect(() => {
...
  useEffect(() => {
    if (currentPath) {
      setLoading(true);
      filesApi.list(currentPath)
        .then(data => {
          setItems(filter ? data.filter(filter) : data);
          setLoading(false);
        })
        .catch(err => {
          console.error('File listing error:', err);
          setLoading(false);
        });
    }
  }, [currentPath, filter, refreshKey]);


  useEffect(() => {
    if (typeof lucide !== 'undefined') {
        lucide.createIcons();
    }
  }, [items, loading, Array.from(selected).join(',')]);

  const toggleSelect = (path) => {
    const newSelected = new Set(selected);
    if (newSelected.has(path)) {
      newSelected.delete(path);
    } else {
      if (!multi) {
        newSelected.clear();
      }
      newSelected.add(path);
    }
    setSelected(newSelected);
    onSelect(Array.from(newSelected));
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
            class="p-1 hover:bg-slate-700 rounded transition-colors text-slate-400 hover:text-white"
            title="Go Back"
          >
            <div key="back-icon"><i data-lucide="chevron-left" class="w-5 h-5"></i></div>
          </button>
          
          <button 
            onClick=${() => setRefreshKey(k => k + 1)}
            class="p-1 hover:bg-slate-700 rounded transition-colors text-slate-400 hover:text-white"
            title="Refresh"
          >
            <div key="refresh-icon"><i data-lucide="refresh-cw" class="${loading ? 'animate-spin' : ''} w-4 h-4"></i></div>
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

      <div class="flex-1 overflow-y-auto min-h-[200px]">
        ${loading ? html`
          <div key="loader" class="h-full flex flex-col items-center justify-center py-10">
            <svg class="animate-spin h-10 w-10 text-sky-500 mb-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            <span class="text-slate-500 text-sm font-medium">Reading directory...</span>
          </div>
        ` : html`
          <div class="divide-y divide-slate-700/50">
            ${items.length === 0 ? html`
              <div class="p-12 text-center">
                <div class="inline-flex p-4 rounded-full bg-slate-700/30 mb-4">
                  <div key="empty-folder-icon"><i data-lucide="folder-open" class="w-8 h-8 text-slate-500"></i></div>
                </div>
                <p class="text-slate-400 font-medium">No supported files found here</p>
                <p class="text-slate-500 text-xs mt-1">Try navigating to another folder</p>
              </div>
            ` : items.map(item => html`
              <div 
                key=${item.path}
                class="flex items-center px-4 py-2 hover:bg-slate-700/50 transition-colors cursor-pointer ${selected.has(item.path) ? 'bg-sky-900/20' : ''}"
                onClick=${() => item.is_dir ? setCurrentPath(item.path) : toggleSelect(item.path)}
              >
                <div class="mr-3">
                  ${item.is_dir ? html`
                    <div key="dir-icon"><i data-lucide="folder" class="w-5 h-5 text-amber-400"></i></div>
                  ` : (
                    multi ? html`
                      <div class="w-5 h-5 flex items-center justify-center" key=${selected.has(item.path) ? 'checked' : 'unchecked'}>
                        <i data-lucide="${selected.has(item.path) ? 'check-square' : 'square'}" class="w-5 h-5 ${selected.has(item.path) ? 'text-sky-500' : 'text-slate-600'}"></i>
                      </div>
                    ` : html`
                      <div class="w-5 h-5 flex items-center justify-center" key="file-icon">
                        <i data-lucide="file" class="w-5 h-5 text-slate-400"></i>
                      </div>
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
                  <div class="w-5 h-5 flex items-center justify-center" key="check-icon">
                    <i data-lucide="check" class="w-4 h-4 text-sky-500"></i>
                  </div>
                ` : html`<div class="w-5 h-5" key="empty-icon"></div>`}
              </div>
            `)}
          </div>
        `}
      </div>
    </div>
  `;
}
