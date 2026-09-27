(() => {
  // No cookie, localStorage identifier, query string, title or referrer is sent.
  if (location.origin !== 'https://www.peipeipe.net' || navigator.doNotTrack === '1' || navigator.globalPrivacyControl) return;
  let sent = false;
  const record = () => {
    if (sent || document.visibilityState !== 'visible') return;
    sent = true;
    const body = JSON.stringify({ path: location.pathname });
    fetch('/_analytics/collect', {
      method: 'POST', body, headers: { 'Content-Type': 'application/json' },
      credentials: 'omit', referrerPolicy: 'no-referrer', keepalive: true, cache: 'no-store',
    }).catch(() => {});
  };
  document.addEventListener('visibilitychange', record);
  record();
})();
