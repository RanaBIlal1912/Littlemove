/**
 * LittleMove admin drag-and-drop upload widget.
 *
 * Type-aware: reads input.accept (or data-dz-accept override) to pick the
 * right zone kind — image, zip, or spreadsheet. Inputs with data-no-dropzone
 * or an unrecognised accept value are skipped entirely (native input shown).
 *
 * Works with both:
 *   (a) Plain file inputs (wrapped with a visible drop zone card)
 *   (b) Unfold's clearable_file_input widget (which hides the <input> inside
 *       opacity-0 / w-[0px] divs — we inject a preview card alongside it)
 *
 * Also handles Django inline formset:added events so new inline rows get zones.
 * Wraps mount logic in try/catch — if anything fails the native input is restored.
 */
(function () {
  'use strict';

  var ACCEPT_IMAGE = ['image/jpeg', 'image/png', 'image/webp', 'image/gif', 'image/avif'];
  var ACCEPT_VIDEO = ['video/mp4', 'video/webm', 'video/quicktime'];
  var ACCEPT_ZIP   = ['application/zip', 'application/x-zip-compressed', 'application/x-zip',
                      'application/octet-stream'];
  var ACCEPT_SHEET = [
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.ms-excel', 'text/csv', 'application/csv', 'text/plain',
  ];

  function fmtSize(b) {
    if (b < 1024)        return b + ' B';
    if (b < 1024 * 1024) return (b / 1024).toFixed(1) + ' KB';
    return (b / 1024 / 1024).toFixed(1) + ' MB';
  }

  /* ── resolve zone config from accept attribute + data-dz-* overrides ────── */
  function getZoneConfig(input) {
    if (input.dataset.noDz !== undefined || input.dataset.noDropzone !== undefined) {
      return null;
    }

    var rawAccept   = (input.dataset.dzAccept || input.accept || '').toLowerCase();
    var maxMb       = parseFloat(input.dataset.dzMaxMb) || null;
    var customLabel = input.dataset.dzLabel || null;

    // ZIP
    if (rawAccept.indexOf('.zip') !== -1) {
      var mb = maxMb || 60;
      return {
        kind: 'zip',
        mimeList: ACCEPT_ZIP,
        extList: ['.zip'],
        maxBytes: mb * 1024 * 1024,
        hintHtml: customLabel
          ? ('<b>' + customLabel + '</b>')
          : '<b>Drag &amp; drop</b> or <b>click to browse</b><br><small>.zip — max ' + mb + ' MB</small>',
      };
    }

    // Spreadsheet
    if (rawAccept.indexOf('.xlsx') !== -1 || rawAccept.indexOf('.csv') !== -1) {
      var mb = maxMb || 10;
      return {
        kind: 'spreadsheet',
        mimeList: ACCEPT_SHEET,
        extList: ['.xlsx', '.csv'],
        maxBytes: mb * 1024 * 1024,
        hintHtml: customLabel
          ? ('<b>' + customLabel + '</b>')
          : '<b>Drag &amp; drop</b> or <b>click to browse</b><br><small>.xlsx, .csv — max ' + mb + ' MB</small>',
      };
    }

    // Video
    if (rawAccept.indexOf('video') !== -1) {
      var mb = maxMb || 50;
      return {
        kind: 'video',
        mimeList: ACCEPT_VIDEO,
        extList: ['.mp4', '.webm', '.mov'],
        maxBytes: mb * 1024 * 1024,
        hintHtml: customLabel
          ? ('<b>' + customLabel + '</b>')
          : '<b>Drag &amp; drop</b> or <b>click to browse</b><br><small>mp4, webm, mov — max ' + mb + ' MB</small>',
      };
    }

    // Image (explicit accept only — never default for empty accept)
    if (rawAccept.indexOf('image') !== -1 ||
        /\.(jpg|jpeg|png|webp|gif|avif)/.test(rawAccept)) {
      var mb = maxMb || 10;
      return {
        kind: 'image',
        mimeList: ACCEPT_IMAGE,
        extList: ['.jpg', '.jpeg', '.png', '.webp', '.gif', '.avif'],
        maxBytes: mb * 1024 * 1024,
        hintHtml: customLabel
          ? ('<b>' + customLabel + '</b>')
          : '<b>Drag &amp; drop</b> or <b>click to browse</b><br><small>jpg, png, webp, gif — max ' + mb + ' MB</small>',
      };
    }

    // Unknown or empty accept — skip; leave native input untouched
    return null;
  }

  /* ── check whether a dropped/selected file matches the zone's accept list ─ */
  function fileMatchesConfig(file, config) {
    // MIME type check (primary)
    if (file.type && config.mimeList.indexOf(file.type) !== -1) return true;
    // Extension fallback (CSV MIME is browser-inconsistent; also for drag-and-drop)
    var name = (file.name || '').toLowerCase();
    for (var i = 0; i < config.extList.length; i++) {
      if (name.endsWith(config.extList[i])) return true;
    }
    return false;
  }

  /* ── determine whether an input is inside Unfold's hidden wrapper ─────── */
  function isUnfoldHidden(input) {
    var p = input.parentNode;
    return p && (
      p.style.overflow === 'hidden' ||
      (p.className && (
        p.className.indexOf('opacity-0') !== -1 ||
        p.className.indexOf('overflow-hidden') !== -1 ||
        p.className.indexOf('w-[0px]') !== -1 ||
        p.style.width === '0px'
      ))
    );
  }

  /* ── find the Unfold widget container (outer div with file wrapper class) */
  function findUnfoldContainer(input) {
    var el = input;
    for (var i = 0; i < 8; i++) {
      el = el.parentNode;
      if (!el || el === document.body) return null;
      if (el.children && el.children.length >= 2) {
        var txt = el.querySelector('input[type="text"][disabled]');
        if (txt) return el;
      }
    }
    return null;
  }

  /* ── look for an existing Unfold image preview near this input ─────────── */
  function findUnfoldPreviewUrl(input) {
    var el = input;
    for (var i = 0; i < 10; i++) {
      el = el.parentNode;
      if (!el || el === document.body) return null;
      var prev = el.previousElementSibling;
      if (prev) {
        var img = prev.querySelector('img');
        if (img && img.src) return img.src;
      }
      var img2 = el.querySelector('a[href] img:not([class*="brand"])');
      if (img2 && img2.src && img2.src.indexOf('data:') === -1) return img2.src;
    }
    return null;
  }

  /* ── core mount logic (wrapped in try/catch by attachZone) ──────────────── */
  function _attachZone(input) {
    if (input.dataset.dzInited) return;

    var config = getZoneConfig(input);
    if (!config) return; // Unknown type or data-no-dropzone — native input stays

    input.dataset.dzInited = '1';

    // Only image zones can show an existing file preview
    var currentUrl = (config.kind === 'image') ? (findUnfoldPreviewUrl(input) || '') : '';

    /* --- build the card --- */
    var card = document.createElement('div');
    card.className = 'lm-dz-card';

    var previewArea = document.createElement('div');
    previewArea.className = 'lm-dz-preview';

    // Existing image preview (ImageField with stored file only)
    if (currentUrl && config.kind === 'image') {
      var curPrev = document.createElement('div');
      curPrev.className = 'lm-dz-thumb-wrap';
      var curImg = document.createElement('img');
      curImg.className = 'lm-dz-thumb';
      curImg.src = currentUrl;
      curImg.alt = 'Current';
      curImg.onerror = function () {
        curImg.style.display = 'none';
        var miss = document.createElement('div');
        miss.className = 'lm-dz-missing';
        miss.textContent = '⚠ File missing — upload again';
        curPrev.appendChild(miss);
      };
      curPrev.appendChild(curImg);
      var curInfo = document.createElement('div');
      curInfo.className = 'lm-dz-info';
      curInfo.innerHTML = '<b>Current image</b><small>Replace by choosing a new file below</small>';
      curPrev.appendChild(curInfo);
      previewArea.appendChild(curPrev);
    }

    var dropHint = document.createElement('div');
    dropHint.className = 'lm-dz-hint';
    dropHint.innerHTML =
      '<span class="material-symbols-outlined" aria-hidden="true">upload</span> ' +
      config.hintHtml;

    var errorDiv = document.createElement('div');
    errorDiv.className = 'lm-dz-error';
    errorDiv.style.display = 'none';

    var newPrev = document.createElement('div');
    newPrev.className = 'lm-dz-new-preview';
    newPrev.style.display = 'none';

    card.appendChild(previewArea);
    card.appendChild(dropHint);
    card.appendChild(errorDiv);
    card.appendChild(newPrev);

    /* --- error helpers --- */
    function showError(msg) {
      errorDiv.textContent = msg;
      errorDiv.style.display = 'block';
      newPrev.style.display = 'none';
    }
    function clearError() { errorDiv.style.display = 'none'; }

    /* --- handle a picked / dropped file --- */
    function handleFile(file) {
      clearError();
      if (!fileMatchesConfig(file, config)) {
        if (config.kind === 'image') {
          showError('Please choose an image file (jpg, png, webp, gif, avif).');
        } else if (config.kind === 'zip') {
          showError('Please choose a ZIP file (.zip).');
        } else if (config.kind === 'spreadsheet') {
          showError('Please choose an Excel or CSV file (.xlsx, .csv).');
        } else {
          showError('File type not accepted.');
        }
        input.value = '';
        return;
      }
      if (file.size > config.maxBytes) {
        showError('File is ' + fmtSize(file.size) + ' — maximum allowed is ' + fmtSize(config.maxBytes) + '.');
        input.value = '';
        return;
      }

      newPrev.innerHTML = '';
      // Image thumbnail only for image zones
      if (config.kind === 'image' && file.type && file.type.startsWith('image/')) {
        var thumb = document.createElement('img');
        thumb.className = 'lm-dz-thumb';
        thumb.src = URL.createObjectURL(file);
        thumb.alt = '';
        newPrev.appendChild(thumb);
      }
      var info = document.createElement('div');
      info.className = 'lm-dz-info';
      info.innerHTML = '<b>' + file.name + '</b><small>' + fmtSize(file.size) + '</small>';
      var rm = document.createElement('button');
      rm.type = 'button'; rm.className = 'lm-dz-remove'; rm.innerHTML = '&#x2715;';
      rm.title = 'Remove';
      rm.onclick = function () {
        input.value = '';
        newPrev.style.display = 'none';
        newPrev.innerHTML = '';
        clearError();
      };
      newPrev.appendChild(info);
      newPrev.appendChild(rm);
      newPrev.style.display = 'flex';
      dropHint.style.display = 'none';
    }

    /* --- drag events --- */
    card.addEventListener('dragover', function (e) {
      e.preventDefault();
      card.classList.add('lm-dz-over');
    });
    card.addEventListener('dragleave', function () {
      card.classList.remove('lm-dz-over');
    });
    card.addEventListener('drop', function (e) {
      e.preventDefault();
      card.classList.remove('lm-dz-over');
      var f = e.dataTransfer.files[0];
      if (!f) return;
      try {
        var dt = new DataTransfer();
        dt.items.add(f);
        input.files = dt.files;
      } catch (err) { /* Safari fallback */ }
      handleFile(f);
    });

    /* --- click on card opens file picker --- */
    card.addEventListener('click', function (e) {
      if (e.target && e.target.classList && e.target.classList.contains('lm-dz-remove')) return;
      input.click();
    });
    card.style.cursor = 'pointer';

    /* --- wire native input change event --- */
    input.addEventListener('change', function () {
      if (input.files && input.files[0]) handleFile(input.files[0]);
    });

    /* --- inject the card --- */
    if (isUnfoldHidden(input)) {
      var container = findUnfoldContainer(input);
      if (container && container.parentNode) {
        // Inject after the Unfold container, then hide the native bar
        container.parentNode.insertBefore(card, container.nextSibling);
        container.style.display = 'none';

        // Also hide the Unfold image-preview thumbnail sibling
        var prevSib = container.previousElementSibling;
        if (prevSib && prevSib.querySelector && prevSib.querySelector('img')) {
          prevSib.style.display = 'none';
        }

        // Proxy the "Clear" checkbox if present (keeps form submission working)
        var origCheck = container.querySelector('input[type="checkbox"]');
        if (origCheck) {
          var clearWrap = document.createElement('label');
          clearWrap.className = 'lm-dz-clear-label';
          clearWrap.style.cssText = 'display:flex;align-items:center;gap:6px;font-size:.8125rem;cursor:pointer;padding:4px 0;';
          var proxyCheck = document.createElement('input');
          proxyCheck.type = 'checkbox';
          proxyCheck.checked = origCheck.checked;
          proxyCheck.addEventListener('change', function () { origCheck.checked = proxyCheck.checked; });
          origCheck.addEventListener('change', function () { proxyCheck.checked = origCheck.checked; });
          var clearLabel = document.createElement('span');
          clearLabel.textContent = 'Clear existing file';
          clearWrap.appendChild(proxyCheck);
          clearWrap.appendChild(clearLabel);
          card.insertBefore(clearWrap, card.firstChild);
        }
        return;
      }
    }

    // Plain file input: inject the card before the input, then visually hide it.
    // The zone's click handler calls input.click() so the picker still works.
    input.parentNode.insertBefore(card, input);
    input.style.position = 'absolute';
    input.style.width = '1px';
    input.style.height = '1px';
    input.style.overflow = 'hidden';
    input.style.clip = 'rect(0,0,0,0)';
    input.style.whiteSpace = 'nowrap';
  }

  /* ── public mount with fallback ──────────────────────────────────────────── */
  function attachZone(input) {
    try {
      _attachZone(input);
    } catch (e) {
      // Mounting failed — restore native input so the user can still upload
      input.style.cssText = '';
      input.dataset.dzInited = '';
    }
  }

  /* ── init all file inputs in a given root element ────────────────────── */
  function initAll(root) {
    var inputs = (root || document).querySelectorAll('input[type="file"]');
    inputs.forEach(function (inp) { attachZone(inp); });
  }

  /* ── on DOM ready ──────────────────────────────────────────────────────── */
  document.addEventListener('DOMContentLoaded', function () {
    initAll(document);

    // Re-init when Django adds a new inline formset row
    document.addEventListener('formset:added', function (e) {
      var row = e.target || (e.detail && e.detail.row);
      if (row) initAll(row);
    });
  });
})();
