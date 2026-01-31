import { html, useState, useEffect, useMemo, useRef } from '../lib.js';

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

const formatValue = (val, isBytes) => {
  if (isBytes) return formatBytes(val);
  return val?.toLocaleString() || '0';
};

export default function ProgressBar({ percent, step, message, total, current, startTime }) {
  const [elapsed, setElapsed] = useState(0);
  const [stepStartTime, setStepStartTime] = useState(Date.now());
  const [lastStep, setLastStep] = useState(step);
  const samples = useRef([]); // Stores { time: ms, current: val }
  
  // Detect if we are handling bytes (usually large numbers or specific steps)
  const isBytes = useMemo(() => {
    const s = step?.toLowerCase() || '';
    return s.includes('copy') || s.includes('extract') || s.includes('compress') || s.includes('upload') || total > 1000000;
  }, [step, total]);

  // Reset step timer and samples when step changes
  if (step !== lastStep) {
    setLastStep(step);
    setStepStartTime(Date.now());
    samples.current = [];
  }

  // Timer for elapsed time
  useEffect(() => {
    if (!startTime) return;
    const interval = setInterval(() => {
      setElapsed(Math.floor((Date.now() - startTime) / 1000));
    }, 1000);
    return () => clearInterval(interval);
  }, [startTime]);

  // HIGH-SPEED SAMPLING: Record current value immediately when it changes
  useEffect(() => {
    if (current === undefined || current === null) return;
    
    const now = Date.now();
    samples.current.push({ time: now, current });
    
    // Keep last 5 seconds of history for a smooth but reactive average
    const cutoff = now - 5000;
    while (samples.current.length > 2 && samples.current[0].time < cutoff) {
      samples.current.shift();
    }
  }, [current]);

  // Calculate Speed: Reactive moving average
  let speed = 0;
  if (samples.current.length >= 2) {
    const first = samples.current[0];
    const last = samples.current[samples.current.length - 1];
    const timeDiff = (last.time - first.time) / 1000;
    const valDiff = last.current - first.current;
    if (timeDiff > 0.1) { // Min 100ms gap for stable calculation
      speed = valDiff / timeDiff;
    }
  }

  // Fallback to step average if window is too small or speed is zero
  if (speed <= 0) {
    const stepElapsed = (Date.now() - stepStartTime) / 1000;
    speed = stepElapsed > 0.5 ? current / stepElapsed : 0;
  }

  const eta = speed > 0 ? (total - current) / speed : 0;

  return html`
    <div class="bg-slate-800 rounded-xl p-5 border border-slate-700 shadow-lg animate-slide-up">
      <div class="flex justify-between items-center mb-3">
        <div class="flex flex-col">
          <span class="text-sm font-medium text-sky-400">${step || 'Processing...'}</span>
          <span class="text-[10px] text-slate-500 font-mono mt-1">
            Runtime: ${formatTime(elapsed)} ${speed > 0 ? html`• Speed: ${isBytes ? formatBytes(speed) + '/s' : speed.toFixed(1) + ' files/s'}` : ''}
          </span>
        </div>
        <div class="flex flex-col items-end">
          <span class="text-sm font-bold text-slate-300">${percent}%</span>
          ${eta > 0 ? html`<span class="text-[10px] text-slate-500 font-mono mt-1">ETA: ${formatTime(eta)}</span>` : ''}
        </div>
      </div>
      
      <div class="h-4 w-full bg-slate-700 rounded-full overflow-hidden mb-3 relative">
        <div 
          class="h-full bg-sky-500 rounded-full transition-all duration-150 ease-out shadow-[0_0_10px_rgba(14,165,233,0.5)]"
          style="width: ${percent}%"
        ></div>
      </div>
      
      <div class="flex justify-between items-center">
        <div class="text-xs text-slate-400 truncate flex-1 mr-4">
          ${message}
        </div>
        ${total && total > 0 ? html`
          <div class="text-xs font-mono text-slate-500 whitespace-nowrap">
            ${formatValue(current, isBytes)} / ${formatValue(total, isBytes)}
          </div>
        ` : ''}
      </div>
    </div>
  `;
}
