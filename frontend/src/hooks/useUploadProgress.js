import { useRef, useState } from "react";

export function useUploadProgress({ initial = 10, ceiling = 92, step = 6, intervalMs = 350, advance } = {}) {
  const timerRef = useRef(null);
  const [progress, setProgress] = useState(0);

  function start() {
    stop();
    setProgress(initial);
    timerRef.current = window.setInterval(() => {
      setProgress((value) => {
        const nextValue = advance ? advance(value, ceiling) : value + step;
        return Math.min(ceiling, nextValue);
      });
    }, intervalMs);
  }

  function complete() {
    stop();
    setProgress(100);
  }

  function reset() {
    stop();
    setProgress(0);
  }

  function stop() {
    if (timerRef.current) {
      window.clearInterval(timerRef.current);
      timerRef.current = null;
    }
  }

  return { progress, start, complete, reset, stop };
}
