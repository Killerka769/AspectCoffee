/* Морфинг иконок работает везде. Курсор, магнит и наклон — только у мыши. */
(function () {
  "use strict";

  var reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var coarse = window.matchMedia("(pointer: coarse)").matches;
  var fine = window.matchMedia("(pointer: fine) and (hover: hover)").matches && !coarse;

  if (!reduce) initMorph();
  if (!fine || reduce) return;

  var root = document.documentElement;
  var cursor = document.querySelector(".aspect-cursor");
  var dot = cursor ? cursor.querySelector(".aspect-cursor__dot") : null;
  var ring = cursor ? cursor.querySelector(".aspect-cursor__ring") : null;
  var label = cursor ? cursor.querySelector(".aspect-cursor__label") : null;
  if (!cursor || !dot || !ring || !label) return;

  root.classList.add("aspect-cursor-on");

  var targetX = 0;
  var targetY = 0;
  var dotX = 0;
  var dotY = 0;
  var ringX = 0;
  var ringY = 0;
  var seen = false;
  var running = false;
  var lastMove = 0;
  var magnets = new Map();
  var activeMagnet = null;
  var tilt = null;
  var mode = "";

  function clamp(value, limit) {
    return Math.max(-limit, Math.min(limit, value));
  }

  function magnetState(el) {
    var state = magnets.get(el);
    if (!state) {
      state = { x: 0, y: 0, tx: 0, ty: 0 };
      magnets.set(el, state);
    }
    return state;
  }

  function resetCard(card) {
    if (!card) return;
    card.classList.remove("is-tilting");
    card.style.transform = "";
    var img = card.querySelector(".aspect-card__media img");
    if (img) img.style.transform = "";
  }

  function setMode(next) {
    if (next === mode) return;
    mode = next;
    cursor.classList.toggle("is-view", next === "view");
    cursor.classList.toggle("is-read", next === "read");
    cursor.classList.toggle("is-buy", next === "buy");
    label.textContent = next === "view" ? "СМОТРЕТЬ" : next === "read" ? "READ" : next === "buy" ? "+" : "";
  }

  function modeFrom(target) {
    if (!target || !target.closest) return "";
    if (target.closest("input, textarea, select, [contenteditable='true']")) return "";
    if (target.closest(".aspect-card__buy, .aspect-pd__buy, .aspect-btn-pay")) return "buy";
    if (target.closest(".asp-jrn__card-img, .asp-jrn__card-title, .asp-art__side-item")) return "read";
    if (target.closest(".aspect-card")) return "view";
    return "";
  }

  function apply() {
    var moving = false;

    dotX += (targetX - dotX) * 0.45;
    dotY += (targetY - dotY) * 0.45;
    ringX += (targetX - ringX) * 0.16;
    ringY += (targetY - ringY) * 0.16;
    if (Math.abs(targetX - ringX) > 0.4 || Math.abs(targetY - ringY) > 0.4) moving = true;

    dot.style.transform = "translate3d(" + dotX.toFixed(2) + "px," + dotY.toFixed(2) + "px,0) translate(-50%,-50%)";
    ring.style.transform = "translate3d(" + ringX.toFixed(2) + "px," + ringY.toFixed(2) + "px,0) translate(-50%,-50%)";

    magnets.forEach(function (state, el) {
      if (!el.isConnected) {
        magnets.delete(el);
        return;
      }
      state.x += (state.tx - state.x) * 0.22;
      state.y += (state.ty - state.y) * 0.22;
      if (Math.abs(state.tx - state.x) > 0.3 || Math.abs(state.ty - state.y) > 0.3) moving = true;
      if (Math.abs(state.x) < 0.2 && Math.abs(state.y) < 0.2 && state.tx === 0 && state.ty === 0) {
        el.style.transform = "";
        magnets.delete(el);
        return;
      }
      el.style.transform = "translate3d(" + state.x.toFixed(2) + "px," + state.y.toFixed(2) + "px,0)";
    });

    if (tilt && tilt.card.isConnected && !tilt.card.classList.contains("card-popup-open")) {
      tilt.rx += (tilt.tx - tilt.rx) * 0.18;
      tilt.ry += (tilt.ty - tilt.ry) * 0.18;
      tilt.ix += (tilt.tix - tilt.ix) * 0.18;
      tilt.iy += (tilt.tiy - tilt.iy) * 0.18;
      if (Math.abs(tilt.tx - tilt.rx) > 0.05 || Math.abs(tilt.ty - tilt.ry) > 0.05) moving = true;
      tilt.card.style.transform =
        "perspective(900px) rotateX(" + (-tilt.ry).toFixed(2) + "deg) rotateY(" + tilt.rx.toFixed(2) + "deg)";
      if (tilt.img) {
        tilt.img.style.transform =
          "translate3d(" + tilt.ix.toFixed(2) + "px," + tilt.iy.toFixed(2) + "px,0) scale(1.06)";
      }
    }

    return moving;
  }

  function kick() {
    lastMove = performance.now();
    if (running) return;
    running = true;
    requestAnimationFrame(function frame(now) {
      var moving = apply();
      if (moving || now - lastMove < 600) {
        requestAnimationFrame(frame);
      } else {
        running = false;
      }
    });
  }

  document.addEventListener("pointermove", function (event) {
    if (event.pointerType && event.pointerType !== "mouse") return;
    targetX = event.clientX;
    targetY = event.clientY;
    if (!seen) {
      dotX = ringX = targetX;
      dotY = ringY = targetY;
      seen = true;
      cursor.classList.add("is-on");
    }

    var typing = event.target.closest && event.target.closest("input, textarea, select, [contenteditable='true']");
    cursor.classList.toggle("is-hidden", !!typing);
    var hot = !typing && event.target.closest && event.target.closest("a, button, summary, [role='button']");
    cursor.classList.toggle("is-hot", !!hot);
    setMode(typing ? "" : modeFrom(event.target));

    var magnet = event.target.closest && event.target.closest(".aspect-btn, .aspect-hero__cta");
    if (activeMagnet && activeMagnet !== magnet) {
      var previous = magnets.get(activeMagnet);
      if (previous) {
        previous.tx = 0;
        previous.ty = 0;
      }
    }
    activeMagnet = magnet;
    if (magnet && !magnet.disabled) {
      var box = magnet.getBoundingClientRect();
      var state = magnetState(magnet);
      state.tx = clamp((event.clientX - (box.left + box.width / 2)) * 0.35, 14);
      state.ty = clamp((event.clientY - (box.top + box.height / 2)) * 0.35, 14);
    }

    var card = event.target.closest && event.target.closest(".aspect-card");
    if (card && card.classList.contains("card-popup-open")) {
      resetCard(card);
      if (tilt && tilt.card === card) tilt = null;
      card = null;
    }
    if (tilt && (!card || card !== tilt.card)) {
      resetCard(tilt.card);
      tilt = null;
    }
    if (card && !card.classList.contains("card-popup-open")) {
      var rect = card.getBoundingClientRect();
      var px = (event.clientX - rect.left) / rect.width - 0.5;
      var py = (event.clientY - rect.top) / rect.height - 0.5;
      if (!tilt) {
        tilt = { card: card, img: card.querySelector(".aspect-card__media img"), rx: 0, ry: 0, ix: 0, iy: 0, tx: 0, ty: 0, tix: 0, tiy: 0 };
        card.classList.add("is-tilting");
      }
      tilt.tx = px * 8;
      tilt.ty = py * 7;
      tilt.tix = px * 12;
      tilt.tiy = py * 8;
    }

    kick();
  }, { passive: true });

  document.addEventListener("pointerdown", function (event) {
    if (event.pointerType === "touch") {
      root.classList.remove("aspect-cursor-on");
      cursor.classList.remove("is-on");
      setMode("");
    }
  }, { passive: true });

  window.addEventListener("blur", function () {
    cursor.classList.remove("is-hot");
    setMode("");
    if (activeMagnet && magnets.get(activeMagnet)) {
      magnets.get(activeMagnet).tx = 0;
      magnets.get(activeMagnet).ty = 0;
    }
    if (tilt) {
      resetCard(tilt.card);
      tilt = null;
    }
    kick();
  });

  function initMorph() {
    var cartTimer = 0;

    function popCart() {
      var button = document.querySelector(".header-cart__btn");
      if (!button) return;
      button.classList.remove("is-cart-ack");
      void button.offsetWidth;
      button.classList.add("is-cart-ack");
      window.clearTimeout(cartTimer);
      cartTimer = window.setTimeout(function () {
        button.classList.remove("is-cart-ack");
      }, 820);
    }

    document.body.addEventListener("cartUpdated", function (event) {
      var detail = event.detail || {};
      if (!detail.variantId && !detail.added) return;
      popCart();
    });

    document.body.addEventListener("wishlistAdded", function (event) {
      var heart = event.detail && event.detail.el;
      if (!heart || !heart.isConnected) return;
      heart.classList.remove("is-heartbeat");
      void heart.offsetWidth;
      heart.classList.add("is-heartbeat");
      var bits = heart.querySelectorAll(".aspect-heart-bit");
      bits.forEach(function (bit) { bit.remove(); });
      for (var i = 0; i < 5; i++) {
        var bit = document.createElement("span");
        bit.className = "aspect-heart-bit";
        var angle = (-120 + i * 30) * Math.PI / 180;
        var dist = 16 + i * 3;
        bit.style.setProperty("--dx", (Math.cos(angle) * dist).toFixed(1) + "px");
        bit.style.setProperty("--dy", (Math.sin(angle) * dist).toFixed(1) + "px");
        heart.appendChild(bit);
      }
      window.setTimeout(function () {
        heart.classList.remove("is-heartbeat");
        heart.querySelectorAll(".aspect-heart-bit").forEach(function (bit) { bit.remove(); });
      }, 720);
    });
  }
})();
