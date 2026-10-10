(function () {
  'use strict';

  var LIMITS = {
    image:    10 * 1024 * 1024,
    video:    50 * 1024 * 1024,
    document: 10 * 1024 * 1024,
  };
  var ACCEPT_IMAGE = ['image/jpeg','image/png','image/webp','image/gif','image/avif'];
  var ACCEPT_VIDEO = ['video/mp4','video/webm','video/quicktime'];

  function fmtSize(b) {
    if (b < 1024) return b + ' B';
    if (b < 1024*1024) return (b/1024).toFixed(1) + ' KB';
    return (b/1024/1024).toFixed(1) + ' MB';
  }

  function initZone(wrapper) {
    var input = wrapper.querySelector('input[type="file"]');
    if (!input) return;
    var kind = wrapper.dataset.kind || 'image';
    var currentUrl = wrapper.dataset.currentUrl || '';
    var previewArea = wrapper.querySelector('.dz-preview-area');

    // Show existing file preview
    if (currentUrl) {
      var prev = document.createElement('div');
      prev.className = 'dz-preview';
      if (kind === 'image') {
        var img = document.createElement('img');
        img.className = 'dz-thumb';
        img.src = currentUrl;
        img.alt = 'Current';
        img.onerror = function () {
          img.style.display = 'none';
          var miss = document.createElement('div');
          miss.className = 'dz-missing';
          miss.textContent = 'File missing — upload again';
          prev.insertBefore(miss, prev.firstChild);
        };
        prev.appendChild(img);
      }
      var info = document.createElement('div');
      info.className = 'dz-info';
      info.innerHTML = '<b>Current file</b><small>Replace by choosing a new file</small>';
      prev.appendChild(info);
      previewArea.appendChild(prev);
    }

    function showError(msg) {
      var old = wrapper.querySelector('.dz-error');
      if (old) old.remove();
      var el = document.createElement('div');
      el.className = 'dz-error'; el.textContent = msg;
      wrapper.appendChild(el);
    }

    function clearError() { var e = wrapper.querySelector('.dz-error'); if (e) e.remove(); }

    function handleFile(file) {
      clearError();
      // Client-side type check
      var isImg = ACCEPT_IMAGE.indexOf(file.type) !== -1;
      var isVid = ACCEPT_VIDEO.indexOf(file.type) !== -1;
      if (kind === 'image' && !isImg) {
        showError('Please choose an image file (jpg, png, webp, gif).');
        input.value = ''; return;
      }
      if (kind === 'video' && !isVid) {
        showError('Please choose a video file (mp4, webm, mov).');
        input.value = ''; return;
      }
      if (LIMITS[kind] && file.size > LIMITS[kind]) {
        showError('File is ' + fmtSize(file.size) + ' — maximum is ' + fmtSize(LIMITS[kind]) + '.');
        input.value = ''; return;
      }
      // Clear old preview
      previewArea.innerHTML = '';
      var prev = document.createElement('div');
      prev.className = 'dz-preview';
      if (kind === 'image' && file.type.startsWith('image/')) {
        var thumb = document.createElement('img');
        thumb.className = 'dz-thumb';
        thumb.src = URL.createObjectURL(file);
        thumb.alt = '';
        prev.appendChild(thumb);
      }
      var info = document.createElement('div');
      info.className = 'dz-info';
      info.innerHTML = '<b>' + file.name + '</b><small>' + fmtSize(file.size) + '</small>';
      prev.appendChild(info);
      var rm = document.createElement('button');
      rm.type = 'button'; rm.className = 'dz-remove'; rm.innerHTML = '&#x2715;';
      rm.onclick = function () { input.value = ''; previewArea.innerHTML = ''; clearError(); };
      prev.appendChild(rm);
      previewArea.appendChild(prev);
    }

    input.addEventListener('change', function () {
      if (input.files[0]) handleFile(input.files[0]);
    });

    wrapper.addEventListener('dragover', function (e) {
      e.preventDefault(); wrapper.classList.add('drag-over');
    });
    wrapper.addEventListener('dragleave', function () { wrapper.classList.remove('drag-over'); });
    wrapper.addEventListener('drop', function (e) {
      e.preventDefault(); wrapper.classList.remove('drag-over');
      var f = e.dataTransfer.files[0];
      if (f) { input.files = e.dataTransfer.files; handleFile(f); }
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    // Init explicitly marked drop zones
    document.querySelectorAll('.lm-drop-zone').forEach(initZone);

    // Auto-wrap all file inputs in admin forms
    document.querySelectorAll('input[type="file"]').forEach(function(input) {
      // Skip already-wrapped inputs
      if (input.closest('.lm-drop-zone')) return;

      var wrapper = document.createElement('div');
      wrapper.className = 'lm-drop-zone';
      wrapper.dataset.kind = (input.accept && input.accept.indexOf('video') !== -1) ? 'video' : 'image';
      var previewArea = document.createElement('div');
      previewArea.className = 'dz-preview-area';
      var label = document.createElement('div');
      label.className = 'dz-label';
      label.innerHTML = '<b>Drag &amp; drop</b> or <b>click to browse</b>';

      // Check for existing image preview rendered by Unfold above the input
      var fieldBox = input.closest('.field-box, .form-row, .fieldBox, [class*="field-"]');
      if (fieldBox) {
        var existingImg = fieldBox.querySelector('a[href] img, .readonly img');
        if (existingImg && existingImg.src) {
          wrapper.dataset.currentUrl = existingImg.src;
        }
      }

      input.parentNode.insertBefore(wrapper, input);
      wrapper.appendChild(input);
      wrapper.appendChild(label);
      wrapper.appendChild(previewArea);
      initZone(wrapper);
    });
  });
})();
