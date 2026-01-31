import React from 'react';
import { motion } from 'framer-motion';

interface ProgressBarProps {
  percent: number;
  step?: string;
  message?: string;
  total?: number;
  current?: number;
}

const ProgressBar: React.FC<ProgressBarProps> = ({ percent, step, message, total, current }) => {
  return (
    <div className="bg-slate-800 rounded-xl p-5 border border-slate-700 shadow-lg">
      <div className="flex justify-between items-center mb-3">
        <span className="text-sm font-medium text-sky-400">{step || 'Processing...'}</span>
        <span className="text-sm font-bold text-slate-300">{percent}%</span>
      </div>
      
      <div className="h-4 w-full bg-slate-700 rounded-full overflow-hidden mb-3">
        <motion.div 
          className="h-full bg-sky-500 rounded-full"
          initial={{ width: 0 }}
          animate={{ width: `${percent}%` }}
          transition={{ duration: 0.3 }}
        />
      </div>
      
      <div className="flex justify-between items-center">
        <div className="text-xs text-slate-400 truncate flex-1 mr-4">
          {message}
        </div>
        {total && total > 0 && (
          <div className="text-xs font-mono text-slate-500 whitespace-nowrap">
            {current?.toLocaleString()} / {total?.toLocaleString()}
          </div>
        )}
      </div>
    </div>
  );
};

export default ProgressBar;
