import React, { useState, useEffect } from 'react';
import { filesApi } from '../api/client';
import type { FileItem, FileConfig } from '../api/client';
import { Folder, File, ChevronLeft, Check, Square, CheckSquare } from 'lucide-react';

interface FileSelectorProps {
  onSelect: (paths: string[]) => void;
  multi?: boolean;
  filter?: (file: FileItem) => boolean;
}

const FileSelector: React.FC<FileSelectorProps> = ({ onSelect, multi = false, filter }) => {
  const [currentPath, setCurrentPath] = useState('');
  const [items, setItems] = useState<FileItem[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(false);
  const [config, setConfig] = useState<FileConfig | null>(null);

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

  const toggleSelect = (path: string) => {
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

  return (
    <div className="bg-slate-800 rounded-xl border border-slate-700 flex flex-col h-96 shadow-lg overflow-hidden">
      <div className="px-4 py-3 border-b border-slate-700 bg-slate-800/50 flex items-center justify-between">
        <div className="flex items-center space-x-2 overflow-hidden mr-4">
          <button 
            onClick={goBack}
            className="p-1 hover:bg-slate-700 rounded transition-colors"
            title="Go Back"
          >
            <ChevronLeft size={20} />
          </button>
          <div className="text-xs font-mono text-slate-400 truncate">
            {currentPath.replace(config?.drive_root || '', 'Drive')}
          </div>
        </div>
        
        {multi && (
          <div className="flex space-x-2">
            <button onClick={selectAll} className="text-[10px] px-2 py-1 bg-slate-700 hover:bg-slate-600 rounded uppercase font-bold tracking-wider transition-colors">All</button>
            <button onClick={selectNone} className="text-[10px] px-2 py-1 bg-slate-700 hover:bg-slate-600 rounded uppercase font-bold tracking-wider transition-colors">None</button>
          </div>
        )}
      </div>

      <div className="flex-1 overflow-y-auto">
        {loading ? (
          <div className="h-full flex items-center justify-center">
            <Loader2 className="animate-spin text-slate-500" />
          </div>
        ) : (
          <div className="divide-y divide-slate-700/50">
            {items.map(item => (
              <div 
                key={item.path}
                className={`flex items-center px-4 py-2 hover:bg-slate-700/50 transition-colors cursor-pointer ${
                  selected.has(item.path) ? 'bg-sky-900/20' : ''
                }`}
                onClick={() => item.is_dir ? setCurrentPath(item.path) : toggleSelect(item.path)}
              >
                <div className="mr-3">
                  {item.is_dir ? (
                    <Folder className="text-amber-400" size={18} />
                  ) : (
                    multi ? (
                      selected.has(item.path) ? 
                        <CheckSquare className="text-sky-500" size={18} /> : 
                        <Square className="text-slate-600" size={18} />
                    ) : (
                      <File className="text-slate-400" size={18} />
                    )
                  )}
                </div>
                
                <div className="flex-1 min-w-0">
                  <div className={`text-sm truncate ${selected.has(item.path) ? 'text-sky-300 font-medium' : 'text-slate-200'}`}>
                    {item.name}
                  </div>
                  {item.size_str && (
                    <div className="text-[10px] text-slate-500">{item.size_str}</div>
                  )}
                </div>

                {!item.is_dir && !multi && selected.has(item.path) && (
                  <Check className="text-sky-500" size={16} />
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

const Loader2 = ({ className }: { className?: string }) => (
  <svg className={className} xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 12a9 9 0 1 1-6.219-8.56"/></svg>
);

export default FileSelector;
