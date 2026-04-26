// 이코노미 스쿨 Service Worker v3.27.1
const CACHE_NAME = 'economy-school-v3.27.1';
const STATIC_ASSETS = [
  './',
  './economy-app.html',
  './economy-manifest.json',
  './economy-icon-192.svg',
  './economy-icon-512.svg'
];

// 설치 시 정적 자원 캐시
self.addEventListener('install', event => {
  console.log('[Economy SW] 설치 중...');
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('[Economy SW] 캐시 추가:', STATIC_ASSETS);
        return cache.addAll(STATIC_ASSETS);
      })
      .catch(err => console.warn('[Economy SW] 캐시 실패:', err))
  );
  self.skipWaiting();
});

// 활성화 시 옛날 캐시 제거
self.addEventListener('activate', event => {
  console.log('[Economy SW] 활성화');
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(
        keys.filter(k => k !== CACHE_NAME && k.startsWith('economy-school'))
            .map(k => {
              console.log('[Economy SW] 옛날 캐시 제거:', k);
              return caches.delete(k);
            })
      )
    )
  );
  self.clients.claim();
});

// fetch 시 네트워크 우선, 실패 시 캐시
self.addEventListener('fetch', event => {
  if (event.request.method !== 'GET') return;
  if (!event.request.url.startsWith('http')) return;

  event.respondWith(
    fetch(event.request)
      .then(response => {
        if (response && response.status === 200 && response.type === 'basic') {
          const responseClone = response.clone();
          caches.open(CACHE_NAME).then(cache => {
            cache.put(event.request, responseClone);
          }).catch(() => {});
        }
        return response;
      })
      .catch(() => caches.match(event.request))
  );
});
