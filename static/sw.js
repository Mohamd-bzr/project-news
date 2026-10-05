/* Retired worker (tombstone).
 *
 * The page used to register this file as a second service worker, alongside the
 * offline shell in web/sw.js. It broke both jobs it had:
 *
 *   • its install precached ['/', '/locales/en.json', '/locales/fa.json'], and
 *     the locales/ directory does not exist — cache.addAll() rejects, the
 *     worker never installs cleanly, and the failure was swallowed by a
 *     console.log that claimed success;
 *   • its activate deleted EVERY cache whose name was not 'freebuff-v4' —
 *     cache storage is per-origin, not per-worker, so that wiped the shell and
 *     API caches written by the real worker and broke the offline layer.
 *
 * Nothing registers this path any more. A browser that installed it earlier
 * keeps it until the file is replaced, which this version does: it drops its
 * own cache, then unregisters itself, so the next load is uncontrolled and the
 * current worker owns the origin alone. It intentionally has no fetch handler.
 */

self.addEventListener('install', function () {
    self.skipWaiting();
});

self.addEventListener('activate', function (event) {
    event.waitUntil(
        caches.delete('freebuff-v4').catch(function () {}).then(function () {
            return self.registration.unregister();
        }).catch(function () {})
    );
});
