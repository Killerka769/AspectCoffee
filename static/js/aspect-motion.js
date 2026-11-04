/**
 * Aspect Coffee — scroll reveal, hero parallax, buy-button pulse
 * Не трогает логику корзины / форм.
 */
(function () {
  "use strict";

  var REVEAL_SELECTOR =
    ".aspect-card, .aspect-section__head, .aspect-banner, .aspect-hero__card, " +
    ".aspect-type-card, .aspect-usp__item, .aspect-cta, .aspect-promo, .aspect-review";

  function motionReduced() {
    return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  }

  function markRevealTargets(root) {
    if (motionReduced()) return;
    var scope = root || document;
    scope.querySelectorAll(REVEAL_SELECTOR).forEach(function (el) {
      if (el.classList.contains("aspect-reveal")) return;
      if (el.closest(".aspect-marquee")) return;
      el.classList.add("aspect-reveal");
    });
  }

  var revealObserver = null;

  function initReveal(root) {
    if (motionReduced()) return null;
    markRevealTargets(root || document);

    if (!("IntersectionObserver" in window)) {
      document.querySelectorAll(".aspect-reveal").forEach(function (el) {
        el.classList.add("is-inview");
      });
      return null;
    }

    var observer = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (!entry.isIntersecting) return;
          entry.target.classList.add("is-inview");
          observer.unobserve(entry.target);
        });
      },
      { root: null, rootMargin: "0px 0px -8% 0px", threshold: 0.08 }
    );

    revealObserver = observer;

    function observeIn(scope) {
      (scope || document).querySelectorAll(".aspect-reveal:not(.is-inview)").forEach(function (el) {
        observer.observe(el);
      });
    }

    observeIn(root || document);

    requestAnimationFrame(function () {
      document.querySelectorAll(".aspect-reveal:not(.is-inview)").forEach(function (el) {
        var rect = el.getBoundingClientRect();
        if (rect.top < window.innerHeight * 0.92 && rect.bottom > 0) {
          el.classList.add("is-inview");
          observer.unobserve(el);
        }
      });
    });

    return observer;
  }

  function initParallax() {
    if (motionReduced()) return;
    var layer = document.querySelector("[data-aspect-parallax]");
    if (!layer) return;

    var ticking = false;

    function update() {
      ticking = false;
      if (window.innerWidth < 768) {
        layer.style.transform = "";
        return;
      }
      var hero = layer.closest(".aspect-hero") || layer;
      var rect = hero.getBoundingClientRect();
      if (rect.bottom < 0 || rect.top > window.innerHeight) return;
      var shift = Math.max(-40, Math.min(40, -rect.top * 0.06));
      layer.style.transform = "translate3d(0, " + shift.toFixed(2) + "px, 0)";
    }

    function onScroll() {
      if (!ticking) {
        ticking = true;
        requestAnimationFrame(update);
      }
    }

    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll, { passive: true });
    update();
  }

  function initBuyPulse() {
    if (motionReduced()) return;
    document.addEventListener(
      "click",
      function (e) {
        var btn = e.target.closest(".aspect-card__buy, .aspect-pd__buy");
        if (!btn || btn.disabled) return;
        btn.classList.remove("aspect-click-pulse");
        void btn.offsetWidth;
        btn.classList.add("aspect-click-pulse");
        btn.addEventListener(
          "animationend",
          function () {
            btn.classList.remove("aspect-click-pulse");
          },
          { once: true }
        );
      },
      true
    );
  }

  function boot(root) {
    if (!document.documentElement.classList.contains("js")) return;
    revealObserver = initReveal(root);
    initParallax();
    initBuyPulse();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () {
      boot();
    });
  } else {
    boot();
  }

  document.body.addEventListener("htmx:afterSettle", function (e) {
    var elt = e.detail && e.detail.elt ? e.detail.elt : document;
    markRevealTargets(elt);
    if (revealObserver) {
      elt.querySelectorAll(".aspect-reveal:not(.is-inview)").forEach(function (el) {
        revealObserver.observe(el);
      });
    }
  });
})();
