import React, { useState } from 'react';
import FileSelector from '../components/FileSelector';
import ProgressBar from '../components/ProgressBar';
import LogOutput from '../components/LogOutput';
import { organizeApi } from '../api/client';
import { useSSE } from '../hooks/useSSE';
import { Tags, Play, CheckCircle2, AlertCircle, ArrowRight } from 'lucide-react';

const Organize: React.FC = () => {
  const [selectedFiles, setSelectedFiles] = useState<string[]>([]);
  const [jobId, setJobId] = useState<string | null>(null);
  const { progress, logs, isComplete, error, confirmRequest, reset } = useSSE(jobId, 'organize');

  const handleStart = async () => {
    if (selectedFiles.length === 0) return;
    try {
      reset();
      const res = await organizeApi.start(selectedFiles);
      setJobId(res.job_id);
    } catch (e: any) {
      console.error(e);
    }
  };

  const handleConfirm = async (apply: boolean) => {
    if (!jobId) return;
    try {
      await organizeApi.confirm(jobId, apply);
    } catch (e: any) {
      console.error(e);
    }
  };

  const handleNew = () => {
    setJobId(null);
    setSelectedFiles([]);
    reset();
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center space-x-3">
        <div className="p-3 bg-emerald-500/10 rounded-xl text-emerald-400">
          <Tags size={24} />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-white">Organize & Rename</h1>
          <p className="text-slate-400">Rename files based on TitleDB (Name [TitleID] [vVersion])</p>
        </div>
      </div>

      {!jobId ? (
        <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
          <div className="bg-slate-800 rounded-2xl p-6 border border-slate-700 shadow-xl">
            <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-4">Select Files to Organize</h2>
            <FileSelector 
              multi
              onSelect={setSelectedFiles} 
              filter={(f) => f.is_dir || [ '.nsp', '.nsz', '.xci', '.xcz' ].some(ext => f.name.toLowerCase().endsWith(ext))}
            />
            
            <div className="mt-8 flex justify-between items-center">
              <div className="text-sm text-slate-400">
                {selectedFiles.length} files selected
              </div>
              <button
                disabled={selectedFiles.length === 0}
                onClick={handleStart}
                className={`flex items-center space-x-2 px-6 py-3 rounded-xl font-bold transition-all ${
                  selectedFiles.length > 0 
                    ? 'bg-emerald-500 hover:bg-emerald-400 text-white shadow-lg shadow-emerald-500/20' 
                    : 'bg-slate-700 text-slate-500 cursor-not-allowed'
                }`}
              >
                <Play size={20} fill="currentColor" />
                <span>Analyze Files</span>
              </button>
            </div>
          </div>
        </div>
      ) : (
        <div className="space-y-6 animate-in fade-in duration-500">
          {progress && (
            <ProgressBar 
              percent={progress.percent || 0}
              step={progress.step}
              message={progress.message}
              total={progress.total}
              current={progress.current}
            />
          )}

          {confirmRequest && (
            <div className="bg-slate-800 rounded-2xl border border-slate-700 shadow-xl overflow-hidden animate-in zoom-in-95 duration-300">
              <div className="p-6 border-b border-slate-700 bg-slate-800/50">
                <h3 className="text-xl font-bold text-white flex items-center">
                  Proposed Changes
                  <span className="ml-3 text-xs bg-emerald-500/20 text-emerald-400 px-2 py-1 rounded-full uppercase tracking-widest font-black">
                    {confirmRequest.plan.length} renames
                  </span>
                </h3>
              </div>
              
              <div className="max-h-96 overflow-y-auto divide-y divide-slate-700/50">
                {confirmRequest.plan.map((item: any, i: number) => (
                  <div key={i} className="p-4 space-y-2">
                    <div className="text-xs text-rose-400 font-mono truncate opacity-60 line-through">{item.old_name}</div>
                    <div className="flex items-center space-x-2">
                      <ArrowRight size={14} className="text-slate-500" />
                      <div className="text-sm text-emerald-400 font-bold truncate">{item.new_name}</div>
                    </div>
                  </div>
                ))}
              </div>

              <div className="p-6 bg-slate-900/30 flex space-x-4">
                <button
                  onClick={() => handleConfirm(true)}
                  className="flex-1 py-3 bg-emerald-600 hover:bg-emerald-500 text-white font-bold rounded-xl transition-colors shadow-lg shadow-emerald-600/20"
                >
                  Apply Changes
                </button>
                <button
                  onClick={() => handleConfirm(false)}
                  className="flex-1 py-3 bg-slate-700 hover:bg-slate-600 text-white font-bold rounded-xl transition-colors"
                >
                  Discard
                </button>
              </div>
            </div>
          )}

          <LogOutput logs={logs} />

          {error && (
            <div className="p-4 bg-rose-500/10 border border-rose-500/20 rounded-xl flex items-center space-x-3 text-rose-400">
              <AlertCircle size={20} />
              <span>{error}</span>
            </div>
          )}

          {isComplete && (
            <div className="flex justify-between items-center p-6 bg-slate-800 rounded-2xl border border-slate-700 shadow-xl">
              <div className="flex items-center space-x-3 text-emerald-400">
                <CheckCircle2 size={24} />
                <span className="font-bold">Organization Finished</span>
              </div>
              <button
                onClick={handleNew}
                className="px-6 py-2 bg-slate-700 hover:bg-slate-600 text-white font-bold rounded-xl transition-colors"
              >
                New Session
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default Organize;
