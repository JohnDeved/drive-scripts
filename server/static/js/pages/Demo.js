import { html, useState, useEffect } from '../lib.js';
import ProgressBar from '../components/ProgressBar.js';
import LogOutput from '../components/LogOutput.js';
import { useSSE } from '../hooks.js';

export default function Demo() {
  const [jobId, setJobId] = useState(null);
  const { progress, logs, isComplete, error, confirmRequest, startTime, confirm, reset } = useSSE(jobId, 'demo');

  useEffect(() => {
    if (typeof lucide !== 'undefined') {
        lucide.createIcons();
    }
  }, [jobId, isComplete, error, confirmRequest]);

  const handleStart = async () => {
    try {
      reset();
      const res = await fetch('api/demo/start', { method: 'POST' }).then(r => r.json());
      setJobId(res.job_id);
    } catch (e) {
      console.error(e);
    }
  };

  const handleNew = () => {
    setJobId(null);
    reset();
  };

  return html`
    <div class="space-y-6">
      <div class="flex items-center justify-between">
        <div class="flex items-center space-x-3">
          <div class="p-3 bg-fuchsia-500/10 rounded-xl text-fuchsia-400">
            <div key="demo-header-icon"><i data-lucide="cpu" class="w-6 h-6"></i></div>
          </div>
          <div>
            <h1 class="text-2xl font-bold text-white">Real-time Stream Demo</h1>
            <p class="text-slate-400">Testing WebSocket stability and high-frequency UI updates</p>
          </div>
        </div>
        
        ${!jobId || isComplete ? html`
          <button
            onClick=${handleStart}
            class="px-6 py-3 bg-fuchsia-600 hover:bg-fuchsia-500 text-white font-bold rounded-xl transition-all shadow-lg shadow-fuchsia-600/20 flex items-center space-x-2"
          >
            <div key="play-icon-demo"><i data-lucide="play" class="w-5 h-5 fill-current"></i></div>
            <span>${isComplete ? 'Run Again' : 'Launch Simulation'}</span>
          </button>
        ` : ''}
      </div>

      ${!jobId ? html`
        <div class="bg-slate-800/50 border border-slate-700 rounded-3xl p-12 text-center space-y-4 animate-fade-in">
          <div class="mx-auto w-20 h-20 bg-slate-800 rounded-full flex items-center justify-center text-slate-500 mb-6">
            <div key="monitor-icon"><i data-lucide="monitor" class="w-10 h-10"></i></div>
          </div>
          <h2 class="text-xl font-bold text-white">Ready to test?</h2>
          <p class="text-slate-400 max-w-md mx-auto">
            This demo will stress-test the WebSocket connection with 20+ updates per second, 
            interactive confirmation dialogs, and dynamic speed calculations.
          </p>
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
          ` : html`
            <div key="demo-loader" class="bg-slate-800 rounded-xl p-5 border border-slate-700 flex items-center justify-center space-x-3">
              <div key="loader-icon-demo"><i data-lucide="loader-2" class="w-5 h-5 animate-spin text-fuchsia-500"></i></div>
              <span class="text-slate-400">Waiting for stream...</span>
            </div>
          `}

          ${confirmRequest ? html`
            <div key="confirm-panel" class="bg-fuchsia-500/10 border border-fuchsia-500/20 rounded-2xl p-6 shadow-xl animate-slide-up">
              <div class="flex items-center space-x-3 text-fuchsia-400 mb-4">
                <div key="confirm-icon-demo"><i data-lucide="help-circle" class="w-6 h-6"></i></div>
                <h3 class="text-xl font-bold">Interactive Intercept</h3>
              </div>
              
              <p class="text-slate-300 mb-6">
                The server has paused and is waiting for your confirmation over the WebSocket. 
                This tests the bidirectional "Stream-Back" capability.
              </p>

              <div class="flex space-x-4">
                <button
                  onClick=${() => confirm(true)}
                  class="flex-1 py-3 bg-fuchsia-600 hover:bg-fuchsia-500 text-white font-bold rounded-xl transition-colors shadow-lg shadow-fuchsia-600/20"
                >
                  Confirm & Continue
                </button>
                <button
                  onClick=${() => confirm(false)}
                  class="flex-1 py-3 bg-slate-700 hover:bg-slate-600 text-white font-bold rounded-xl transition-colors"
                >
                  Abort
                </button>
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
                <span class="font-bold">Simulation Complete</span>
              </div>
              <button
                onClick=${handleNew}
                class="px-6 py-2 bg-slate-700 hover:bg-slate-600 text-white font-bold rounded-xl transition-colors"
              >
                Clear
              </button>
            </div>
          ` : ''}
        </div>
      `}
    </div>
  `;
}
