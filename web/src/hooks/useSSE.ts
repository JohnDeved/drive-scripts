import { useState, useEffect, useCallback, useRef } from 'react';

export interface ProgressData {
  step?: string;
  current?: number;
  total?: number;
  percent?: number;
  message?: string;
  stats?: Record<string, any>;
  [key: string]: any;
}

export interface SSEEvent {
  type: 'progress' | 'log' | 'complete' | 'error' | 'confirm_request' | 'cancelled';
  data: any;
}

export function useSSE(jobId: Optional<string>, tool: string) {
  const [progress, setProgress] = useState<ProgressData | null>(null);
  const [logs, setLogs] = useState<string[]>([]);
  const [isComplete, setIsComplete] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [confirmRequest, setConfirmRequest] = useState<any>(null);
  const eventSourceRef = useRef<EventSource | null>(null);

  const reset = useCallback(() => {
    setProgress(null);
    setLogs([]);
    setIsComplete(false);
    setError(null);
    setConfirmRequest(null);
  }, []);

  useEffect(() => {
    if (!jobId) {
      reset();
      return;
    }

    const url = `/api/${tool}/${jobId}/stream`;
    const eventSource = new EventSource(url);
    eventSourceRef.current = eventSource;

    eventSource.addEventListener('progress', (e) => {
      const data = JSON.parse((e as MessageEvent).data);
      setProgress(prev => ({ ...prev, ...data }));
    });

    eventSource.addEventListener('log', (e) => {
      const data = JSON.parse((e as MessageEvent).data);
      setLogs(prev => [...prev, data.message]);
    });

    eventSource.addEventListener('complete', (e) => {
      const data = JSON.parse((e as MessageEvent).data);
      setLogs(prev => [...prev, data.message || 'Operation complete.']);
      setIsComplete(true);
      eventSource.close();
    });

    eventSource.addEventListener('error', (e) => {
      const data = JSON.parse((e as MessageEvent).data);
      setError(data.message);
      eventSource.close();
    });

    eventSource.addEventListener('confirm_request', (e) => {
      const data = JSON.parse((e as MessageEvent).data);
      setConfirmRequest(data);
    });

    eventSource.onerror = () => {
      // Don't set error if we manually closed it
      if (eventSource.readyState !== EventSource.CLOSED) {
        setError('Connection to server lost.');
        eventSource.close();
      }
    };

    return () => {
      eventSource.close();
    };
  }, [jobId, tool, reset]);

  return { progress, logs, isComplete, error, confirmRequest, reset };
}

type Optional<T> = T | null | undefined;
