/**
 * LittleMove admin drag-and-drop upload widget.
 *
 * Works with both:
 *   (a) Plain file inputs (wrapped with a visible drop zone card)
 *   (b) Unfold's clearable_file_input widget (which hides the <input> inside
 *       opacity-0 / w-[0px] divs — we inject a preview card alongside it)
 *
 * Also handles Django inline formset:added events so new inline rows get zones.
 */
(function () {
  'use strict';

  var LIMITS = {
    image:    10 * 1024 * 1024,   // 10 MB
    video:    50 * 1024 * 1024,   // 50 MB
    document: 10 * 1024 * 1024,  // 10 MB
  };
  var ACCEPT_IMAGE = ['image/jpeg','image/png','image/webp','image/gif','image/avif'];
  var ACCEPT_VIDEO = ['video/mp4','video/webm','video/quicktime'];

  function fmtSize(b) {
    if (b < 1024)       return b + ' B';
    if (b < 1024*1024)  return (b / 1024).toFixed(1) + ' KB';
    return (b / 1024 / 1024).toFixed(1) + ' MB';
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
      // Look for the outer Unfold file widget wrapper: it is a sibling container
      // that holds both the text-input display and the hidden file input
      if (el.children && el.children.length >= 2) {
        // Check if it contains the text "Choose file to upload" placeholder
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
      // Unfold renders a <div class="mb-4 max-w-48"><a href="..."><img src="..."></a></div>
      // as the previous sibling of the widget wrapper
      var prev = el.previousElementSibling;
      if (prev) {
        var img = prev.querySelector('img');
        if (img && img.src) return img.src;
      }
      // Also check field-level containers
      var img2 = el.querySelector('a[href] img:not([class*="brand"])');
      if (img2 && img2.src && img2.src.indexOf('data:') === -1) return img2.src;
    }
    return null;
  }

  /* ── build and attach a drop-zone card ──────────────────────────────── */
  function attachZone(input) {
    // Skip if already zoned
    if (input.dataset.dzInited) return;
    input.dataset.dzInited = '1';

    var kind = (input.accept && input.accept.indexOf('video') !== -1) ? 'video' : 'image';
    var currentUrl = findUnfoldPreviewUrl(input) || '';

    /* --- create the card --- */
    var card = document.createElement('div');
    card.className = 'lm-dz-card';

    var previewArea = document.createElement('div');
    previewArea.className = 'lm-dz-preview';

    // Existing file preview
    if (currentUrl && kind === 'image') {
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
    dropHint.innerHTML = '<span class="material-symbols-outlined" aria-hidden="true">upload</span>'
      + ' <b>Drag &amp; drop</b> or <b>click to browse</b><br>'
      + '<small>' + (kind === 'image' ? 'jpg, png, webp, gif — max 10 MB' : 'mp4, webm, mov — max 50 MB') + '</small>';

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
    function clearError() {
      errorDiv.style.display = 'none';
    }

    /* --- handle a picked file --- */
    function handleFile(file) {
      clearError();
      var isImg = ACCEPT_IMAGE.indexOf(file.type) !== -1;
      var isVid = ACCEPT_VIDEO.indexOf(file.type) !== -1;
      if (kind === 'image' && !isImg) {
        showError('Please choose an image file (jpg, png, webp, gif, avif).');
        input.value = ''; return;
      }
      if (kind === 'video' && !isVid) {
        showError('Please choose a video file (mp4, webm, mov).');
        input.value = ''; return;
      }
      var limit = LIMITS[kind] || LIMITS.image;
      if (file.size > limit) {
        showError('File is ' + fmtSize(file.size) + ' — maximum allowed is ' + fmtSize(limit) + '.');
        input.value = ''; return;
      }

      // Build new-file preview
      newPrev.innerHTML = '';
      if (kind === 'image' && file.type.startsWith('image/')) {
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

    /* --- wire drag events on the card --- */
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
      // Transfer files to the real input
      try {
        var dt = new DataTransfer();
        dt.items.add(f);
        input.files = dt.files;
      } catch (err) { /* Safari fallback: click is not needed since handleFile is called */ }
      handleFile(f);
    });

    /* --- click on card opens file picker --- */
    card.addEventListener('click', function (e) {
      if (e.target === rm || e.target.classList.contains('lm-dz-remove')) return;
      input.click();
    });
    card.style.cursor = 'pointer';

    /* --- wire the file input change --- */
    input.addEventListener('change', function () {
      if (input.files && input.files[0]) {
        handleFile(input.files[0]);
      }
    });

    /* --- inject the card --- */
    // For Unfold inputs: inject after the widget's outer container
    if (isUnfoldHidden(input)) {
      var container = findUnfoldContainer(input);
      if (container && container.parentNode) {
        container.parentNode.insertBefore(card, container.nextSibling);
        return;
      }
    }
    // For plain file inputs: inject just before the input
    input.parentNode.insertBefore(card, input);
  }

  /* ── init all file inputs in a given root element ────────────────────── */
  function initAll(root) {
    var inputs = (root || document).querySelectorAll('input[type="file"]');
    inputs.forEach(function (inp) {
      attachZone(inp);
    });
  }

  /* ── on DOM ready ──────────────────────────────────────────────────────── */
  document.addEventListener('DOMContentLoaded', function () {
    initAll(document);

    // Re-init when Django adds a new inline formset row
    document.addEventListener('formset:added', function (e) {
      var row = e.target || e.detail && e.detail.row;
      if (row) initAll(row);
    });
  });
})();
