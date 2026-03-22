(function () {
    "use strict";

    var params = new URLSearchParams(window.location.search);
    if (!params.has("_prefetch")) {
        return;
    }

    params.delete("_prefetch");
    var cleanUrl = window.location.pathname + (params.toString() ? "?" + params.toString() : "");
    window.history.replaceState({}, "", cleanUrl);

    var pagesToPrefetch = [
        "/projects/",
        "/tasks/",
        "/documents/",
        "/ai-chat/",
        "/team/"
    ];

    var scheduleWork = window.requestIdleCallback || function (cb) {
        return setTimeout(cb, 100);
    };

    function prefetchPages(urls, index) {
        if (index >= urls.length) {
            return;
        }

        scheduleWork(function () {
            fetch(urls[index], {
                credentials: "same-origin",
                priority: "low"
            })
            .then(function () {
                prefetchPages(urls, index + 1);
            })
            .catch(function () {
                prefetchPages(urls, index + 1);
            });
        });
    }

    if (document.readyState === "complete") {
        prefetchPages(pagesToPrefetch, 0);
    } else {
        window.addEventListener("load", function () {
            prefetchPages(pagesToPrefetch, 0);
        });
    }
})();
