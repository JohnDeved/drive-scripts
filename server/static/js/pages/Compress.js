import { html, useState, useEffect, useMemo } from '../lib.js';
import FileSelector from '../components/FileSelector.js';
import ProgressBar from '../components/ProgressBar.js';
import LogOutput from '../components/LogOutput.js';
import { compressApi } from '../api.js';
import { useSSE } from '../hooks.js';

export default function Compress() {
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [verifyAfter, setVerifyAfter] = useState(true);
  const [askConfirm, setAskConfirm] = useState(true);
  const [jobId, setJobId] = useState(null);
  const { progress, logs, isComplete, error, confirmRequest, startTime, reset } = useSSE(jobId, 'compress');

  const filter = useMemo(() => (f) => 
    f.is_dir || [ '.nsp', '.xci' ].some(ext => f.name.toLowerCase().endsWith(ext)), 
  []);

  useEffect(() => {
    if (typeof lucide !== 'undefined') {
        lucide.createIcons();
    }
  }, [jobId, isComplete, error, confirmRequest]);

  const handleStart = async () => {
    if (selectedFiles.length === 0) return;
    try {
      reset();
      const res = await compressApi.start(selectedFiles, verifyAfter, askConfirm);
      setJobId(res.job_id);
    } catch (e) {
      console.error(e);
    }
  };

  const handleConfirm = async (keep) => {
    if (!jobId) return;
    try {
      await compressApi.confirm(jobId, keep);
    } catch (e) {
      console.error(e);
    }
  };

  const handleNew = () => {
    setJobId(null);
    setSelectedFiles([]);
    reset();
  };

  return html`
    <div class="space-y-6">
      <div class="flex items-center space-x-3">
        <div class="p-3 bg-amber-500/10 rounded-xl text-amber-400">
          <i data-lucide="minimize-2" class="w-6 h-6"></i>
        </div>
        <div>
          <h1 class="text-2xl font-bold text-white">Compress NSZ</h1>
          <p class="text-slate-400">Compress NSP/XCI to NSZ/XCZ format</p>
        </div>
      </div>

      ${!jobId ? html`
        <div class="space-y-6 animate-fade-in">
          <div class="bg-slate-800 rounded-2xl p-6 border border-slate-700 shadow-xl">
            <h2 class="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-4">Select Files to Compress</h2>
            <${FileSelector} 
              multi
              onSelect=${setSelectedFiles} 
              filter=${filter}
            />
            
            <div class="mt-6 flex flex-wrap gap-4 items-center">
              <label class="flex items-center space-x-2 cursor-pointer group">
                <input 
                  type="checkbox" 
                  checked=${verifyAfter} 
                  onChange=${(e) => setVerifyAfter(e.target.checked)}
                  class="w-4 h-4 rounded border-slate-600 bg-slate-700 text-amber-500 focus:ring-amber-500"
                />
                <span class="text-sm text-slate-300 group-hover:text-white transition-colors">Verify after compression</span>
              </label>
              <label class="flex items-center space-x-2 cursor-pointer group">
                <input 
                  type="checkbox" 
                  checked=${askConfirm} 
                  onChange=${(e) => setAskConfirm(e.target.checked)}
                  class="w-4 h-4 rounded border-slate-600 bg-slate-700 text-amber-500 focus:ring-amber-500"
                />
                <span class="text-sm text-slate-300 group-hover:text-white transition-colors">Ask before saving</span>
              </label>
            </div>

            <div class="mt-8 flex justify-between items-center">
              <div class="text-sm text-slate-400">
                ${selectedFiles.length} files selected
              </div>
              <button
                disabled=${selectedFiles.length === 0}
                onClick=${handleStart}
                class="flex items-center space-x-2 px-6 py-3 rounded-xl font-bold transition-all ${
                  selectedFiles.length > 0 
                    ? 'bg-amber-500 hover:bg-amber-400 text-white shadow-lg shadow-amber-500/20' 
                    : 'bg-slate-700 text-slate-500 cursor-not-allowed'
                }"
              >
                <i data-lucide="play" class="w-5 h-5 fill-current"></i>
                <span>Start Compression</span>
              </button>
            </div>
          </div>
        </div>
      ` : html`
        <div class="space-y-6 animate-fade-in">
          ${progress ? html`
            <${ProgressBar} 
              percent=${progress.percent || 0}
              step=${progress.step}
              message=${progress.message}
              total=${progress.total}
              current=${progress.current}
              startTime=${startTime}
            />
          ` : ''}

          ${confirmRequest ? html`
            <div class="bg-amber-500/10 border border-amber-500/20 rounded-2xl p-6 shadow-xl animate-slide-up">
              <div class="flex items-center space-x-3 text-amber-400 mb-4">
                <i data-lucide="help-circle" class="w-6 h-6"></i>
                <h3 class="text-xl font-bold">Confirm Compression</h3>
              </div>
              
              <div class="grid grid-cols-2 gap-4 mb-6">
                <div class="bg-slate-900/50 p-4 rounded-xl">
                  <div class="text-xs text-slate-500 uppercase font-bold mb-1">Original</div>
                  <div class="text-lg font-mono text-slate-300">${confirmRequest.original_size_str}</div>
                </div>
                <div class="bg-slate-900/50 p-4 rounded-xl">
                  <div class="text-xs text-slate-500 uppercase font-bold mb-1">Compressed</div>
                  <div class="text-lg font-mono text-emerald-400">${confirmRequest.compressed_size_str}</div>
                </div>
              </div>

              <p class="text-slate-300 mb-6">
                Compression saved <span class="text-emerald-400 font-bold">${confirmRequest.savings}</span> (${confirmRequest.percent}% of original). 
                Keep the compressed version and delete the original?
              </p>

              <div class="flex space-x-4">
                <button
                  onClick=${() => handleConfirm(true)}
                  class="flex-1 py-3 bg-emerald-600 hover:bg-emerald-500 text-white font-bold rounded-xl transition-colors shadow-lg shadow-emerald-600/20"
                >
                  Yes, Keep it
                </button>
                <button
                  onClick=${() => handleConfirm(false)}
                  class="flex-1 py-3 bg-slate-700 hover:bg-slate-600 text-white font-bold rounded-xl transition-colors"
                >
                  No, Discard
                </button>
              </div>
            </div>
          ` : ''}

          <${LogOutput} logs=${logs} />

          ${error ? html`
            <div class="p-4 bg-rose-500/10 border border-rose-500/20 rounded-xl flex items-center space-x-3 text-rose-400">
              <i data-lucide="alert-circle" class="w-5 h-5"></i>
              <span>${error}</span>
            </div>
          ` : ''}

          ${isComplete ? html`
            <div class="flex justify-between items-center p-6 bg-slate-800 rounded-2xl border border-slate-700 shadow-xl">
              <div class="flex items-center space-x-3 text-emerald-400">
                <i data-lucide="check-circle-2" class="w-6 h-6"></i>
                <span class="font-bold">Compression Finished</span>
              </div>
              <button
                onClick=${handleNew}
                class="px-6 py-2 bg-slate-700 hover:bg-slate-600 text-white font-bold rounded-xl transition-colors"
              >
                New Session
              </button>
            </div>
          ` : ''}
        </div>
      `}
    </div>
  `;
}
