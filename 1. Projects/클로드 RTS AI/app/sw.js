// RTS 앱 서비스워커 — 오프라인 캐시 + PWA 설치 가능하게 만드는 최소 구현
// v3: three.js를 UMD(three.min.js)에서 ES 모듈(three.module.js + GLTFLoader)로 전환,
//     실제 근육 3D 자산(assets/) 추가 — 캐시명을 올려 예전 사용자 캐시를 자동 정리.
const CACHE_NAME = "rts-app-v4";
const ASSETS = [
  "./",
  "./index.html",
  "./style.css",
  "./app.js",
  "./viz.js",
  "./vendor/three.module.js",
  "./vendor/loaders/GLTFLoader.js",
  "./vendor/utils/BufferGeometryUtils.js",
  "./assets/muscles.glb",
  "./assets/muscle_object_mapping.json",
  "./data.json",
  "./viz_data.json",
  "./muscle_map.json",
  "./manifest.json",
  "./icons/icon-192.png",
  "./icons/icon-512.png"
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(ASSETS)).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  event.respondWith(
    caches.match(event.request).then((cached) => {
      const fetchPromise = fetch(event.request).then((resp) => {
        if (resp && resp.status === 200 && event.request.method === "GET") {
          const respClone = resp.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, respClone));
        }
        return resp;
      }).catch(() => cached);
      return cached || fetchPromise;
    })
  );
});
