import { useEffect, useRef } from "react";

export function usePolling(
  callback: () => Promise<boolean | void>,
  enabled: boolean,
  intervalMs = 3000,
) {
  const saved = useRef(callback);

  useEffect(() => {
    saved.current = callback;
  });

  useEffect(() => {
    if (!enabled) return;

    let stopped = false;
    let timer: ReturnType<typeof setTimeout> | undefined;

    const tick = async () => {
      let done = false;
      try {
        done = (await saved.current()) === true;
      } catch {
      }
      if (!stopped && !done) timer = setTimeout(tick, intervalMs);
    };

    timer = setTimeout(tick, intervalMs);
    return () => {
      stopped = true;
      if (timer) clearTimeout(timer);
    };
  }, [enabled, intervalMs]);
}