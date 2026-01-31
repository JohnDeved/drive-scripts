import React, { useEffect, useRef } from 'react';

interface LogOutputProps {
  logs: string[];
}

const LogOutput: React.FC<LogOutputProps> = ({ logs }) => {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logs]);

  return (
    <div className="bg-slate-950 rounded-xl border border-slate-800 flex flex-col h-64 shadow-inner">
      <div className="px-4 py-2 border-b border-slate-800 bg-slate-900/50 rounded-t-xl text-xs font-semibold text-slate-500 uppercase tracking-wider">
        Operation Log
      </div>
      <div 
        ref={scrollRef}
        className="flex-1 overflow-y-auto p-4 font-mono text-sm space-y-1"
      >
        {logs.length === 0 ? (
          <div className="text-slate-700 italic">No log output yet.</div>
        ) : (
          logs.map((log, i) => {
            const isError = log.includes('FAIL') || log.includes('Error') || log.includes('failed');
            const isSuccess = log.includes('OK') || log.includes('success') || log.includes('Done');
            
            return (
              <div 
                key={i} 
                className={`${isError ? 'text-rose-400' : isSuccess ? 'text-emerald-400' : 'text-slate-300'}`}
              >
                <span className="text-slate-600 mr-2">[{new Date().toLocaleTimeString()}]</span>
                {log}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};

export default LogOutput;
