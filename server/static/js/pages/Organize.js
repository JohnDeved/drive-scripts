import { html, useState, useEffect, useMemo } from '../lib.js';
import FileSelector from '../components/FileSelector.js';
import ProgressBar from '../components/ProgressBar.js';
import LogOutput from '../components/LogOutput.js';
import { organizeApi } from '../api.js';
import { useSSE } from '../hooks.js';

export default function Organize() {
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [jobId, setJobId] = useState(null);
  const { progress, logs, isComplete, error, confirmRequest, reset } = useSSE(jobId, 'organize');

  const filter = useMemo(() => (f) => 
    f.is_dir || [ '.nsp', '.nsz', '.xci', '.xcz' ].some(ext => f.name.toLowerCase().endsWith(ext)), 
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
      const res = await organizeApi.start(selectedFiles);
      setJobId(res.job_id);
    } catch (e) {
      console.error(e);
    }
  };

  const handleConfirm = async (apply) => {
    if (!jobId) return;
    try {
      await organizeApi.confirm(jobId, apply);
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
        <div class="p-3 bg-emerald-500/10 rounded-xl text-emerald-400">
          <i data-lucide="tags" class="w-6 h-6"></i>
        </div>
        <div>
          <h1 class="text-2xl font-bold text-white">Organize & Rename</h1>
          <p class="text-slate-400">Rename files based on TitleDB (Name [TitleID] [vVersion])</p>
        </div>
      </div>

      ${!jobId ? html`
        <div class="space-y-6 animate-fade-in">
          <div class="bg-slate-800 rounded-2xl p-6 border border-slate-700 shadow-xl">
            <h2 class="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-4">Select Files to Organize</h2>
            <${FileSelector} 
              multi
              onSelect=${setSelectedFiles} 
              filter=${filter}
            />
            
            <div class="mt-8 flex justify-between items-center">
              <div class="text-sm text-slate-400">
                ${selectedFiles.length} files selected
              </div>
              <button
                disabled=${selectedFiles.length === 0}
                onClick=${handleStart}
                class="flex items-center space-x-2 px-6 py-3 rounded-xl font-bold transition-all ${
                  selectedFiles.length > 0 
                    ? 'bg-emerald-500 hover:bg-emerald-400 text-white shadow-lg shadow-emerald-500/20' 
                    : 'bg-slate-700 text-slate-500 cursor-not-allowed'
                }"
              >
                <i data-lucide="play" class="w-5 h-5 fill-current"></i>
                <span>Analyze Files</span>
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
            />
          ` : ''}

          ${confirmRequest ? html`
            <div class="bg-slate-800 rounded-2xl border border-slate-700 shadow-xl overflow-hidden animate-slide-up">
              <div class="p-6 border-b border-slate-700 bg-slate-800/50">
                <h3 class="text-xl font-bold text-white flex items-center">
                  Proposed Changes
                  <span class="ml-3 text-xs bg-emerald-500/20 text-emerald-400 px-2 py-1 rounded-full uppercase tracking-widest font-black">
                    ${confirmRequest.plan.length} renames
                  </span>
                </h3>
              </div>
              
              <div class="max-h-96 overflow-y-auto divide-y divide-slate-700/50">
                ${confirmRequest.plan.map((item, i) => html`
                  <div key=${i} class="p-4 space-y-2">
                    <div class="text-xs text-rose-400 font-mono truncate opacity-60 line-through">${item.old_name}</div>
                    <div class="flex items-center space-x-2">
                      <i data-lucide="arrow-right" class="w-3.5 h-3.5 text-slate-500"></i>
                      <div class="text-sm text-emerald-400 font-bold truncate">${item.new_name}</div>
                    </div>
                  </div>
                `)}
              </div>

              <div class="p-6 bg-slate-900/30 flex space-x-4">
                <button
                  onClick=${() => handleConfirm(true)}
                  class="flex-1 py-3 bg-emerald-600 hover:bg-emerald-500 text-white font-bold rounded-xl transition-colors shadow-lg shadow-emerald-600/20"
                >
                  Apply Changes
                </button>
                <button
                  onClick=${() => handleConfirm(false)}
                  class="flex-1 py-3 bg-slate-700 hover:bg-slate-600 text-white font-bold rounded-xl transition-colors"
                >
                  Discard
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
                <span class="font-bold">Organization Finished</span>
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
