import { html } from '../lib.js';

export default function ProgressBar({ percent, step, message, total, current }) {
  return html`
    <div class="bg-slate-800 rounded-xl p-5 border border-slate-700 shadow-lg animate-slide-up">
      <div class="flex justify-between items-center mb-3">
        <span class="text-sm font-medium text-sky-400">${step || 'Processing...'}</span>
        <span class="text-sm font-bold text-slate-300">${percent}%</span>
      </div>
      
      <div class="h-4 w-full bg-slate-700 rounded-full overflow-hidden mb-3">
        <div 
          class="h-full bg-sky-500 rounded-full transition-all duration-300"
          style="width: ${percent}%"
        ></div>
      </div>
      
      <div class="flex justify-between items-center">
        <div class="text-xs text-slate-400 truncate flex-1 mr-4">
          ${message}
        </div>
        ${total && total > 0 ? html`
          <div class="text-xs font-mono text-slate-500 whitespace-nowrap">
            ${current?.toLocaleString()} / ${total?.toLocaleString()}
          </div>
        ` : ''}
      </div>
    </div>
  `;
}
