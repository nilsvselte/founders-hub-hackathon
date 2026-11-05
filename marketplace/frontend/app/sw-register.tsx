"use client";

import { useEffect } from "react";

/** Registers /sw.js once the page loads, so the app can be installed and receive push. */
export function ServiceWorkerRegister() {
  useEffect(() => {
    if (!("serviceWorker" in navigator)) return;
    navigator.serviceWorker.register("/sw.js", { scope: "/" }).catch(() => {
      // Without a service worker the site still works; install and push are unavailable.
    });
  }, []);
  return null;
}
