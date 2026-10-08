/* LittleMove — storefront interactions
   Progressive enhancement: everything degrades gracefully without JS.
   Features: loader, Swiper sliders, GSAP reveals, 3D tilt, cart drawer,
   quick view, wishlist, sale popup, chatbot API, AJAX add-to-cart,
   search suggestions, confetti, bottom-nav active state. */
(function () {
  "use strict";

  var REDUCED = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var $ = function (sel, root) { return (root || document).querySelector(sel); };
  var $$ = function (sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); };

  function getCookie(name) {
    var m = document.cookie.match("(^|;)\\s*" + name + "\\s*=\\s*([^;]+)");
    return m ? decodeURIComponent(m.pop()) : "";
  }
  function csrf() { return getCookie("csrftoken"); }
  function rs(n) { return "Rs " + Number(n || 0).toLocaleString("en-PK"); }

  /* ---------------- 1. Logo loader (once per session) ---------------- */
  (function loader() {
    var el = document.getElementById("loader-overlay");
    if (!el) return;
    if (sessionStorage.getItem("lm_loaded")) { el.remove(); return; }
    window.addEventListener("load", function () {
      sessionStorage.setItem("lm_loaded", "1");
      setTimeout(function () {
        el.classList.add("hide");
        setTimeout(function () { el.remove(); }, 450);
      }, REDUCED ? 100 : 650);
    });
    // safety: never trap the user
    setTimeout(function () { if (el.parentNode) { el.classList.add("hide"); } }, 4000);
  })();

  /* ---------------- 2. Swiper hero / testimonials / pdp ---------------- */
  function initSwipers() {
    if (typeof Swiper === "undefined") return;
    var hero = $(".hero-swiper");
    if (hero && !hero.swiper) {
      new Swiper(hero, {
        loop: hero.querySelectorAll(".swiper-slide").length > 1,
        effect: REDUCED ? "slide" : "creative",
        creativeEffect: {
          prev: { shadow: true, translate: ["-20%", 0, -200] },
          next: { translate: ["100%", 0, 0] }
        },
        autoplay: REDUCED ? false : { delay: 5000, disableOnInteraction: false },
        pagination: { el: hero.querySelector(".swiper-pagination"), clickable: true },
        navigation: {
          prevEl: hero.querySelector(".swiper-button-prev"),
          nextEl: hero.querySelector(".swiper-button-next")
        }
      });
    }
    var ts = $(".testimonials-swiper");
    if (ts && !ts.swiper) {
      new Swiper(ts, {
        slidesPerView: 1, spaceBetween: 18, grabCursor: true,
        autoplay: REDUCED ? false : { delay: 4500, disableOnInteraction: false },
        pagination: { el: ts.querySelector(".swiper-pagination"), clickable: true },
        breakpoints: { 700: { slidesPerView: 2 }, 1000: { slidesPerView: 3 } }
      });
    }
    var thumbs = $(".pdp-thumbs");
    var main = $(".pdp-swiper");
    if (main && !main.swiper) {
      var thumbSwiper = null;
      if (thumbs && !thumbs.swiper) {
        thumbSwiper = new Swiper(thumbs, {
          slidesPerView: 4, spaceBetween: 8, watchSlidesProgress: true
        });
      }
      new Swiper(main, {
        spaceBetween: 10,
        pagination: { el: main.querySelector(".swiper-pagination"), clickable: true },
        thumbs: thumbSwiper ? { swiper: thumbSwiper } : undefined
      });
    }
  }

  /* ---------------- 3. GSAP ScrollTrigger reveals ---------------- */
  function initReveals() {
    var els = $$(".reveal");
    if (!els.length) return;
    if (REDUCED || typeof gsap === "undefined" || typeof ScrollTrigger === "undefined") {
      els.forEach(function (el) { el.classList.add("is-in"); });
      return;
    }
    gsap.registerPlugin(ScrollTrigger);
    els.forEach(function (el) {
      gsap.fromTo(el, { y: 26, autoAlpha: 0 }, {
        y: 0, autoAlpha: 1, duration: .6, ease: "power2.out",
        scrollTrigger: { trigger: el, start: "top 88%", once: true },
        onStart: function () { el.classList.add("is-in"); }
      });
    });
  }

  /* ---------------- 4. 3D tilt ---------------- */
  function initTilt() {
    if (REDUCED) return;
    $$(".tilt-card").forEach(function (card) {
      // Tilt the card itself; the .perspective lives on an ancestor via CSS,
      // but transforming in place still gives a convincing 3D feel.
      card.addEventListener("pointermove", function (e) {
        var r = card.getBoundingClientRect();
        var px = (e.clientX - r.left) / r.width - .5;
        var py = (e.clientY - r.top) / r.height - .5;
        card.style.transform = "perspective(900px) rotateX(" + (-py * 6) + "deg) rotateY(" + (px * 6) + "deg) translateZ(4px)";
      });
      card.addEventListener("pointerleave", function () { card.style.transform = ""; });
    });
  }

  /* ---------------- 5/10. Cart drawer + AJAX add-to-cart ---------------- */
  var drawer = document.getElementById("cart-drawer");
  var drawerBg = document.getElementById("cart-drawer-bg");

  function openDrawer(yes) {
    if (!drawer) return;
    drawer.classList.toggle("open", yes);
    drawer.setAttribute("aria-hidden", yes ? "false" : "true");
    if (drawerBg) drawerBg.classList.toggle("open", yes);
    document.body.style.overflow = yes ? "hidden" : "";
  }

  function renderDrawer(data) {
    if (!drawer) return;
    var list = document.getElementById("cart-drawer-items");
    if (list) {
      if (!data.items || !data.items.length) {
        list.innerHTML = '<p class="cart-drawer-empty">Your cart is empty.</p>';
      } else {
        list.innerHTML = data.items.map(function (it) {
          var img = it.image
            ? '<img src="' + escapeHtml(it.image) + '" alt="">'
            : '<span class="ph"></span>';
          var itemUrl = escapeHtml(it.url || '#');
          return (
            '<div class="cart-drawer-item" data-pid="' + it.pid + '">' +
            '<a href="' + itemUrl + '">' + img + '</a>' +
            '<div class="cdi-info">' +
              '<b>' + escapeHtml(it.name) + '</b>' +
              '<div class="cdi-actions">' +
                '<div class="cdi-qty">' +
                  '<button class="cdi-minus" type="button" data-pid="' + it.pid + '" data-qty="' + (it.qty - 1) + '" aria-label="Remove one">−</button>' +
                  '<span>' + it.qty + '</span>' +
                  '<button class="cdi-plus" type="button" data-pid="' + it.pid + '" data-qty="' + (it.qty + 1) + '" aria-label="Add one">+</button>' +
                '</div>' +
                '<span class="cdi-price">' + rs(it.line_total || (it.price * it.qty)) + '</span>' +
                '<button class="cdi-remove" type="button" data-pid="' + it.pid + '" aria-label="Remove from cart">&#x2715;</button>' +
              '</div>' +
            '</div>' +
            '</div>'
          );
        }).join("") +
        '<div class="cart-drawer-suggest"><a href="/shop/">Continue shopping &rarr;</a></div>';
      }
    }
    var totalEl = document.getElementById("cart-drawer-total");
    if (totalEl) totalEl.textContent = rs(data.total);
    var bar = document.getElementById("cart-free-bar");
    var note = document.getElementById("cart-free-note");
    if (bar) {
      var toFree = data.to_free_delivery || 0;
      if (toFree > 0) {
        var pct = data.subtotal / (data.subtotal + toFree) * 100;
        bar.style.width = Math.min(100, pct) + "%";
        if (note) note.textContent = "Add " + rs(toFree) + " more for free delivery";
      } else {
        bar.style.width = "100%";
        if (note) note.textContent = data.subtotal > 0 ? "You have free delivery!" : "";
      }
    }
  }

  function cartAjax(url, pid, qty) {
    var fd = new FormData();
    if (qty !== undefined) fd.append("qty", qty);
    fd.append("csrfmiddlewaretoken", csrf());
    fetch(url.replace("0", pid), {
      method: "POST",
      headers: { "Accept": "application/json", "X-Requested-With": "XMLHttpRequest" },
      body: fd
    }).then(function (r) { return r.json(); }).then(function (d) {
      updateBadges(d.cart_count);
      renderDrawer(d);
    }).catch(function () {});
  }

  function initDrawerItemControls() {
    var list = document.getElementById("cart-drawer-items");
    if (!list) return;
    list.addEventListener("click", function (e) {
      var minusBtn = e.target.closest ? e.target.closest(".cdi-minus") : null;
      var plusBtn  = e.target.closest ? e.target.closest(".cdi-plus")  : null;
      var removeBtn = e.target.closest ? e.target.closest(".cdi-remove") : null;
      if (minusBtn || plusBtn) {
        var btn = minusBtn || plusBtn;
        var pid = btn.dataset.pid;
        var qty = parseInt(btn.dataset.qty, 10);
        if (qty <= 0) {
          cartAjax("/cart/remove/0/".replace("0", pid), pid, undefined);
        } else {
          var fd = new FormData();
          fd.append("qty", qty);
          fd.append("csrfmiddlewaretoken", csrf());
          fetch("/cart/update/" + pid + "/", {
            method: "POST",
            headers: { "Accept": "application/json", "X-Requested-With": "XMLHttpRequest" },
            body: fd
          }).then(function (r) { return r.json(); }).then(function (d) {
            updateBadges(d.cart_count);
            renderDrawer(d);
          }).catch(function () {});
        }
      }
      if (removeBtn) {
        var pid2 = removeBtn.dataset.pid;
        var fd2 = new FormData();
        fd2.append("csrfmiddlewaretoken", csrf());
        fetch("/cart/remove/" + pid2 + "/", {
          method: "POST",
          headers: { "Accept": "application/json", "X-Requested-With": "XMLHttpRequest" },
          body: fd2
        }).then(function (r) { return r.json(); }).then(function (d) {
          updateBadges(d.cart_count);
          renderDrawer(d);
        }).catch(function () {});
      }
    });
  }

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  function bumpBadge() {
    $$(".badge-count").forEach(function (b) {
      b.classList.remove("pop"); void b.offsetWidth; b.classList.add("pop");
    });
  }

  function updateBadges(count) {
    $$(".badge-count").forEach(function (b) { b.textContent = count; });
    bumpBadge();
  }

  function initCartForms() {
    // Intercept product-card add-to-cart forms (marked data-ajax)
    document.addEventListener("submit", function (e) {
      var form = e.target;
      if (!form.matches || !form.matches("form[data-ajax]")) return;
      // let "buy now" fall through to a normal POST so we can redirect to checkout
      if (e.submitter && e.submitter.name === "buy_now") return;
      e.preventDefault();
      var fd = new FormData(form);
      fetch(form.action, {
        method: "POST",
        headers: { "X-Requested-With": "XMLHttpRequest", "Accept": "application/json", "X-CSRFToken": csrf() },
        body: fd
      }).then(function (r) { return r.json(); }).then(function (data) {
        if (!data || !data.ok) { form.submit(); return; }
        updateBadges(data.cart_count);
        renderDrawer(data);
        openDrawer(true);
      }).catch(function () { form.submit(); });
    });
  }

  function initDrawerControls() {
    if (!drawer) return;
    $$("[data-open-cart]").forEach(function (b) {
      b.addEventListener("click", function (e) { e.preventDefault(); openDrawer(true); });
    });
    $$("[data-close-cart]").forEach(function (b) {
      b.addEventListener("click", function () { openDrawer(false); });
    });
    if (drawerBg) drawerBg.addEventListener("click", function () { openDrawer(false); });
    document.addEventListener("keydown", function (e) { if (e.key === "Escape") openDrawer(false); });
  }

  /* ---------------- 6. Quick view modal ---------------- */
  var qv = document.getElementById("qv-modal");
  function openQuickView(slug) {
    if (!qv || !slug) return;
    var content = document.getElementById("qv-content");
    if (content) content.innerHTML = '<p style="padding:40px;text-align:center">Loading…</p>';
    qv.classList.add("open");
    qv.setAttribute("aria-hidden", "false");
    document.body.style.overflow = "hidden";
    fetch("/toy/" + encodeURIComponent(slug) + "/quickview/", {
      headers: { "X-Requested-With": "XMLHttpRequest" }
    }).then(function (r) { return r.text(); }).then(function (html) {
      if (content) content.innerHTML = html;
    }).catch(function () {
      if (content) content.innerHTML = '<p style="padding:40px;text-align:center">Could not load.</p>';
    });
  }
  function closeQuickView() {
    if (!qv) return;
    qv.classList.remove("open");
    qv.setAttribute("aria-hidden", "true");
    document.body.style.overflow = "";
  }
  function initQuickView() {
    document.addEventListener("click", function (e) {
      var b = e.target.closest ? e.target.closest(".quick-view-btn") : null;
      if (b) { e.preventDefault(); openQuickView(b.dataset.slug); }
      if (e.target.closest && e.target.closest("[data-close-qv]")) closeQuickView();
    });
    if (qv) qv.addEventListener("click", function (e) { if (e.target === qv) closeQuickView(); });
    document.addEventListener("keydown", function (e) { if (e.key === "Escape") closeQuickView(); });
  }

  /* ---------------- 7. Wishlist (localStorage hearts) ---------------- */
  function wlGet() {
    try { return JSON.parse(localStorage.getItem("lm_wishlist") || "[]"); }
    catch (e) { return []; }
  }
  function wlSet(arr) { localStorage.setItem("lm_wishlist", JSON.stringify(arr)); }
  function paintHearts() {
    var wl = wlGet();
    $$(".wishlist-btn").forEach(function (b) {
      var on = wl.indexOf(b.dataset.pid) !== -1;
      b.classList.toggle("active", on);
      b.textContent = on ? "♥" : "♡";
    });
  }
  function initWishlist() {
    paintHearts();
    document.addEventListener("click", function (e) {
      var b = e.target.closest ? e.target.closest(".wishlist-btn") : null;
      if (!b) return;
      e.preventDefault();
      var pid = b.dataset.pid, wl = wlGet(), i = wl.indexOf(pid);
      if (i === -1) wl.push(pid); else wl.splice(i, 1);
      wlSet(wl); paintHearts();
      // best-effort sync to the server session (ignore failures)
      fetch("/api/wishlist/" + pid + "/", {
        method: "POST", headers: { "X-CSRFToken": csrf(), "X-Requested-With": "XMLHttpRequest" }
      }).catch(function () {});
    });
  }

  /* ---------------- 8 + 12. Sale popup + confetti ---------------- */
  function confetti(root) {
    if (REDUCED) return;
    var colors = ["#3BA4E6", "#FF7272", "#3CCB9A", "#FFC93C", "#FFB7C5"];
    for (var i = 0; i < 40; i++) {
      (function (i) {
        var p = document.createElement("span");
        p.style.cssText = "position:absolute;top:-10px;width:9px;height:9px;border-radius:2px;pointer-events:none;z-index:5;" +
          "left:" + Math.random() * 100 + "%;background:" + colors[i % colors.length] + ";";
        root.appendChild(p);
        var fall = p.animate(
          [{ transform: "translateY(0) rotate(0)", opacity: 1 },
           { transform: "translateY(" + (260 + Math.random() * 160) + "px) rotate(" + (Math.random() * 540) + "deg)", opacity: 0 }],
          { duration: 1400 + Math.random() * 900, easing: "cubic-bezier(.2,.6,.3,1)" }
        );
        fall.onfinish = function () { p.remove(); };
      })(i);
    }
  }
  function initPopup() {
    var overlay = document.getElementById("sale-popup");
    if (!overlay) return;
    var key = "lm_popup_seen_" + (overlay.dataset.id || "x");
    var days = parseInt(overlay.dataset.days || "7", 10);
    var seen = parseFloat(localStorage.getItem(key) || "0");
    if (seen && (Date.now() - seen) < days * 86400000) return;
    var delay = parseInt(overlay.dataset.delay || "3", 10) * 1000;
    function close() {
      overlay.classList.remove("open");
      localStorage.setItem(key, String(Date.now()));
      document.body.style.overflow = "";
    }
    setTimeout(function () {
      overlay.classList.add("open");
      var box = overlay.querySelector(".popup-box");
      if (box) confetti(box);
    }, delay);
    $$("[data-close-popup]", overlay).forEach(function (b) { b.addEventListener("click", close); });
    overlay.addEventListener("click", function (e) { if (e.target === overlay) close(); });
    document.addEventListener("keydown", function (e) { if (e.key === "Escape") close(); });
  }

  /* ---------------- 9. Chatbot via /api/chat/ ---------------- */
  function initChatApi() {
    var bot = document.getElementById("mila-bot");
    if (!bot) return;
    var url = bot.getAttribute("data-chat-url");
    if (!url) return;                 // fall back to the inline TREE script
    bot.dataset.apiMode = "1";        // signal the inline script to stand down

    // The inline fallback script may already have bound listeners (it runs
    // before this deferred file). Clone the controls to strip those handlers.
    var toggle = document.getElementById("mila-toggle");
    var xbtn = document.getElementById("mila-x");
    if (toggle) { var tc = toggle.cloneNode(true); toggle.parentNode.replaceChild(tc, toggle); toggle = tc; }
    if (xbtn) { var xc = xbtn.cloneNode(true); xbtn.parentNode.replaceChild(xc, xbtn); xbtn = xc; }

    var win = document.getElementById("mila-window");
    var msgs = document.getElementById("mila-msgs");
    var opts = document.getElementById("mila-opts");
    if (!toggle || !msgs) return;

    function open(yes) {
      bot.classList.toggle("open", yes);
      toggle.setAttribute("aria-expanded", yes ? "true" : "false");
      if (win) win.setAttribute("aria-hidden", yes ? "false" : "true");
      if (yes && !msgs.children.length) {
        bubble("Hi, I'm Mila! How can I help you find the right toy today?", "bot");
      }
    }
    function bubble(text, who) {
      var d = document.createElement("div");
      d.className = who === "me" ? "mila-msg me" : "mila-msg";
      d.textContent = text;
      msgs.appendChild(d);
      msgs.scrollTop = msgs.scrollHeight;
      return d;
    }
    function send(text) {
      bubble(text, "me");
      var typing = document.createElement("div");
      typing.className = "mila-typing";
      typing.innerHTML = "<span></span><span></span><span></span>";
      msgs.appendChild(typing); msgs.scrollTop = msgs.scrollHeight;
      fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRFToken": csrf() },
        body: JSON.stringify({ message: text })
      }).then(function (r) { return r.json(); }).then(function (data) {
        typing.remove();
        bubble(data.answer || "Sorry, please try again.", "bot");
      }).catch(function () {
        typing.remove();
        bubble("Sorry, I couldn't reach the server. Please try WhatsApp.", "bot");
      });
    }
    if (opts) {
      opts.innerHTML = "";
      var row = document.createElement("form");
      row.className = "mila-input";
      row.innerHTML = '<input type="text" placeholder="Type your question…" aria-label="Your message">' +
        '<button type="submit" aria-label="Send">→</button>';
      opts.appendChild(row);
      row.addEventListener("submit", function (e) {
        e.preventDefault();
        var inp = row.querySelector("input");
        var v = (inp.value || "").trim();
        if (v) { send(v); inp.value = ""; }
      });
    }
    toggle.addEventListener("click", function () { open(!bot.classList.contains("open")); });
    if (xbtn) xbtn.addEventListener("click", function () { open(false); });
  }

  /* ---------------- 11. Search suggestions ---------------- */
  function initSearchSuggest() {
    var input = document.getElementById("q");
    var form = input && input.closest("form");
    if (!input || !form) return;
    var box = document.createElement("div");
    box.className = "search-suggest";
    box.setAttribute("role", "listbox");
    form.appendChild(box);
    var t = null;
    function hide() { box.classList.remove("open"); box.innerHTML = ""; }
    input.addEventListener("input", function () {
      var q = input.value.trim();
      clearTimeout(t);
      if (q.length < 2) { hide(); return; }
      t = setTimeout(function () {
        fetch("/api/search/?q=" + encodeURIComponent(q))
          .then(function (r) { return r.json(); })
          .then(function (data) {
            if (!data.results || !data.results.length) { hide(); return; }
            box.innerHTML = data.results.map(function (p) {
              var img = p.image ? '<img src="' + p.image + '" alt="">' : '<span class="ph"></span>';
              return '<a href="' + p.url + '">' + img +
                '<span><b>' + escapeHtml(p.name) + '</b><small>' + escapeHtml(p.category) + '</small></span>' +
                '<span class="ss-price">' + rs(p.price) + '</span></a>';
            }).join("");
            box.classList.add("open");
          }).catch(hide);
      }, 300);
    });
    document.addEventListener("click", function (e) {
      if (!form.contains(e.target)) hide();
    });
  }

  /* ---------------- 13. Bottom-nav active state ---------------- */
  function initBottomNav() {
    var path = location.pathname;
    $$(".bottom-nav a").forEach(function (a) {
      var href = a.getAttribute("href");
      if (href && href !== "/" && path.indexOf(href) === 0) a.setAttribute("aria-current", "page");
      if (href === "/" && path === "/") a.setAttribute("aria-current", "page");
    });
  }

  /* ---------------- 14. Recently viewed (localStorage) ---------------- */
  function initRecentlyViewed() {
    var slug = document.body.getAttribute("data-product-slug");
    if (slug) {
      var seen = [];
      try { seen = JSON.parse(localStorage.getItem("lm_recent") || "[]"); } catch (e) {}
      seen = seen.filter(function (s) { return s !== slug; });
      seen.unshift(slug);
      localStorage.setItem("lm_recent", JSON.stringify(seen.slice(0, 8)));
    }
  }

  /* ---------------- init ---------------- */
  function boot() {
    document.documentElement.classList.remove("js-off");
    initSwipers();
    initReveals();
    initTilt();
    initCartForms();
    initDrawerControls();
    initDrawerItemControls();
    initQuickView();
    initWishlist();
    initPopup();
    initChatApi();
    initSearchSuggest();
    initBottomNav();
    initRecentlyViewed();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
