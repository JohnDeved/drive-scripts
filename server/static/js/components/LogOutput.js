import { html, useEffect, useRef } from '../lib.js';

export default function LogOutput({ logs }) {
  const scrollRef = useRef(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logs]);

  return html`
    <div class="bg-slate-950 rounded-xl border border-slate-800 flex flex-col h-64 shadow-inner">
      <div class="px-4 py-2 border-b border-slate-800 bg-slate-900/50 rounded-t-xl text-xs font-semibold text-slate-500 uppercase tracking-wider">
        Operation Log
      </div>
      <div 
        ref=${scrollRef}
        class="flex-1 overflow-y-auto p-4 font-mono text-sm space-y-1"
      >
        ${logs.length === 0 ? html`
          <div class="text-slate-700 italic">No log output yet.</div>
        ` : logs.map((log, i) => {
            const msg = typeof log === 'string' ? log : log.message;
            const time = typeof log === 'string' ? new Date().toLocaleTimeString() : log.time;
            
            const isError = msg.includes('FAIL') || msg.includes('Error') || msg.includes('failed');
            const isSuccess = msg.includes('OK') || msg.includes('success') || msg.includes('Done');
            
            return html`
              <div 
                key=${i} 
                class="${isError ? 'text-rose-400' : isSuccess ? 'text-emerald-400' : 'text-slate-300'}"
              >
                <span class="text-slate-600 mr-2">[${time}]</span>
                ${msg}
              </div>
            `;
          })
        }
      </div>
    </div>
  `;
}
