import React, { useState } from 'react';
import FileSelector from '../components/FileSelector';
import ProgressBar from '../components/ProgressBar';
import LogOutput from '../components/LogOutput';
import { extractApi } from '../api/client';
import { useSSE } from '../hooks/useSSE';
import { Zap, Play, CheckCircle2, AlertCircle } from 'lucide-react';

const Extract: React.FC = () => {
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const { progress, logs, isComplete, error, reset } = useSSE(jobId, 'extract');

  const handleStart = async () => {
    if (!selectedFile) return;
    try {
      reset();
      const res = await extractApi.start(selectedFile);
      setJobId(res.job_id);
    } catch (e: any) {
      console.error(e);
    }
  };

  const handleNew = () => {
    setJobId(null);
    setSelectedFile(null);
    reset();
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center space-x-3">
        <div className="p-3 bg-sky-500/10 rounded-xl text-sky-400">
          <Zap size={24} />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-white">Extract Archives</h1>
          <p className="text-slate-400">Extract ZIP, 7z, and RAR archives with nested archive support</p>
        </div>
      </div>

      {!jobId ? (
        <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
          <div className="bg-slate-800 rounded-2xl p-6 border border-slate-700 shadow-xl">
            <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-4">Select Archive</h2>
            <FileSelector 
              onSelect={(paths) => setSelectedFile(paths[0] || null)} 
              filter={(f) => f.is_dir || [ '.zip', '.7z', '.rar' ].some(ext => f.name.toLowerCase().endsWith(ext))}
            />
            
            <div className="mt-6 flex justify-end">
              <button
                disabled={!selectedFile}
                onClick={handleStart}
                className={`flex items-center space-x-2 px-6 py-3 rounded-xl font-bold transition-all ${
                  selectedFile 
                    ? 'bg-sky-500 hover:bg-sky-400 text-white shadow-lg shadow-sky-500/20' 
                    : 'bg-slate-700 text-slate-500 cursor-not-allowed'
                }`}
              >
                <Play size={20} fill="currentColor" />
                <span>Start Extraction</span>
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
                <span className="font-bold">Extraction Finished</span>
              </div>
              <button
                onClick={handleNew}
                className="px-6 py-2 bg-slate-700 hover:bg-slate-600 text-white font-bold rounded-xl transition-colors"
              >
                Start Another
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default Extract;
