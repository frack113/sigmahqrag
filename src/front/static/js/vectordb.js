async function loadVectorDB() {
    if (window.isProcessing) return;
    window.isProcessing = true;

    const loadingEl = document.getElementById('vectordb-loading');
    const contentEl = document.getElementById('vectordb-content');
    const errorEl = document.getElementById('vectordb-error');
    const tableBody = document.getElementById('collections-list');

    if (loadingEl) loadingEl.style.display = 'block';
    if (contentEl) contentEl.style.display = 'none';
    if (errorEl) errorEl.style.display = 'none';

    try {
        // 1. Check Status using the new helper
        const status = await getQdrantStatus();

        if (!status.healthy) {
            throw new Error(`Qdrint is unhealthy: ${status.service} version ${status.current_version}`);
        }

        // 2. Get Collections List using our new helper
        const collectionNames = await listCollections();

        if (tableBody) {
            tableBody.innerHTML = '';
        }

        for (const col of collectionNames) {
             // 3. Use the data already in the list object
             const config = col;

            if (tableBody) {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${col.name}</td>
                    <td><span class="badge bg-success">Active</span></td>
                    <td class="num">~${config.points || 0}</td>
                    <td class="num">${col.shards || 1}</td>
                    <td class="num">${config.vector_size || 384}-dim</td>
                    <td>
                        <button class="btn btn-danger btn-sm" onclick="recreateCollection('${col.name}')">
                            [Re Create]
                        </button>
                    </td>
                `;
                tableBody.appendChild(row);
            }
        }

        if (contentEl) contentEl.style.display = 'block';

    } catch (e) {
        console.error('Error loading Vector DB:', e);
        if (errorEl) {
            errorEl.textContent = `Error: ${e.message}`;
            errorEl.style.display = 'block';
        }
    } finally {
        window.isProcessing = false;
        if (loadingEl) loadingEl.style.display = 'none';
    }
}

async function recreateCollection(name) {
    if (!confirm(`Are you sure you want to RE-CREATE the collection "${name}"? This will DELETE all existing data.`)) {
        return;
    }

    if (window.isProcessing) return;
    window.isProcessing = true;

    try {
        // 1. Delete
        await deleteCollection(name);
        
        // 2. Create (using default 384 dim as per project convention)
        await createCollection(name);

        alert(`Collection "${name}" has been successfully re-created.`);
        await loadVectorDB();
    } catch (e) {
        console.error('Error recreating collection:', e);
        alert(`Failed to recreate collection: ${e.message}`);
    } finally {
        window.isProcessing = false;
    }
}

async function startSigmaRefEmbedding() {
    if (window.isProcessing) return;

    const githubProgressSection = document.getElementById('github-progress-section');
    const githubProgressFill = document.getElementById('github-progress-fill');
    const githubProgressText = document.getElementById('github-progress-text');
    const githubMessageEl = document.getElementById('github-message');
    
    const progressSection = document.getElementById('sigmaref-progress-section');
    const progressFill = document.getElementById('sigmaref-progress-fill');
    const progressText = document.getElementById('sigmaref-progress-text');
    const messageEl = document.getElementById('sigmaref-message');
    const btnIndexDocs = document.getElementById('btn-index-docs');

    if (btnIndexDocs) btnIndexDocs.disabled = true;
    if (githubMessageEl) githubMessageEl.style.display = 'none';
    if (messageEl) messageEl.style.display = 'none';
    
    [githubProgressFill, progressFill].forEach(fill => {
        if (fill) {
            fill.style.width = '0%';
            fill.style.background = 'linear-gradient(to right, rgb(0, 0, 1), rgb(0, 0, 255))';
        }
    });
    [githubProgressText, progressText].forEach(text => {
        if (text) text.textContent = '0%';
    });

    try {
        const response = await fetch('/api/v1/files/embed', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        const result = await response.json();

        if (result.success || result.data) {
            const tasks = result.data?.triggered || [];
            
            if (tasks.includes('github_embeddings')) {
                pollEmbedProgress('github_embeddings', githubProgressFill, githubProgressText, githubMessageEl, btnIndexDocs);
            }
            
            if (tasks.includes('sigmaref_embeddings')) {
                pollEmbedProgress('sigmaref_embeddings', progressFill, progressText, messageEl, btnIndexDocs);
            }
            
            if (tasks.length === 0) {
                if (result.error) {
                    throw new Error(result.error);
                }
            }
        } else {
            throw new Error(result.error || result.message || 'Unknown error');
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
        [githubProgressFill, progressFill].forEach(fill => {
            if (fill) fill.style.width = '0%';
        });
        if (btnIndexDocs) btnIndexDocs.disabled = false;
    }
}

async function pollEmbedProgress(source, progressFill, progressText, messageEl, btnIndexDocs) {
    let pollCount = 0;
    const maxPolls = 300;
    const pollInterval = setInterval(async () => {
        pollCount++;
        if (pollCount > maxPolls) {
            clearInterval(pollInterval);
            checkAllComplete(btnIndexDocs);
            return;
        }
        try {
            const response = await fetch(`/api/v1/qdrant/embed-status/${source}`);
            const statusData = await response.json();

            if (!statusData || statusData.status === 'not_found') {
                if (pollCount > 5) {
                    clearInterval(pollInterval);
                    checkAllComplete(btnIndexDocs);
                }
                return;
            }

            if (statusData.status === 'running') {
                const pct = Math.round(statusData.progress_percent || 0);
                if (progressFill) progressFill.style.width = pct + '%';
                if (progressText) progressText.textContent = pct + '%';
            } else if (statusData.status === 'completed' || statusData.status === 'idle') {
                if (progressFill) {
                    progressFill.style.width = '100%';
                    progressFill.style.background = '#4caf50';
                }
                if (progressText) progressText.textContent = '100%';
                if (messageEl) {
                    messageEl.textContent = statusData.status === 'idle' ? 'Completed (no new documents)' : (statusData.message || 'Completed');
                    messageEl.style.display = 'block';
                }
                clearInterval(pollInterval);
                checkAllComplete(btnIndexDocs);
            } else if (statusData.status === 'failed') {
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

// Initialize on load
document.addEventListener('DOMContentLoaded', loadVectorDB);
