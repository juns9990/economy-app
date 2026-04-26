// INVESTMENT SIGNAL PRO - Service Worker v2
const CACHE = 'signal-pro-v3.7.6';
const ASSETS = [
  './signal-pro.html',
  './signal-manifest.json',
  './signal-icon-192.png',
  './signal-icon-512.png',
];

self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE).then(c => c.addAll(ASSETS)).catch(() => {})
  );
  self.skipWaiting();
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  // 실시간 데이터 API는 캐시하지 않음
  const url = e.request.url;
  if (url.includes('groq.com') || url.includes('yahoo') || url.includes('workers.dev') || url.includes('finance.yahoo')) {
    return;
  }
  // 그 외는 네트워크 우선, 실패시 캐시
  e.respondWith(
    fetch(e.request).catch(() => caches.match(e.request))
  );
});
