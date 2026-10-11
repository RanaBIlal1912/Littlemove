/* LittleMove admin language pill */
(function () {
  'use strict';

  function setCookie(name, value, days) {
    var exp = days ? ';max-age=' + (days * 86400) : '';
    document.cookie = name + '=' + value + ';path=/' + exp + ';samesite=Lax';
    document.cookie = name + '=' + value + ';path=/;domain=' + location.hostname + exp + ';samesite=Lax';
  }
  function delCookie(name) {
    document.cookie = name + '=;path=/;max-age=0';
    document.cookie = name + '=;path=/;max-age=0;domain=' + location.hostname;
  }

  function lmLangChange(code) {
    if (!code) return;
    if (code === '__reset__') {
      delCookie('lm_gt_lang');
      delCookie('googtrans');
      setCookie('django_language', 'en', 365);
      location.reload();
      return;
    }
    setCookie('googtrans', '/en/' + code, 0);
    setCookie('lm_gt_lang', code, 365);
    setCookie('django_language', 'en', 365);
    location.reload();
  }

  function closeAll() {
    document.querySelectorAll('.lm-admin-lang-menu').forEach(function (m) {
      m.hidden = true;
      var btn = m.previousElementSibling;
      if (btn) btn.setAttribute('aria-expanded', 'false');
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    var btn = document.getElementById('lm-admin-lang-btn');
    var menu = document.getElementById('lm-admin-lang-menu');
    if (!btn || !menu) return;

    btn.addEventListener('click', function (e) {
      e.stopPropagation();
      var open = !menu.hidden;
      closeAll();
      if (!open) {
        menu.hidden = false;
        btn.setAttribute('aria-expanded', 'true');
      }
    });

    menu.addEventListener('click', function (e) {
      var opt = e.target.closest('[data-code]');
      if (!opt) return;
      lmLangChange(opt.dataset.code);
    });

    document.addEventListener('click', function (e) {
      if (!document.getElementById('lm-admin-lang-wrap').contains(e.target)) {
        closeAll();
      }
    });

    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') closeAll();
    });
  });
})();
