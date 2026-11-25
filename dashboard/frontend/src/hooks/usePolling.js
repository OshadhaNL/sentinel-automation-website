import { useEffect, useState } from 'react';

// Wait for each request to finish before scheduling another one.
export default function usePolling(load, { enabled = true, interval = 15000 } = {}) {
  const [error, setError] = useState(null);

  useEffect(() => {
    setError(null);
    if (!enabled) return;
    let timer;
    let controller;
    let active = true;

    async function refresh() {
      if (!active || document.hidden) return;
      const request = new AbortController();
      controller = request;
      try {
        await load(request.signal);
        if (!request.signal.aborted) setError(null);
      } catch (failure) {
        if (!request.signal.aborted) setError(failure);
      } finally {
        if (controller === request) controller = null;
        if (active && !request.signal.aborted && !document.hidden && interval !== null) {
          timer = setTimeout(refresh, interval);
        }
      }
    }

    function onVisibilityChange() {
      clearTimeout(timer);
      controller?.abort();
      if (!document.hidden) refresh();
    }

    timer = setTimeout(refresh, 0);
    document.addEventListener('visibilitychange', onVisibilityChange);
    return () => {
      active = false;
      clearTimeout(timer);
      controller?.abort();
      document.removeEventListener('visibilitychange', onVisibilityChange);
    };
  }, [load, enabled, interval]);

  return error;
}
