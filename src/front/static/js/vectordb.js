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

async function startSigmaRefEmbedding() {
    if (window.isProcessing) return;

    var githubProgressSection = document.getElementById('github-progress-section');
    var githubProgressFill = document.getElementById('github-progress-fill');
    var githubProgressText = document.getElementById('github-progress-text');
    var githubMessageEl = document.getElementById('github-message');

    var progressSection = document.getElementById('sigmaref-progress-section');
    var progressFill = document.getElementById('sigmaref-progress-fill');
    var progressText = document.getElementById('sigmaref-progress-text');
    var messageEl = document.getElementById('sigmaref-message');
    var btnIndexDocs = document.getElementById('btn-index-docs');

    if (btnIndexDocs) btnIndexDocs.disabled = true;
    if (githubMessageEl) githubMessageEl.style.display = 'none';
    if (messageEl) messageEl.style.display = 'none';

    [githubProgressFill, progressFill].forEach(function(fill) {
        if (fill) {
            fill.style.width = '0%';
            fill.style.background = 'linear-gradient(to right, rgb(0, 0, 1), rgb(0, 0, 255))';
        }
    });
    [githubProgressText, progressText].forEach(function(text) {
        if (text) text.textContent = '0%';
    });

    try {
        var tasks = [];

        var gResult = await askWorker('github_embeddings', { collection_name: 'all' });
        if (gResult.task_id) {
            tasks.push('github_embeddings');
        }

        var sResult = await askWorker('sigmaref_embeddings', { collection_name: 'sigmaref' });
        if (sResult.task_id) {
            tasks.push('sigmaref_embeddings');
        }

        if (tasks.indexOf('github_embeddings') !== -1) {
            pollEmbedProgress('github_embeddings', githubProgressFill, githubProgressText, githubMessageEl, btnIndexDocs);
        }

        if (tasks.indexOf('sigmaref_embeddings') !== -1) {
            pollEmbedProgress('sigmaref_embeddings', progressFill, progressText, messageEl, btnIndexDocs);
        }

        if (tasks.length === 0) {
            if (gResult.error && sResult.error) {
                throw new Error('All workers busy');
            }
        }
    } catch (error) {
        console.error('Failed to start embedding:', error);
        if (githubMessageEl) {
            githubMessageEl.textContent = 'Error: ' + error.message;
            githubMessageEl.style.display = 'block';
        }
        if (messageEl) {
            messageEl.textContent = 'Error: ' + error.message;
            messageEl.style.display = 'block';
        }
        [githubProgressFill, progressFill].forEach(function(fill) {
            if (fill) fill.style.width = '0%';
        });
        if (btnIndexDocs) btnIndexDocs.disabled = false;
    }
}

async function pollEmbedProgress(source, progressFill, progressText, messageEl, btnIndexDocs) {
    var pollCount = 0;
    var maxPolls = 300;
    var pollInterval = setInterval(async function() {
        pollCount++;
        if (pollCount > maxPolls) {
            clearInterval(pollInterval);
            checkAllComplete(btnIndexDocs);
            return;
        }
        try {
            var response = await fetch(DISPATCHER_API + '/status/' + encodeURIComponent(source));
            if (response.status === 404) {
                if (pollCount > 5) {
                    clearInterval(pollInterval);
                    checkAllComplete(btnIndexDocs);
                }
                return;
            }
            var statusData = await response.json();

            if (statusData.status === 'running' || statusData.status === 'waiting') {
                var pct = Math.round(statusData.progress_percent || 0);
                if (progressFill) progressFill.style.width = pct + '%';
                if (progressText) progressText.textContent = pct + '%';
            } else if (statusData.status === 'idle') {
                if (progressFill) {
                    progressFill.style.width = '100%';
                    progressFill.style.background = '#4caf50';
                }
                if (progressText) progressText.textContent = '100%';
                if (messageEl) {
                    messageEl.textContent = 'Completed';
                    messageEl.style.display = 'block';
                }
                clearInterval(pollInterval);
                checkAllComplete(btnIndexDocs);
            } else if (statusData.status === 'error') {
                if (progressFill) {
                    progressFill.style.background = '#f44336';
                }
                if (messageEl) {
                    messageEl.textContent = 'Error: ' + (statusData.error || 'Task failed');
                    messageEl.style.display = 'block';
                }
                clearInterval(pollInterval);
                checkAllComplete(btnIndexDocs);
            }
        } catch (e) {
            console.error('Poll error:', e);
            clearInterval(pollInterval);
            checkAllComplete(btnIndexDocs);
        }
    }, 2000);
}

function checkAllComplete(btnIndexDocs) {
    if (btnIndexDocs) btnIndexDocs.disabled = false;
}

document.addEventListener('DOMContentLoaded', loadVectorDB);
