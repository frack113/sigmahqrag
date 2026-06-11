/**
 * Reusable GitHub release tag selector JS module.
 *
 * Usage:
 *   <link rel="stylesheet" href="/static/css/_shared-layout.css">
 *   <div class="form-group">
 *     <label>Release Tag:</label>
 *     <select id="my-select"></select>
 *   </div>
 *   <script src="/static/js/release-selector.js"></script>
 *   <script>
 *     loadReleaseTags('my-select', 'llama.cpp');
 *     // or for a custom repo:
 *     loadCustomReleaseTags('my-select', 'qdrant', 'qdrant-web-ui');
 *   </script>
 */

function _matchTag(tag, value) {
    if (!value) return false;
    if (tag === value) return true;
    var t = tag.replace(/^[vb]/i, '');
    var v = value.replace(/^[vb]/i, '');
    return t === value || tag === 'v' + v || tag === 'b' + v || t === v;
}

function _populateSelect(sel, releases, opts, fmt) {
    var found = false;
    releases.forEach(function(r) {
        var opt = document.createElement('option');
        opt.value = r.tag_name;
        var label = fmt(r);
        if (_matchTag(r.tag_name, opts.value)) { opt.selected = true; found = true; label += ' (installed)'; }
        opt.textContent = label;
        sel.appendChild(opt);
    });
    if (opts.value && !found) {
        var opt = document.createElement('option');
        opt.value = opts.value;
        opt.textContent = opts.value.replace(/^[vb]/i, '') + ' (installed)';
        opt.selected = true;
        sel.insertBefore(opt, sel.firstChild);
    }
}

/**
 * Default label formatter: strip leading 'v' or 'b' prefix from tag for display.
 */
function defaultReleaseLabel(r) {
    var tag = r.tag_name || '';
    var label = tag.replace(/^[vb]/i, '');
    if (r.prerelease) label += ' (pre-release)';
    return label || tag;
}

/**
 * Populate a <select> with release tags for a known service.
 * @param {string} selectId - DOM id of the <select> element
 * @param {string} service - Service name (llama.cpp, qdrant, qdrant-web-ui)
 * @param {object} [opts] - Optional overrides
 * @param {string} [opts.placeholder] - Placeholder text (default: "Latest (auto)")
 * @param {function} [opts.onLoad] - Callback after populate (receives releases array)
 * @param {string} [opts.value] - Tag value to pre-select
 * @param {function} [opts.label] - Label formatter fn(release) -> string (default: strips v/b prefix)
 */
function loadReleaseTags(selectId, service, opts) {
    opts = opts || {};
    var sel = document.getElementById(selectId);
    if (!sel) return;
    var fmt = opts.label || defaultReleaseLabel;
    sel.innerHTML = '';
    fetch('/api/v1/releases/' + encodeURIComponent(service))
        .then(function(r) { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
        .then(function(data) {
            var releases = data.releases || [];
            if (releases.length) {
                _populateSelect(sel, releases, opts, fmt);
            } else if (opts.value) {
                sel.innerHTML = '<option value="' + opts.value + '" selected>' + opts.value.replace(/^[vb]/i, '') + ' (installed)</option><option value="">\u2014 Refresh to load releases \u2014</option>';
            } else {
                sel.innerHTML = '<option value="">\u2014 Press \u21bb Refresh \u2014</option>';
            }
            if (opts.onLoad) opts.onLoad(releases);
        })
        .catch(function() {
            if (opts.value) {
                sel.innerHTML = '<option value="' + opts.value + '" selected>' + opts.value.replace(/^[vb]/i, '') + ' (installed)</option>';
            } else {
                sel.innerHTML = '<option value="">Unavailable</option>';
            }
        });
}

/**
 * Populate a <select> with release tags for an arbitrary GitHub repo.
 * @param {string} selectId - DOM id of the <select> element
 * @param {string} owner - GitHub owner
 * @param {string} repo - Repository name
 * @param {object} [opts] - Same options as loadReleaseTags
 */
function loadCustomReleaseTags(selectId, owner, repo, opts) {
    opts = opts || {};
    var sel = document.getElementById(selectId);
    if (!sel) return;
    var fmt = opts.label || defaultReleaseLabel;
    sel.innerHTML = '';
    fetch('/api/v1/releases/custom/?owner=' + encodeURIComponent(owner) + '&repo=' + encodeURIComponent(repo))
        .then(function(r) { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
        .then(function(data) {
            var releases = data.releases || [];
            if (releases.length) {
                _populateSelect(sel, releases, opts, fmt);
            } else {
                sel.innerHTML = '<option value="">\u2014 Press \u21bb Refresh \u2014</option>';
            }
            if (opts.onLoad) opts.onLoad(releases);
        })
        .catch(function() {
            sel.innerHTML = '<option value="">Unavailable</option>';
        });
}

/**
 * Refresh all release caches from GitHub and re-populate all selectors.
 * @param {Array} services - Array of {selectId, service}
 * @param {Array} customServices - Array of {selectId, owner, repo}
 * @param {object} [opts] - Options with version info for pre-selection
 * @param {function} [opts.onComplete] - Called after all selects re-populated
 */
function refreshAllReleases(services, customServices, opts) {
    opts = opts || {};
    fetch('/api/v1/releases/refresh', { method: 'POST' })
        .then(function(r) { return r.json(); })
        .then(function(data) {
            if (services) {
                services.forEach(function(s) {
                    loadReleaseTags(s.selectId, s.service, s.opts || {});
                });
            }
            if (customServices) {
                customServices.forEach(function(s) {
                    loadCustomReleaseTags(s.selectId, s.owner, s.repo, s.opts || {});
                });
            }
            if (opts.onComplete) opts.onComplete(data);
        })
        .catch(function(err) {
            console.error('Refresh failed:', err);
        });
}
