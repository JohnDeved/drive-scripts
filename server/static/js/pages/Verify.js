import { html, useState, useEffect, useMemo } from '../lib.js';
import FileSelector from '../components/FileSelector.js';
import ProgressBar from '../components/ProgressBar.js';
import LogOutput from '../components/LogOutput.js';
import { verifyApi } from '../api.js';
import { useSSE } from '../hooks.js';

export default function Verify() {
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [jobId, setJobId] = useState(null);
  const { progress, logs, isComplete, error, startTime, reset } = useSSE(jobId, 'verify');

  const filter = useMemo(() => (f) => 
    f.is_dir || [ '.nsp', '.nsz', '.xci', '.xcz' ].some(ext => f.name.toLowerCase().endsWith(ext)), 
  []);

  useEffect(() => {
    if (typeof lucide !== 'undefined') {
        lucide.createIcons();
    }
  }, [jobId, isComplete, error]);

  const handleStart = async () => {
    if (selectedFiles.length === 0) return;
    try {
      reset();
      const res = await verifyApi.start(selectedFiles);
      setJobId(res.job_id);
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
        <div class="p-3 bg-indigo-500/10 rounded-xl text-indigo-400">
          <div key="verify-header-icon"><i data-lucide="check-circle" class="w-6 h-6"></i></div>
        </div>
        <div>
          <h1 class="text-2xl font-bold text-white">Verify NSZ</h1>
          <p class="text-slate-400">Verify game files using NSZ quick verify</p>
        </div>
      </div>

      ${!jobId ? html`
        <div class="space-y-6 animate-fade-in">
          <div class="bg-slate-800 rounded-2xl p-6 border border-slate-700 shadow-xl">
            <h2 class="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-4">Select Files to Verify</h2>
            <${FileSelector} 
              multi
              onSelect=${setSelectedFiles} 
              filter=${filter}
            />
            
            <div class="mt-6 flex justify-between items-center">
              <div class="text-sm text-slate-400">
                ${selectedFiles.length} files selected
              </div>
              <button
                disabled=${selectedFiles.length === 0}
                onClick=${handleStart}
                class="flex items-center space-x-2 px-6 py-3 rounded-xl font-bold transition-all ${
                  selectedFiles.length > 0 
                    ? 'bg-indigo-500 hover:bg-indigo-400 text-white shadow-lg shadow-indigo-500/20' 
                    : 'bg-slate-700 text-slate-500 cursor-not-allowed'
                }"
              >
                <div key="play-icon-verify"><i data-lucide="play" class="w-5 h-5 fill-current"></i></div>
                <span>Start Verification</span>
              </button>
            </div>
          </div>
        </div>
      ` : html`
        <div class="space-y-6 animate-fade-in">
          ${progress ? html`
            <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div class="md:col-span-2">
                <${ProgressBar} 
                  percent=${progress.percent || 0}
                  step=${progress.step}
                  message=${progress.message}
                  total=${progress.total}
                  current=${progress.current}
                  startTime=${startTime}
                />
              </div>
              <div class="bg-slate-800 rounded-xl p-5 border border-slate-700 flex justify-around items-center">
                <div class="text-center">
                  <div class="text-2xl font-black text-emerald-400">${progress.stats?.passed || 0}</div>
                  <div class="text-[10px] uppercase font-bold text-slate-500">Passed</div>
                </div>
                <div class="w-px h-8 bg-slate-700" />
                <div class="text-center">
                  <div class="text-2xl font-black text-rose-400">${progress.stats?.failed || 0}</div>
                  <div class="text-[10px] uppercase font-bold text-slate-500">Failed</div>
                </div>
              </div>
            </div>
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
                <span class="font-bold">Verification Finished</span>
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
