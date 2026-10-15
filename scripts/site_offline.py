"""The offline page and the service worker behind it.

A visitor who loses the connection should still read the pages they already opened, and
see a designed page, not the browser's dinosaur, for any other. Two files do that, both
written by ``build_catalogue_site.build``:

* ``/offline/`` is a page of the site, in the 404's language and inside the site chrome.
  The worker precaches it and serves it for a navigation it can answer from nowhere else.
  Its script lists the pages the worker has kept, read from the Cache API.
* ``/sw.js`` is served from the root, so its scope is the whole site.

The page is ``offline/index.html`` and not ``offline.html`` because of the Worker's
``auto-trailing-slash`` html_handling: it answers ``/offline.html`` with a redirect, and a
redirected response stored in a cache cannot be served for a navigation (the browser
rejects it). A directory index is served 200 at ``/offline/`` with no redirect, which is
the address the worker precaches and the address every other page of the site uses.

What the worker keeps, and why that is safe on this site:

* Pages are cached only when the response is a plain 200 from this origin, is HTML and
  was not redirected. The stage site sits behind Cloudflare Access, whose sign-in is a
  redirect to another origin; that response is never stored and never served as content.
* Fonts and icons are cache first because their names are hashed or never change.
* Everything else, every non-GET request and every other origin is left to the browser.
* The caches carry the build version in their name. A new deploy installs a worker with a
  new name, deletes the caches of older ones, and so drops pages whose inline CSS names
  fonts that deploy no longer ships. That is deliberate: a page kept across a deploy would
  paint with a missing font, so the page and the fonts it names live and die together.
* The page a visitor first lands on loads before any worker exists, so the worker fetches
  the pages open in its windows once, when it takes control, and keeps them by the same
  rule. Without that the first page of a first visit would never be saved.

Retiring the worker. Deleting ``/sw.js`` does not remove it: a browser that gets a 404
for an update check keeps the worker it has, with its caches, and keeps running it.
Network first means it never serves a stale page while the site answers, but to take it
away for good, ship a ``/sw.js`` whose ``install`` calls ``self.skipWaiting()`` and whose
``activate`` deletes every cache named ``ai-site-*``, calls
``self.registration.unregister()`` and then navigates each window client to its own URL.
Keep that file deployed, with the same ``no-cache`` header, until returning visitors have
had time to fetch it, and remove the registration snippet from the pages in the same
deploy.
"""

from __future__ import annotations

import json

import site_errors
import site_style

OFFLINE_PATH = "/offline/"
SW_PATH = "/sw.js"
# Every cache this worker makes starts with this, which is how it finds its own old ones
# and nothing else on the origin.
CACHE_PREFIX = "ai-site-"
STATIC_SUFFIX = "-static"
PAGES_SUFFIX = "-pages"
MAX_PAGES = 60

# The icons the build writes; only the tab icon is stored at install.
PRECACHE_ICON = "/favicon.png"
IMMUTABLE_ICONS = ("/favicon.png", "/apple-touch-icon.png")


def precache_urls() -> list[str]:
    """What the worker stores at install: the offline page, the tab icon and the two faces.

    Nothing else. The licence texts under ``/fonts/`` are fetched on demand if ever asked
    for, and a page is stored only after the visitor has opened it.
    """
    return [OFFLINE_PATH, PRECACHE_ICON, site_style.SANS_URL, site_style.SERIF_URL]


SW_TEMPLATE = r"""/* The catalogue's service worker, from scripts/site_offline.py: do not edit.
   It exists so a visitor who goes offline still reads the pages already opened and sees
   the offline page for any other. It does nothing else and talks to no other origin. */
"use strict";

var PREFIX = @@PREFIX@@;
var STATIC = PREFIX + @@VERSION@@ + @@STATIC_SUFFIX@@; // offline page, icon, fonts
var PAGES = PREFIX + @@VERSION@@ + @@PAGES_SUFFIX@@; // pages the visitor opened
var OFFLINE = @@OFFLINE@@;
var PRECACHE = @@PRECACHE@@;
var IMMUTABLE_ICONS = @@ICONS@@;
var FONTS = @@FONTS@@;
var MAX_PAGES = @@MAX_PAGES@@;

// A response worth keeping: a plain 200 from this origin that was not redirected. An
// opaque or redirected response is never stored, so Cloudflare Access's sign-in redirect
// can never come back later as if it were the page. A non-200 is never stored either.
function plain(response) {
  return response.status === 200 && response.type === "basic" && !response.redirected;
}

function isHtml(response) {
  var type = response.headers.get("content-type") || "";
  return type.toLowerCase().indexOf("text/html") === 0;
}

// Pages are keyed by path alone: the site ignores the query string, so ?a=1 and ?a=2 are
// one page and cannot fill the cache with copies of it.
function pageKey(url) {
  return new Request(url.origin + url.pathname);
}

self.addEventListener("install", function (event) {
  // cache: "reload" skips the HTTP cache, so a new version never precaches an old file.
  // One failure rejects the install, and the previous worker keeps serving.
  event.waitUntil(
    caches.open(STATIC).then(function (cache) {
      return Promise.all(PRECACHE.map(function (url) {
        return fetch(new Request(url, { cache: "reload" })).then(function (response) {
          if (!plain(response)) throw new Error("cannot precache " + url);
          return cache.put(url, response);
        });
      }));
    }).then(function () {
      // The pages and fonts of one deploy go together, so a new worker takes over at once
      // rather than waiting for every tab to close.
      return self.skipWaiting();
    })
  );
});

self.addEventListener("activate", function (event) {
  event.waitUntil(
    caches.keys().then(function (names) {
      return Promise.all(names.filter(function (name) {
        // Prefix match only: a cache this worker did not make is not its to delete.
        return name.indexOf(PREFIX) === 0 && name !== STATIC && name !== PAGES;
      }).map(function (name) { return caches.delete(name); }));
    }).then(function () {
      return self.clients.claim();
    }).then(keepOpenPages)
  );
});

// The page a visitor lands on first was loaded before this worker existed, so no fetch
// event saw it. Fetch the pages open in this worker's windows once, and keep them by the
// same rule a navigation uses. Best effort: a failure here must not stop activation.
function keepOpenPages() {
  return self.clients.matchAll({ type: "window" }).then(function (windows) {
    return Promise.all(windows.map(function (client) {
      var url = new URL(client.url);
      if (url.origin !== self.location.origin || url.pathname === OFFLINE) return null;
      return fetch(url.origin + url.pathname + url.search).then(function (response) {
        if (plain(response) && isHtml(response)) return remember(pageKey(url), response);
        return null;
      }).catch(function () { return null; });
    }));
  }).catch(function () { return null; });
}

// Keep the newest MAX_PAGES. cache.keys() is in insertion order and a page is deleted
// before it is put again, so the front of the list is the page opened longest ago.
function remember(key, response) {
  return caches.open(PAGES).then(function (cache) {
    return cache.delete(key).then(function () {
      return cache.put(key, response);
    }).then(function () {
      return cache.keys();
    }).then(function (keys) {
      return Promise.all(keys.slice(0, Math.max(0, keys.length - MAX_PAGES)).map(function (old) {
        return cache.delete(old);
      }));
    });
  });
}

function fromCaches(url) {
  return caches.open(PAGES).then(function (cache) {
    return cache.match(pageKey(url)).then(function (hit) {
      var last = url.pathname.split("/").pop();
      if (hit || url.pathname.slice(-1) === "/" || last.indexOf(".") !== -1) return hit;
      // /family and /family/ are one page; the Worker redirects one to the other.
      return cache.match(new Request(url.origin + url.pathname + "/"));
    });
  });
}

function offlinePage() {
  return caches.open(STATIC).then(function (cache) {
    return cache.match(OFFLINE);
  }).then(function (hit) {
    return hit || new Response("You are offline.", {
      status: 503,
      headers: { "Content-Type": "text/plain; charset=utf-8" }
    });
  });
}

// Network first, so a page is never older than the connection allows. A copy is made
// only of a good HTML page, and only after the network has answered.
function navigate(event) {
  var url = new URL(event.request.url);
  return fetch(event.request).then(function (response) {
    if (plain(response) && isHtml(response) && url.pathname !== OFFLINE) {
      var copy = response.clone();
      // Best effort: a full disk must not turn a good page into an error.
      event.waitUntil(remember(pageKey(url), copy).catch(function () {}));
    }
    return response;
  }, function () {
    return fromCaches(url).then(function (hit) {
      return hit || offlinePage();
    });
  });
}

// Fonts and icons never change under one name, so the cache wins and the network is the
// fallback for one that was not precached.
function immutable(event) {
  return caches.open(STATIC).then(function (cache) {
    return cache.match(event.request).then(function (hit) {
      if (hit) return hit;
      return fetch(event.request).then(function (response) {
        if (plain(response)) event.waitUntil(cache.put(event.request, response.clone()));
        return response;
      });
    });
  });
}

self.addEventListener("fetch", function (event) {
  var request = event.request;
  // Not intercepted at all, so the browser handles them as if there were no worker: any
  // method but GET, any other origin, and every address that is not a page, font or icon.
  if (request.method !== "GET") return;
  var url = new URL(request.url);
  if (url.origin !== self.location.origin) return;
  if (request.mode === "navigate") {
    event.respondWith(navigate(event));
  } else if (url.pathname.indexOf(FONTS) === 0 || IMMUTABLE_ICONS.indexOf(url.pathname) !== -1) {
    event.respondWith(immutable(event));
  }
});
"""


def _js(value: object) -> str:
    return json.dumps(value, ensure_ascii=True)


def render_worker(version: str) -> str:
    """The service worker for one build. ``version`` is already a safe single token."""
    values = {
        "PREFIX": CACHE_PREFIX,
        "VERSION": version,
        "STATIC_SUFFIX": STATIC_SUFFIX,
        "PAGES_SUFFIX": PAGES_SUFFIX,
        "OFFLINE": OFFLINE_PATH,
        "PRECACHE": precache_urls(),
        "ICONS": list(IMMUTABLE_ICONS),
        "FONTS": site_style.FONT_URL_PREFIX,
        "MAX_PAGES": MAX_PAGES,
    }
    text = SW_TEMPLATE
    for name, value in values.items():
        text = text.replace(f"@@{name}@@", _js(value))
    return text


# Registered after the load event so the worker's install never competes with the page
# for bandwidth, and only where a worker can run at all. A failed registration is not the
# visitor's problem: the site works exactly as it did without one.
REGISTER_SCRIPT = (
    '(function(){if(!("serviceWorker" in navigator)||!window.isSecureContext)return;'
    'window.addEventListener("load",function(){'
    f'navigator.serviceWorker.register("{SW_PATH}").catch(function(){{}});}});}})();'
)


# ----------------------------------------------------------------------- the offline page

OFFLINE_LETTERS = (("o", "f"), ("f", "i"), ("f", "y"))

OFFLINE_SCRIPT_TEMPLATE = r"""
(function () {
  var retry = document.getElementById("offline-retry");
  if (retry) {
    retry.hidden = false;
    retry.addEventListener("click", function () { window.location.reload(); });
  }
  var box = document.getElementById("offline-saved");
  var list = document.getElementById("offline-list");
  var none = document.getElementById("offline-none");
  if (!box || !list || !none) return;
  var PREFIX = @@PREFIX@@;
  var SUFFIX = @@SUFFIX@@;
  var OFFLINE = @@OFFLINE@@;
  function title(response, path) {
    return response.text().then(function (text) {
      var found = new DOMParser().parseFromString(text.slice(0, 2048), "text/html").title;
      // Every title ends in the site's name, which the heading above already says; the
      // front page's is that name alone.
      found = found.replace(/ · AI$/, "");
      return found && found !== "AI" ? found : path === "/" ? "Home" : path;
    }, function () { return path; });
  }
  function show(items) {
    items.forEach(function (item) {
      var row = document.createElement("li");
      var link = document.createElement("a");
      var name = document.createElement("span");
      var kind = document.createElement("span");
      link.setAttribute("href", item.path);
      name.className = "lost-name";
      name.textContent = item.title;
      kind.className = "lost-kind";
      kind.textContent = item.path;
      link.appendChild(name);
      link.appendChild(kind);
      row.appendChild(link);
      list.appendChild(row);
    });
    box.hidden = !items.length;
    none.hidden = items.length > 0;
  }
  if (!window.caches) { none.hidden = false; return; }
  caches.keys().then(function (names) {
    var mine = names.filter(function (name) {
      return name.indexOf(PREFIX) === 0 && name.slice(-SUFFIX.length) === SUFFIX;
    });
    return Promise.all(mine.map(function (name) {
      return caches.open(name).then(function (cache) {
        return cache.keys().then(function (requests) {
          return requests.reverse().map(function (request) {
            return { cache: cache, request: request };
          });
        });
      });
    }));
  }).then(function (groups) {
    var seen = {};
    var found = [];
    groups.forEach(function (group) {
      group.forEach(function (entry) {
        var url = new URL(entry.request.url);
        var path = url.pathname;
        // Same origin and a rooted path only: a link built from a cache key must never
        // leave the site, so "//host" and anything else is dropped.
        if (url.origin !== window.location.origin || path.charAt(0) !== "/") return;
        if (path.charAt(1) === "/" || path === OFFLINE || seen[path]) return;
        seen[path] = true;
        found.push(entry);
      });
    });
    return Promise.all(found.map(function (entry) {
      return entry.cache.match(entry.request).then(function (response) {
        var type = response && response.headers.get("content-type") || "";
        if (type.toLowerCase().indexOf("text/html") !== 0) return null;
        var path = new URL(entry.request.url).pathname;
        return title(response, path).then(function (text) {
          return { path: path, title: text };
        });
      });
    }));
  }).then(function (items) {
    show(items.filter(Boolean));
  }, function () { show([]); });
})();
"""


def render_offline_script() -> str:
    text = OFFLINE_SCRIPT_TEMPLATE
    for name, value in (
        ("PREFIX", CACHE_PREFIX),
        ("SUFFIX", PAGES_SUFFIX),
        ("OFFLINE", OFFLINE_PATH),
    ):
        text = text.replace(f"@@{name}@@", _js(value))
    return text


def offline_main(back: str) -> str:
    """The body of the offline page. ``back`` is the site's Back link, already built.

    The list of saved pages starts hidden and only the script reveals it, so without
    script the page is the heading, the sentence and a Try again link. That link has an
    empty ``href``, which is the address the visitor asked for, so it asks again.
    """
    letters = "".join(
        f'<span class="ld stage-{stage}">{letter}</span>' for letter, stage in OFFLINE_LETTERS
    )
    return (
        '<div class="page narrow lost">\n'
        f"{back}\n"
        '<h1 class="title lost-word"><span class="sr-only">You are offline</span>'
        f'<span class="typed" aria-hidden="true">{letters}<span class="caret"></span></span>'
        "</h1>\n"
        '<p class="lede">You\'re offline. This page is not saved on this device, and there '
        "is no connection to fetch it.</p>\n"
        '<section class="lost-suggest" id="offline-saved" aria-labelledby="offline-saved-h" '
        "hidden>\n"
        '<h2 id="offline-saved-h">Saved on this device</h2>\n<ul id="offline-list"></ul>\n'
        "</section>\n"
        '<p class="lost-asked" id="offline-none" hidden>No pages are saved on this device '
        "yet.</p>\n"
        '<p class="lost-asked">Pages you open are kept in this browser, and nowhere else, so '
        "you can read them again without a connection.</p>\n"
        '<div class="lost-links">'
        '<button type="button" class="pill" id="offline-retry" hidden>Try again</button>'
        '<noscript><a class="pill" href="">Try again</a></noscript></div>\n'
        "</div>"
    )


# The 404's own stylesheet supplies the heading, the list and the actions; this page adds
# nothing, so the two read as one place.
OFFLINE_CSS = site_errors.LOST_CSS
