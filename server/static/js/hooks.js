import { useState, useEffect, useCallback, useRef } from './lib.js';

export function useSSE(jobId, tool) {
  const [progress, setProgress] = useState(null);
  const [logs, setLogs] = useState([]);
  const [isComplete, setIsComplete] = useState(false);
  const [error, setError] = useState(null);
  const [confirmRequest, setConfirmRequest] = useState(null);
  const [startTime, setStartTime] = useState(null);
  const socketRef = useRef(null);

  const reset = useCallback(() => {
    setProgress(null);
    setLogs([]);
    setIsComplete(false);
    setError(null);
    setConfirmRequest(null);
    setStartTime(null);
  }, []);

  const confirm = useCallback((result) => {
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify({ type: 'confirm', result }));
      setConfirmRequest(null);
    }
  }, []);

  useEffect(() => {
    if (!jobId) {
      reset();
      return;
    }

    setStartTime(Date.now());
    
    // Resolve WebSocket URL
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    // Handle path correctly for both local and Colab proxy
    const path = window.location.pathname.endsWith('/') ? window.location.pathname : window.location.pathname + '/';
    const wsUrl = `${protocol}//${host}${path}api/${tool}/${jobId}/ws`;

    console.log('Connecting to WebSocket:', wsUrl);
    const socket = new WebSocket(wsUrl);
    socketRef.current = socket;

    socket.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      
      switch (msg.type) {
        case 'progress':
          setProgress(prev => ({ ...prev, ...msg.data }));
          break;
        case 'log':
          setLogs(prev => [...prev, { 
            message: msg.data.message, 
            time: new Date().toLocaleTimeString() 
          }]);
          break;
        case 'confirm_request':
          setConfirmRequest(msg.data);
          break;
        case 'complete':
          setLogs(prev => [...prev, { 
            message: msg.data.message || 'Operation complete.', 
            time: new Date().toLocaleTimeString() 
          }]);
          setIsComplete(true);
          
          // Play success sound
          try {
            const audio = new Audio('assets/success.mp3');
            audio.volume = 0.5;
            audio.play().catch(e => console.warn('Audio playback blocked by browser:', e));
          } catch (e) {
            console.error('Failed to play success sound:', e);
          }
          
          socket.close();
          break;
        case 'error':
          setError(msg.data.message);
          socket.close();
          break;
      }
    };

    socket.onerror = (e) => {
      console.error('WebSocket Error:', e);
      setError('Connection lost.');
    };

    socket.onclose = () => {
      console.log('WebSocket Closed');
    };

    return () => {
      socket.close();
    };
  }, [jobId, tool, reset]);

  return { progress, logs, isComplete, error, confirmRequest, startTime, confirm, reset };
}
