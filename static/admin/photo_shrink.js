/**
 * LittleMove admin photo shrinker.
 * Loaded on bulk-upload and bulk-import pages (not global admin).
 * Requires: static/vendor/jszip-3.10.1.min.js loaded BEFORE this file.
 */
(function () {
  'use strict';

  var MAX_LONG_SIDE  = 1200;
  var JPEG_QUALITY   = 0.85;
  var WARN_BYTES     = 55 * 1024 * 1024;   // 55 MB — warn / split
  var PART_BYTES     = 40 * 1024 * 1024;   // 40 MB per part
  var IMAGE_RE       = /\.(jpe?g|png|webp|gif|bmp|tiff?)$/i;
  var IMAGE_MIMES    = ['image/jpeg','image/png','image/webp','image/gif','image/bmp','image/tiff'];

  function isImagePath(p) { return IMAGE_RE.test(p); }
  function isImageMime(t) { return IMAGE_MIMES.indexOf(t) !== -1; }

  /* --- convert canvas to blob as a Promise --- */
  function canvasToBlob(canvas, type, quality) {
    return new Promise(function (resolve) {
      canvas.toBlob(resolve, type, quality);
    });
  }

  /* --- check whether a PNG blob contains any transparent pixels (sample 100×100) --- */
  async function pngHasAlpha(blob) {
    var bmp;
    try { bmp = await createImageBitmap(blob); } catch (e) { return true; }
    var w = Math.min(bmp.width, 100), h = Math.min(bmp.height, 100);
    var c = document.createElement('canvas'); c.width = w; c.height = h;
    var ctx = c.getContext('2d'); ctx.drawImage(bmp, 0, 0, w, h);
    if (bmp.close) bmp.close();
    var data = ctx.getImageData(0, 0, w, h).data;
    for (var i = 3; i < data.length; i += 4) { if (data[i] < 255) return true; }
    return false;
  }

  /* --- shrink one image blob, returning {blob, newPath, changed} --- */
  async function shrinkOne(blob, originalPath) {
    var isPng = /\.png$/i.test(originalPath);
    var isJpeg = /\.jpe?g$/i.test(originalPath);

    // For PNG: check alpha so we don't lose transparency
    var hasAlpha = false;
    if (isPng && blob.type !== 'image/jpeg') {
      try { hasAlpha = await pngHasAlpha(blob); } catch (e) { hasAlpha = true; }
    }

    var outputType = (isJpeg || !hasAlpha) ? 'image/jpeg' : 'image/png';

    var bmp;
    try {
      bmp = await createImageBitmap(blob, { imageOrientation: 'from-image' });
    } catch (e) {
      try { bmp = await createImageBitmap(blob); } catch (e2) { return { blob: blob, newPath: originalPath, changed: false }; }
    }

    var w = bmp.width, h = bmp.height;
    var longSide = Math.max(w, h);
    var scale = longSide > MAX_LONG_SIDE ? MAX_LONG_SIDE / longSide : 1;
    var tw = Math.round(w * scale), th = Math.round(h * scale);

    // Skip re-encoding if already JPEG, correct size, no conversion needed
    if (scale === 1 && isJpeg) {
      if (bmp.close) bmp.close();
      return { blob: blob, newPath: originalPath, changed: false };
    }

    var canvas = document.createElement('canvas');
    canvas.width = tw; canvas.height = th;
    canvas.getContext('2d').drawImage(bmp, 0, 0, tw, th);
    if (bmp.close) bmp.close();

    var quality = outputType === 'image/jpeg' ? JPEG_QUALITY : undefined;
    var outBlob = await canvasToBlob(canvas, outputType, quality);

    // New path: change extension if needed
    var newPath = originalPath;
    if (outputType === 'image/jpeg' && !/\.jpe?g$/i.test(originalPath)) {
      newPath = originalPath.replace(/\.[^./]+$/, '.jpg');
    }

    return { blob: outBlob, newPath: newPath, changed: true };
  }

  /* --- process a list of {path, blob} entries, return {entries, renamedMap, originalBytes, shrunkBytes} --- */
  async function shrinkAll(entries, onProgress) {
    var out = [], originalBytes = 0, shrunkBytes = 0;
    var renamedMap = {}; // oldPath -> newPath

    for (var i = 0; i < entries.length; i++) {
      onProgress(i + 1, entries.length);
      var e = entries[i];
      originalBytes += e.blob.size;
      var result = await shrinkOne(e.blob, e.path);
      shrunkBytes += result.blob.size;
      if (result.newPath !== e.path) renamedMap[e.path] = result.newPath;
      out.push({ path: result.newPath, blob: result.blob });
    }
    return { entries: out, renamedMap: renamedMap, originalBytes: originalBytes, shrunkBytes: shrunkBytes };
  }

  /* --- build a ZIP blob from an array of {path, blob} entries using JSZip --- */
  async function buildZip(entries) {
    var zip = new window.JSZip();
    for (var i = 0; i < entries.length; i++) {
      zip.file(entries[i].path, entries[i].blob);
    }
    return zip.generateAsync({ type: 'blob', compression: 'DEFLATE', compressionOptions: { level: 6 } });
  }

  /* --- split entries by top-level folder into parts <= PART_BYTES --- */
  function splitByFolder(entries) {
    // Group by top-level folder
    var folders = {}; // folderName -> {entries: [], bytes: 0}
    entries.forEach(function (e) {
      var slash = e.path.indexOf('/');
      var folder = slash >= 0 ? e.path.substring(0, slash) : '__root__';
      if (!folders[folder]) folders[folder] = { entries: [], bytes: 0 };
      folders[folder].entries.push(e);
      folders[folder].bytes += e.blob.size;
    });

    var parts = []; // array of entry arrays
    var currentPart = [], currentBytes = 0;

    Object.keys(folders).sort().forEach(function (fname) {
      var f = folders[fname];
      if (currentBytes + f.bytes > PART_BYTES && currentPart.length > 0) {
        parts.push(currentPart);
        currentPart = []; currentBytes = 0;
      }
      currentPart = currentPart.concat(f.entries);
      currentBytes += f.bytes;
    });
    if (currentPart.length > 0) parts.push(currentPart);
    return parts;
  }

  /* --- read a ZIP file's image entries using JSZip --- */
  async function readZipEntries(file) {
    var ab = await file.arrayBuffer();
    var zip = await window.JSZip.loadAsync(ab);
    var entries = [];
    var promises = [];
    zip.forEach(function (path, zipEntry) {
      if (!zipEntry.dir && isImagePath(path) && !path.includes('__MACOSX')) {
        promises.push(
          zipEntry.async('blob').then(function (blob) {
            entries.push({ path: path, blob: blob });
          })
        );
      }
    });
    await Promise.all(promises);
    return entries;
  }

  /* --- read folder / multiple image files --- */
  function readFileEntries(files) {
    var entries = [];
    for (var i = 0; i < files.length; i++) {
      var f = files[i];
      if (!isImagePath(f.name) && !isImageMime(f.type)) continue;
      // webkitRelativePath gives "FolderName/image.jpg"; plain name is just "image.jpg"
      var path = f.webkitRelativePath || f.name;
      entries.push({ path: path, blob: f });
    }
    return entries;
  }

  /* --- inject a blob back into an <input type="file"> --- */
  function injectIntoInput(input, blob, filename) {
    try {
      var file = new File([blob], filename, { type: 'application/zip' });
      var dt = new DataTransfer();
      dt.items.add(file);
      input.files = dt.files;
      // Fire a change event so drop_zone.js updates its preview. Flag the input so
      // our own change listener skips this synthetic event (avoids re-shrinking).
      input._lmShrinkInjecting = true;
      input.dispatchEvent(new Event('change', { bubbles: true }));
      input._lmShrinkInjecting = false;
    } catch (e) {
      console.warn('lm-shrink: could not inject into input', e);
    }
  }

  /* --- UI helpers --- */
  function getOrCreateProgressUI(input) {
    var existing = document.getElementById('lm-shrink-ui-' + input.id);
    if (existing) return existing;
    var div = document.createElement('div');
    div.id = 'lm-shrink-ui-' + input.id;
    div.className = 'lm-shrink-ui';
    div.innerHTML =
      '<div class="lm-shrink-bar-wrap"><div class="lm-shrink-bar" id="lm-shrink-bar-' + input.id + '"></div></div>' +
      '<div class="lm-shrink-status" id="lm-shrink-status-' + input.id + '">Preparing…</div>';
    // Insert after the input's parent card (drop zone) or after the input itself
    var card = input.closest('.lm-dz-card') || input.parentNode;
    card.parentNode.insertBefore(div, card.nextSibling);
    return div;
  }

  function setProgress(inputId, done, total, label) {
    var bar = document.getElementById('lm-shrink-bar-' + inputId);
    var status = document.getElementById('lm-shrink-status-' + inputId);
    if (bar) bar.style.width = (total > 0 ? Math.round(done / total * 100) : 100) + '%';
    if (status) status.textContent = label || ('Shrinking photos ' + done + ' / ' + total);
  }

  function showResult(inputId, msg, isError) {
    var ui = document.getElementById('lm-shrink-ui-' + inputId);
    if (!ui) return;
    ui.innerHTML = '<div class="lm-shrink-result' + (isError ? ' lm-shrink-error' : '') + '">' + msg + '</div>';
  }

  function fmtMB(bytes) { return (bytes / 1024 / 1024).toFixed(1) + ' MB'; }

  /* --- batch upload multiple ZIP blobs to the bulk-upload endpoint --- */
  async function uploadParts(parts, csrfToken, replaceValue, inputId) {
    var combined = { matched: [], unmatched: [], errors: [], skipped: [] };
    for (var i = 0; i < parts.length; i++) {
      setProgress(inputId, i + 1, parts.length, 'Uploading part ' + (i + 1) + ' of ' + parts.length + '…');
      var zipBlob = await buildZip(parts[i]);
      var fd = new FormData();
      fd.append('csrfmiddlewaretoken', csrfToken);
      fd.append('replace', replaceValue || '');
      fd.append('zipfile', new File([zipBlob], 'part_' + (i + 1) + '.zip', { type: 'application/zip' }));

      var resp;
      try {
        resp = await fetch(window.location.pathname, {
          method: 'POST',
          headers: { 'X-Requested-With': 'XMLHttpRequest' },
          body: fd,
        });
      } catch (networkErr) {
        return { error: 'Network error uploading part ' + (i + 1) + ': ' + networkErr };
      }

      if (!resp.ok) {
        var txt = await resp.text().catch(function () { return ''; });
        return { error: 'Server error on part ' + (i + 1) + ': ' + resp.status + ' ' + txt.substring(0, 200) };
      }

      var data;
      try { data = await resp.json(); } catch (e) { return { error: 'Non-JSON response from server' }; }
      if (data.error) return { error: data.error };

      combined.matched = combined.matched.concat(data.matched || []);
      combined.unmatched = combined.unmatched.concat(data.unmatched || []);
      combined.errors = combined.errors.concat(data.errors || []);
      combined.skipped = combined.skipped.concat(data.skipped || []);
    }
    return combined;
  }

  /* --- format a combined JSON report as readable HTML --- */
  function formatReport(data) {
    var lines = [];
    if (data.matched && data.matched.length) {
      lines.push('<strong>✓ ' + data.matched.length + ' product(s) updated:</strong>');
      data.matched.forEach(function (m) { lines.push('&nbsp;&nbsp;' + m.name + ' — ' + m.count + ' photo(s)'); });
    }
    if (data.unmatched && data.unmatched.length) {
      lines.push('<strong style="color:#b45309">⚠ ' + data.unmatched.length + ' folder(s) matched no product:</strong> ' + data.unmatched.join(', '));
    }
    if (data.errors && data.errors.length) {
      lines.push('<strong style="color:#b91c1c">✗ Errors:</strong> ' + data.errors.join('; '));
    }
    return lines.join('<br>') || 'No changes made.';
  }

  /* --- main entry: process a given file input with an explicit file array --- */
  async function handleInputWithFiles(input, fileArray, pageType) {
    if (!fileArray || fileArray.length === 0) return;
    if (!window.JSZip) { console.warn('JSZip not loaded'); return; }

    var files = fileArray;
    var isZip = files.length === 1 && /\.zip$/i.test(files[0].name);

    // Read entries
    var entries;
    setProgress(input.id, 0, 1, 'Reading files…');
    try {
      entries = isZip ? await readZipEntries(files[0]) : readFileEntries(files);
    } catch (e) {
      showResult(input.id, '✗ Could not read files: ' + e, true);
      return;
    }

    if (entries.length === 0) {
      showResult(input.id, 'No image files found.', true);
      return;
    }

    // Shrink
    var shrunk = await shrinkAll(entries, function (done, total) {
      setProgress(input.id, done, total);
    });

    // Show renamed files
    var renames = Object.keys(shrunk.renamedMap);
    var renameNote = renames.length
      ? '<br><small>ℹ ' + renames.length + ' file(s) renamed to .jpg: ' + renames.slice(0, 3).map(function (k) { return shrunk.renamedMap[k]; }).join(', ') + (renames.length > 3 ? '…' : '') + '</small>'
      : '';

    var summary = shrunk.entries.length + ' photos, ' + fmtMB(shrunk.originalBytes) + ' → ' + fmtMB(shrunk.shrunkBytes);

    // Build output ZIP
    setProgress(input.id, shrunk.entries.length, shrunk.entries.length, 'Building ZIP…');
    var outZip = await buildZip(shrunk.entries);

    if (outZip.size <= WARN_BYTES) {
      // Fits in one upload — inject into input
      injectIntoInput(input, outZip, 'photos_shrunk.zip');
      showResult(input.id, '✓ ' + summary + renameNote + '<br><small>Ready to submit.</small>');
      return;
    }

    // ZIP is still large
    if (pageType === 'bulk-import') {
      // Can't split + batch on bulk-import (Excel needed too)
      injectIntoInput(input, outZip, 'photos_shrunk.zip');
      if (outZip.size > 60 * 1024 * 1024) {
        showResult(input.id,
          '⚠ ' + summary + ' — photos are ' + fmtMB(outZip.size) + ' after shrinking. ' +
          'Import the Excel/CSV now (leave the ZIP empty), then add photos separately via <strong>Bulk photo upload</strong>.' + renameNote,
          true);
      } else {
        showResult(input.id, '✓ ' + summary + renameNote + '<br><small>Ready to submit.</small>');
      }
      return;
    }

    // bulk-upload: split by folder and upload via AJAX
    var parts = splitByFolder(shrunk.entries);
    if (parts.length <= 1) {
      // Single part (just large) — inject and warn
      injectIntoInput(input, outZip, 'photos_shrunk.zip');
      showResult(input.id, '✓ ' + summary + renameNote + '<br><small>Ready to submit (ZIP is ' + fmtMB(outZip.size) + ').</small>');
      return;
    }

    // Multiple parts — upload automatically
    showResult(input.id, 'Splitting into ' + parts.length + ' parts (' + summary + ')…' + renameNote);
    var csrfToken = (document.querySelector('[name=csrfmiddlewaretoken]') || {}).value || '';
    var replaceVal = (document.querySelector('[name=replace]') || {}).checked ? 'on' : '';
    var result = await uploadParts(parts, csrfToken, replaceVal, input.id);
    if (result.error) {
      showResult(input.id, '✗ Upload failed: ' + result.error + renameNote, true);
    } else {
      // Disable the form submit button and show inline result
      var form = input.closest('form');
      if (form) {
        var btn = form.querySelector('[type=submit]');
        if (btn) btn.disabled = true;
      }
      showResult(input.id, '✓ All parts uploaded. ' + formatReport(result) + renameNote);
    }
  }

  /* --- wire up each shrink-enabled input on page load --- */
  function initShrink() {
    var targets = document.querySelectorAll('[data-dz-shrink]');
    targets.forEach(function (input) {
      var pageType = input.dataset.dzShrink || 'bulk-upload';
      var ui = getOrCreateProgressUI(input);

      // Guard against re-entrancy: injectIntoInput fires a 'change' event, which
      // would otherwise re-trigger the shrinker on the already-shrunk ZIP.
      input.addEventListener('change', function () {
        if (input._lmShrinkInjecting) return;
        if (!input.files || !input.files.length) return;
        ui.style.display = 'block';
        handleInputWithFiles(input, Array.from(input.files), pageType).catch(function (e) {
          showResult(input.id, '✗ Error: ' + e, true);
        });
      });

      // Handle folder / multi-image picks relayed from the secondary inputs.
      input.addEventListener('lm-shrink-files', function (e) {
        var overrideFiles = e.detail && e.detail.files;
        if (!overrideFiles || !overrideFiles.length) return;
        ui.style.display = 'block';
        var pageType2 = (e.detail && e.detail.pageType) || pageType;
        handleInputWithFiles(input, Array.from(overrideFiles), pageType2).catch(function (err) {
          showResult(input.id, '✗ Error: ' + err, true);
        });
      });
    });
  }

  document.addEventListener('DOMContentLoaded', initShrink);
})();
