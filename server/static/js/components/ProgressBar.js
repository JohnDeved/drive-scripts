import { html, useState, useEffect } from '../lib.js';

const formatBytes = (bytes, decimals = 2) => {
  if (!bytes || bytes === 0) return '0 Bytes';
  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
};

const formatTime = (seconds) => {
  if (!seconds || seconds <= 0) return '0s';
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  if (h > 0) return `${h}h ${m}m ${s}s`;
  if (m > 0) return `${m}m ${s}s`;
  return `${s}s`;
};

export default function ProgressBar({ percent, step, message, total, current, startTime }) {
  const [elapsed, setElapsed] = useState(0);
  
  useEffect(() => {
    if (!startTime) return;
    const interval = setInterval(() => {
      setElapsed(Math.floor((Date.now() - startTime) / 1000));
    }, 1000);
    return () => clearInterval(interval);
  }, [startTime]);

  const speed = elapsed > 0 ? current / elapsed : 0;
  const eta = speed > 0 ? (total - current) / speed : 0;

  return html`
    <div class="bg-slate-800 rounded-xl p-5 border border-slate-700 shadow-lg animate-slide-up">
      <div class="flex justify-between items-center mb-3">
        <div class="flex flex-col">
          <span class="text-sm font-medium text-sky-400">${step || 'Processing...'}</span>
          <span class="text-[10px] text-slate-500 font-mono mt-1">
            Runtime: ${formatTime(elapsed)} ${speed > 0 ? html`• Speed: ${formatBytes(speed)}/s` : ''}
          </span>
        </div>
        <div class="flex flex-col items-end">
          <span class="text-sm font-bold text-slate-300">${percent}%</span>
          ${eta > 0 ? html`<span class="text-[10px] text-slate-500 font-mono mt-1">ETA: ${formatTime(eta)}</span>` : ''}
        </div>
      </div>
      
      <div class="h-4 w-full bg-slate-700 rounded-full overflow-hidden mb-3 relative">
        <div 
          class="h-full bg-sky-500 rounded-full transition-all duration-300 shadow-[0_0_10px_rgba(14,165,233,0.5)]"
          style="width: ${percent}%"
        ></div>
      </div>
      
      <div class="flex justify-between items-center">
        <div class="text-xs text-slate-400 truncate flex-1 mr-4">
          ${message}
        </div>
        ${total && total > 0 ? html`
          <div class="text-xs font-mono text-slate-500 whitespace-nowrap">
            ${formatBytes(current)} / ${formatBytes(total)}
          </div>
        ` : ''}
      </div>
    </div>
  `;
}
