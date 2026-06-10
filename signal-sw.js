// INVESTMENT SIGNAL PRO — Service Worker
// Vela / v3.9.9
const CACHE = 'signal-pro-v3.9.9';
const CORE = [
  './signal-pro.html',
  './signal-manifest.json',
  './signal-icon-192.png',
  './signal-icon-512.png',
  './signal-icon-180.png',
];

// 설치 — 핵심 자산 캐시
self.addEventListener('install', (e) => {
  self.skipWaiting();
  e.waitUntil(
    caches.open(CACHE).then((c) => c.addAll(CORE).catch(() => {}))
  );
});

// 활성화 — 옛 캐시 정리
self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

// fetch 전략
self.addEventListener('fetch', (e) => {
  const url = new URL(e.request.url);

  // 외부 API(시세/AI/종목DB)는 항상 네트워크 — 캐시하지 않음
  const isDynamic =
    url.hostname.includes('yahoo') ||
    url.hostname.includes('groq') ||
    url.hostname.includes('workers.dev') ||
    url.pathname.includes('signal-stocks-db.json') ||
    url.pathname.endsWith('.json') && url.pathname.includes('stocks');

  if (isDynamic || e.request.method !== 'GET') {
    e.respondWith(fetch(e.request).catch(() => caches.match(e.request)));
    return;
  }

  // 앱 셸: 네트워크 우선, 실패 시 캐시 (최신 유지 + 오프라인 지원)
  e.respondWith(
    fetch(e.request)
      .then((res) => {
        if (res && res.status === 200 && url.origin === location.origin) {
          const clone = res.clone();
          caches.open(CACHE).then((c) => c.put(e.request, clone));
        }
        return res;
      })
      .catch(() => caches.match(e.request).then((r) => r || caches.match('./signal-pro.html')))
  );
});
