const DISPATCHER_API = '/api/v1/dispatcher';

function esc(s) {
    if (s == null) return '';
    var m = { '&': '\x26amp;', '<': '\x26lt;', '>': '\x26gt;', '"': '\x26quot;', "'": '\x26#39;' };
    return String(s).replace(/[&<>"']/g, function(c) { return m[c]; });
}

function escAttr(s) {
    if (s == null) return '';
    var m = { '&': '\x26amp;', '"': '\x26quot;', "'": '\x26#39;', '<': '\x26lt;', '>': '\x26gt;' };
    return String(s).replace(/[&"'<>]/g, function(c) { return m[c]; });
}

async function loadVectorDB() {
    if (window.isProcessing) return;
    window.isProcessing = true;

    var loadingEl = document.getElementById('vectordb-loading');
    var contentEl = document.getElementById('vectordb-content');
    var errorEl = document.getElementById('vectordb-error');
    var tableBody = document.getElementById('collections-list');

    if (loadingEl) loadingEl.style.display = 'block';
    if (contentEl) contentEl.style.display = 'none';
    if (errorEl) errorEl.style.display = 'none';

    try {
        var status = await getQdrantStatus();

        if (!status.healthy) {
            throw new Error('Qdrint is unhealthy: ' + status.service + ' version ' + status.current_version);
        }

        var collectionNames = await listCollections();

        if (tableBody) {
            tableBody.innerHTML = '';
        }

        for (var i = 0; i < collectionNames.length; i++) {
            var col = collectionNames[i];
            var config = col;
            var nameEsc = esc(col.name);
            var nameAttr = escAttr(col.name);

            if (tableBody) {
                var row = document.createElement('tr');
                row.innerHTML = '<td>' + nameEsc + '</td>'
                    + '<td><span class="badge bg-success">Active</span></td>'
                    + '<td class="num">~' + esc(config.points || 0) + '</td>'
                    + '<td class="num">' + esc(col.shards || 1) + '</td>'
                    + '<td class="num">' + esc(config.vector_size || 384) + '-dim</td>'
                    + '<td>'
                    + '<button class="btn btn-danger btn-sm" onclick="recreateCollection(\x27' + nameAttr + '\x27)">'
                    + '[Re Create]'
                    + '</button>'
                    + '</td>';
                tableBody.appendChild(row);
            }
        }

        if (contentEl) contentEl.style.display = 'block';

    } catch (e) {
        console.error('Error loading Vector DB:', e);
        if (errorEl) {
            errorEl.textContent = 'Error: ' + e.message;
            errorEl.style.display = 'block';
        }
    } finally {
        window.isProcessing = false;
        if (loadingEl) loadingEl.style.display = 'none';
    }
}

async function recreateCollection(name) {
    if (!confirm('Are you sure you want to RE-CREATE the collection "' + name + '"? This will DELETE all existing data.')) {
        return;
    }

    if (window.isProcessing) return;
    window.isProcessing = true;

    var btn = event?.target || event?.srcElement;
    if (btn) btn.disabled = true;

    try {
        await deleteCollection(name);
        await createCollection(name);

        await loadVectorDB();
    } catch (e) {
        console.error('Error recreating collection:', e);
        alert('Failed to recreate collection: ' + e.message);
    } finally {
        window.isProcessing = false;
        if (btn) btn.disabled = false;
    }
}

async function askWorker(workerType, taskParams) {
    var resp = await fetch(DISPATCHER_API + '/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ worker_type: workerType, task_params: taskParams || {} }),
    });
    return await resp.json();
}

async function startUnifiedIndex() {
    var btn = document.getElementById('btn-index-docs');
    if (btn && btn.disabled) return;  // already running
    if (btn) btn.disabled = true;

    var specBar = new ProgressBar({
        container: document.getElementById('indexer-progress-spec'),
        fill: document.getElementById('indexer-progress-spec-fill'),
        text: document.getElementById('indexer-progress-spec-text'),
    });
    var docsBar = new ProgressBar({
        container: document.getElementById('indexer-progress-docs'),
        fill: document.getElementById('indexer-progress-docs-fill'),
        text: document.getElementById('indexer-progress-docs-text'),
    });
    var resultEl = document.getElementById('indexer-result');
    var errorEl = document.getElementById('indexer-error');

    if (resultEl) resultEl.style.display = 'none';
    if (errorEl) errorEl.style.display = 'none';

    function setSpecProgress(pct, label) {
        specBar.setProgress(pct);
        specBar.setText(label);
    }

    function setDocsProgress(pct, label) {
        docsBar.setProgress(pct);
        docsBar.setText(label);
    }

    async function callGroup(group) {
        var resp = await fetch('/api/v1/qdrant', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action: 'index_all', payload: { action: 'index_all', group: group } }),
        });
        if (!resp.ok) {
            var body = await resp.text();
            throw new Error('HTTP ' + resp.status + ': ' + body.slice(0, 200));
        }
        return await resp.json();
    }

    console.log('Indexer: starting spec phase...');

    try {
        // Phase 1: Specification
        setSpecProgress(0, 'Indexation...');
        setDocsProgress(0, 'En attente');
        var specResult = await callGroup('spec');
        if (specResult.status === 'success') {
            var specCount = (specResult.data && specResult.data.results) ? specResult.data.results.reduce(function(s, r) { return s + r.processed; }, 0) : 0;
            setSpecProgress(100, specCount + ' documents');
            console.log('Indexer: spec done, ' + specCount + ' documents');
        } else {
            setSpecProgress(0, 'Erreur');
            if (errorEl) { errorEl.textContent = 'Erreur spécification: ' + (specResult.message || 'Échec'); errorEl.style.display = 'block'; }
            console.error('Indexer: spec failed', specResult);
            return;
        }

        // Phase 2: Documents
        console.log('Indexer: starting docs phase...');
        setDocsProgress(0, 'Indexation...');
        var docsResult = await callGroup('docs');
        if (docsResult.status === 'success') {
            var docsCount = (docsResult.data && docsResult.data.results) ? docsResult.data.results.reduce(function(s, r) { return s + r.processed; }, 0) : 0;
            setDocsProgress(100, docsCount + ' documents');
            console.log('Indexer: docs done, ' + docsCount + ' documents');
        } else {
            setDocsProgress(0, 'Erreur');
            if (errorEl) { errorEl.textContent = 'Erreur documents: ' + (docsResult.message || 'Échec'); errorEl.style.display = 'block'; }
            console.error('Indexer: docs failed', docsResult);
            return;
        }

        // Show combined result
        if (resultEl) {
            var specResults = (specResult.data && specResult.data.results) || [];
            var docsResults = (docsResult.data && docsResult.data.results) || [];
            var allResults = specResults.concat(docsResults);
            var lines = allResults.map(function(r) {
                return r.route + ': ' + r.processed + ' documents' + (r.errors && r.errors.length ? ' (' + r.errors.length + ' erreurs)' : '');
            });
            resultEl.innerHTML = '<strong>Terminé</strong><br>' + lines.join('<br>');
            resultEl.style.display = 'block';
        }
    } catch (error) {
        console.error('Indexer error:', error);
        if (errorEl) {
            errorEl.textContent = 'Erreur: ' + error.message;
            errorEl.style.display = 'block';
        }
    } finally {
        if (btn) btn.disabled = false;
    }
}

document.addEventListener('DOMContentLoaded', loadVectorDB);
