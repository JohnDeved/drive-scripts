import { useState, useEffect, useCallback, useRef } from './lib.js';

export function useSSE(jobId, tool) {
  const [progress, setProgress] = useState(null);
  const [logs, setLogs] = useState([]);
  const [isComplete, setIsComplete] = useState(false);
  const [error, setError] = useState(null);
  const [confirmRequest, setConfirmRequest] = useState(null);
  const eventSourceRef = useRef(null);

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
      const data = JSON.parse(e.data);
      setProgress(prev => ({ ...prev, ...data }));
    });

    eventSource.addEventListener('log', (e) => {
      const data = JSON.parse(e.data);
      setLogs(prev => [...prev, data.message]);
    });

    eventSource.addEventListener('complete', (e) => {
      const data = JSON.parse(e.data);
      setLogs(prev => [...prev, data.message || 'Operation complete.']);
      setIsComplete(true);
      eventSource.close();
    });

    eventSource.addEventListener('error', (e) => {
      const data = JSON.parse(e.data);
      setError(data.message);
      eventSource.close();
    });

    eventSource.addEventListener('confirm_request', (e) => {
      const data = JSON.parse(e.data);
      setConfirmRequest(data);
    });

    eventSource.onerror = () => {
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
