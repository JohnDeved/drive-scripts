import React, { useState } from 'react';
import FileSelector from '../components/FileSelector';
import ProgressBar from '../components/ProgressBar';
import LogOutput from '../components/LogOutput';
import { verifyApi } from '../api/client';
import { useSSE } from '../hooks/useSSE';
import { CheckCircle, Play, CheckCircle2, AlertCircle } from 'lucide-react';

const Verify: React.FC = () => {
  const [selectedFiles, setSelectedFiles] = useState<string[]>([]);
  const [jobId, setJobId] = useState<string | null>(null);
  const { progress, logs, isComplete, error, reset } = useSSE(jobId, 'verify');

  const handleStart = async () => {
    if (selectedFiles.length === 0) return;
    try {
      reset();
      const res = await verifyApi.start(selectedFiles);
      setJobId(res.job_id);
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
        <div className="p-3 bg-indigo-500/10 rounded-xl text-indigo-400">
          <CheckCircle size={24} />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-white">Verify NSZ</h1>
          <p className="text-slate-400">Verify game files using NSZ quick verify</p>
        </div>
      </div>

      {!jobId ? (
        <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
          <div className="bg-slate-800 rounded-2xl p-6 border border-slate-700 shadow-xl">
            <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-4">Select Files to Verify</h2>
            <FileSelector 
              multi
              onSelect={setSelectedFiles} 
              filter={(f) => f.is_dir || [ '.nsp', '.nsz', '.xci', '.xcz' ].some(ext => f.name.toLowerCase().endsWith(ext))}
            />
            
            <div className="mt-6 flex justify-between items-center">
              <div className="text-sm text-slate-400">
                {selectedFiles.length} files selected
              </div>
              <button
                disabled={selectedFiles.length === 0}
                onClick={handleStart}
                className={`flex items-center space-x-2 px-6 py-3 rounded-xl font-bold transition-all ${
                  selectedFiles.length > 0 
                    ? 'bg-indigo-500 hover:bg-indigo-400 text-white shadow-lg shadow-indigo-500/20' 
                    : 'bg-slate-700 text-slate-500 cursor-not-allowed'
                }`}
              >
                <Play size={20} fill="currentColor" />
                <span>Start Verification</span>
              </button>
            </div>
          </div>
        </div>
      ) : (
        <div className="space-y-6 animate-in fade-in duration-500">
          {progress && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="md:col-span-2">
                <ProgressBar 
                  percent={progress.percent || 0}
                  step={progress.step}
                  message={progress.message}
                  total={progress.total}
                  current={progress.current}
                />
              </div>
              <div className="bg-slate-800 rounded-xl p-5 border border-slate-700 flex justify-around items-center">
                <div className="text-center">
                  <div className="text-2xl font-black text-emerald-400">{progress.stats?.passed || 0}</div>
                  <div className="text-[10px] uppercase font-bold text-slate-500">Passed</div>
                </div>
                <div className="w-px h-8 bg-slate-700" />
                <div className="text-center">
                  <div className="text-2xl font-black text-rose-400">{progress.stats?.failed || 0}</div>
                  <div className="text-[10px] uppercase font-bold text-slate-500">Failed</div>
                </div>
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
                <span className="font-bold">Verification Finished</span>
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

export default Verify;
