import { html, useState, useEffect, useMemo } from '../lib.js';
import FileSelector from '../components/FileSelector.js';
import ProgressBar from '../components/ProgressBar.js';
import LogOutput from '../components/LogOutput.js';
import { extractApi } from '../api.js';
import { useSSE } from '../hooks.js';

export default function Extract() {
  const [selectedFile, setSelectedFile] = useState(null);
  const [jobId, setJobId] = useState(null);
  const { progress, logs, isComplete, error, startTime, reset } = useSSE(jobId, 'extract');

  const filter = useMemo(() => (f) => 
    f.is_dir || [ '.zip', '.7z', '.rar' ].some(ext => f.name.toLowerCase().endsWith(ext)), 
  []);

  useEffect(() => {
    if (typeof lucide !== 'undefined') {
        lucide.createIcons();
    }
  }, [jobId, isComplete, error]);

  const handleStart = async () => {
    if (!selectedFile) return;
    try {
      reset();
      const res = await extractApi.start(selectedFile);
      setJobId(res.job_id);
    } catch (e) {
      console.error(e);
    }
  };

  const handleNew = () => {
    setJobId(null);
    setSelectedFile(null);
    reset();
  };

  return html`
    <div class="space-y-6">
      <div class="flex items-center space-x-3">
        <div class="p-3 bg-sky-500/10 rounded-xl text-sky-400">
          <div key="extract-header-icon"><i data-lucide="zap" class="w-6 h-6"></i></div>
        </div>
        <div>
          <h1 class="text-2xl font-bold text-white">Extract Archives</h1>
          <p class="text-slate-400">Extract ZIP, 7z, and RAR archives with nested archive support</p>
        </div>
      </div>

      ${!jobId ? html`
        <div class="space-y-6 animate-fade-in">
          <div class="bg-slate-800 rounded-2xl p-6 border border-slate-700 shadow-xl">
            <h2 class="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-4">Select Archive</h2>
            <${FileSelector} 
              onSelect=${(paths) => setSelectedFile(paths[0] || null)} 
              filter=${filter}
            />
            
            <div class="mt-6 flex justify-end">
              <button
                disabled=${!selectedFile}
                onClick=${handleStart}
                class="flex items-center space-x-2 px-6 py-3 rounded-xl font-bold transition-all ${
                  selectedFile 
                    ? 'bg-sky-500 hover:bg-sky-400 text-white shadow-lg shadow-sky-500/20' 
                    : 'bg-slate-700 text-slate-500 cursor-not-allowed'
                }"
              >
                <div key="play-icon-extract"><i data-lucide="play" class="w-5 h-5 fill-current"></i></div>
                <span>Start Extraction</span>
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

          <${LogOutput} logs=${logs} />

          ${error ? html`
            <div key="error-banner" class="p-4 bg-rose-500/10 border border-rose-500/20 rounded-xl flex items-center space-x-3 text-rose-400">
              <div key="error-icon"><i data-lucide="alert-circle" class="w-5 h-5"></i></div>
              <span>${error}</span>
            </div>
          ` : ''}

          ${isComplete ? html`
            <div key="complete-banner" class="flex justify-between items-center p-6 bg-slate-800 rounded-2xl border border-slate-700 shadow-xl">
              <div class="flex items-center space-x-3 text-emerald-400">
                <div key="complete-icon">
                  <i data-lucide="check-circle-2" class="w-6 h-6"></i>
                </div>
                <span class="font-bold">Extraction Finished</span>
              </div>
              <button
                onClick=${handleNew}
                class="px-6 py-2 bg-slate-700 hover:bg-slate-600 text-white font-bold rounded-xl transition-colors"
              >
                Start Another
              </button>
            </div>
          ` : ''}
        </div>
      `}
    </div>
  `;
}
