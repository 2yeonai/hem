// AI 공장 허브 서비스워커 — 오프라인 캐시 + PWA 설치 가능하게 만드는 최소 구현
// scope는 볼트 루트("/")로 등록한다 (index.html에서
// navigator.serviceWorker.register("...sw.js", { scope: "/" }) 로 등록).
// 그래야 이 허브 폴더 밖(각 공장의 ui/ 폴더)에 있는 원본 승인화면 목업들도
// 같은 서비스워커가 캐시/오프라인 처리를 해줄 수 있다.
const CACHE_NAME = "ai공장허브-v1";

const HUB_BASE = "/1. Projects/ai공장짓기/AI공장_모바일허브";

const ASSETS = [
  `${HUB_BASE}/index.html`,
  `${HUB_BASE}/manifest.json`,
  `${HUB_BASE}/icons/icon-192.png`,
  `${HUB_BASE}/icons/icon-512.png`,
  "/1. Projects/클로드 방역 ai/ui/승인화면_프로토타입_v1.html",
  "/1. Projects/클로드 꽃집 ai/ui/승인화면_프로토타입_v1.html",
  "/1. Projects/클로드 정부지원사업 ai/ui/승인화면_프로토타입_v1.html",
  "/1. Projects/클로드 RTS AI/app/index.html",
].map((p) => encodeURI(p));

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
  if (event.request.method !== "GET") return;
  event.respondWith(
    caches.match(event.request).then((cached) => {
      const fetchPromise = fetch(event.request).then((resp) => {
        if (resp && resp.status === 200) {
          const respClone = resp.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, respClone));
        }
        return resp;
      }).catch(() => cached);
      return cached || fetchPromise;
    })
  );
});
