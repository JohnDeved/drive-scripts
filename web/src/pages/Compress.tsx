import React, { useState } from 'react';
import FileSelector from '../components/FileSelector';
import ProgressBar from '../components/ProgressBar';
import LogOutput from '../components/LogOutput';
import { compressApi } from '../api/client';
import { useSSE } from '../hooks/useSSE';
import { Minimize2, Play, CheckCircle2, AlertCircle, HelpCircle } from 'lucide-react';

const Compress: React.FC = () => {
  const [selectedFiles, setSelectedFiles] = useState<string[]>([]);
  const [verifyAfter, setVerifyAfter] = useState(true);
  const [askConfirm, setAskConfirm] = useState(true);
  const [jobId, setJobId] = useState<string | null>(null);
  const { progress, logs, isComplete, error, confirmRequest, reset } = useSSE(jobId, 'compress');

  const handleStart = async () => {
    if (selectedFiles.length === 0) return;
    try {
      reset();
      const res = await compressApi.start(selectedFiles, verifyAfter, askConfirm);
      setJobId(res.job_id);
    } catch (e: any) {
      console.error(e);
    }
  };

  const handleConfirm = async (keep: boolean) => {
    if (!jobId) return;
    try {
      await compressApi.confirm(jobId, keep);
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
        <div className="p-3 bg-amber-500/10 rounded-xl text-amber-400">
          <Minimize2 size={24} />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-white">Compress NSZ</h1>
          <p className="text-slate-400">Compress NSP/XCI to NSZ/XCZ format</p>
        </div>
      </div>

      {!jobId ? (
        <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
          <div className="bg-slate-800 rounded-2xl p-6 border border-slate-700 shadow-xl">
            <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-4">Select Files to Compress</h2>
            <FileSelector 
              multi
              onSelect={setSelectedFiles} 
              filter={(f) => f.is_dir || [ '.nsp', '.xci' ].some(ext => f.name.toLowerCase().endsWith(ext))}
            />
            
            <div className="mt-6 flex flex-wrap gap-4 items-center">
              <label className="flex items-center space-x-2 cursor-pointer group">
                <input 
                  type="checkbox" 
                  checked={verifyAfter} 
                  onChange={(e) => setVerifyAfter(e.target.checked)}
                  className="w-4 h-4 rounded border-slate-600 bg-slate-700 text-amber-500 focus:ring-amber-500"
                />
                <span className="text-sm text-slate-300 group-hover:text-white transition-colors">Verify after compression</span>
              </label>

              <label className="flex items-center space-x-2 cursor-pointer group">
                <input 
                  type="checkbox" 
                  checked={askConfirm} 
                  onChange={(e) => setAskConfirm(e.target.checked)}
                  className="w-4 h-4 rounded border-slate-600 bg-slate-700 text-amber-500 focus:ring-amber-500"
                />
                <span className="text-sm text-slate-300 group-hover:text-white transition-colors">Ask before saving</span>
              </label>
            </div>

            <div className="mt-8 flex justify-between items-center">
              <div className="text-sm text-slate-400">
                {selectedFiles.length} files selected
              </div>
              <button
                disabled={selectedFiles.length === 0}
                onClick={handleStart}
                className={`flex items-center space-x-2 px-6 py-3 rounded-xl font-bold transition-all ${
                  selectedFiles.length > 0 
                    ? 'bg-amber-500 hover:bg-amber-400 text-white shadow-lg shadow-amber-500/20' 
                    : 'bg-slate-700 text-slate-500 cursor-not-allowed'
                }`}
              >
                <Play size={20} fill="currentColor" />
                <span>Start Compression</span>
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
            <div className="bg-amber-500/10 border border-amber-500/20 rounded-2xl p-6 shadow-xl animate-in zoom-in-95 duration-300">
              <div className="flex items-center space-x-3 text-amber-400 mb-4">
                <HelpCircle size={24} />
                <h3 className="text-xl font-bold">Confirm Compression</h3>
              </div>
              
              <div className="grid grid-cols-2 gap-4 mb-6">
                <div className="bg-slate-900/50 p-4 rounded-xl">
                  <div className="text-xs text-slate-500 uppercase font-bold mb-1">Original</div>
                  <div className="text-lg font-mono text-slate-300">{confirmRequest.original_size_str}</div>
                </div>
                <div className="bg-slate-900/50 p-4 rounded-xl">
                  <div className="text-xs text-slate-500 uppercase font-bold mb-1">Compressed</div>
                  <div className="text-lg font-mono text-emerald-400">{confirmRequest.compressed_size_str}</div>
                </div>
              </div>

              <p className="text-slate-300 mb-6">
                Compression saved <span className="text-emerald-400 font-bold">{confirmRequest.savings}</span> ({confirmRequest.percent}% of original). 
                Keep the compressed version and delete the original?
              </p>

              <div className="flex space-x-4">
                <button
                  onClick={() => handleConfirm(true)}
                  className="flex-1 py-3 bg-emerald-600 hover:bg-emerald-500 text-white font-bold rounded-xl transition-colors shadow-lg shadow-emerald-600/20"
                >
                  Yes, Keep it
                </button>
                <button
                  onClick={() => handleConfirm(false)}
                  className="flex-1 py-3 bg-slate-700 hover:bg-slate-600 text-white font-bold rounded-xl transition-colors"
                >
                  No, Discard
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
                <span className="font-bold">Compression Finished</span>
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

export default Compress;
