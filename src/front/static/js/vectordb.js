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

    const progressSection = document.getElementById('sigmaref-progress-section');
    const progressFill = document.getElementById('sigmaref-progress-fill');
    const progressText = document.getElementById('sigmaref-progress-text');
    const messageEl = document.getElementById('sigmaref-message');
    const btnIndexDocs = document.getElementById('btn-index-docs');

    if (btnIndexDocs) btnIndexDocs.disabled = true;
    if (messageEl) messageEl.style.display = 'none';
    if (progressFill) {
        progressFill.style.width = '0%';
        progressFill.style.background = 'linear-gradient(to right, rgb(0, 0, 1), rgb(0, 0, 255))';
    }
    if (progressText) progressText.textContent = '0%';

    try {
        const response = await fetch('/api/v1/qdrant', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                action: 'embed_sigmaref',
                payload: {
                    action: 'embed_sigmaref',
                    registry_path: 'data/documents/sigmaref/registry.json',
                    collection_name: 'sigma_doc'
                }
            })
        });
        const result = await response.json();

        if (result.status === 'success') {
            const taskId = result.data.task_id;
            localStorage.setItem('SIGMAREF_TASK_KEY', taskId);

            const streamResp = await fetch(`/api/v1/qdrant/embed/${taskId}/stream`);
            const reader = streamResp.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';

            const timeout = setTimeout(() => {
                reader.cancel();
                done();
            }, 10000);

            function done() {
                clearTimeout(timeout);
                if (btnIndexDocs) btnIndexDocs.disabled = false;
            }

            while (true) {
                const { done: streamDone, value } = await reader.read();
                if (streamDone) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop() || '';

                for (const line of lines) {
                    if (!line.startsWith('data: ')) continue;
                    const data = JSON.parse(line.slice(6));

                    if (data.status === 'processing') {
                        const pct = data.total > 0 ? Math.round((data.processed / data.total) * 100) : 0;
                        if (progressFill) progressFill.style.width = pct + '%';
                        if (progressText) progressText.textContent = pct + '%';
                    } else if (data.status === 'completed') {
                        if (progressFill) {
                            progressFill.style.width = '100%';
                            progressFill.style.background = '#4caf50';
                        }
                        if (progressText) progressText.textContent = '100%';
                        if (messageEl) {
                            messageEl.textContent = data.message || 'Completed';
                            messageEl.style.display = 'block';
                        }
                        done();
                        return;
                    } else if (data.status === 'failed') {
                        if (progressFill) {
                            progressFill.style.background = '#f44336';
                        }
                        if (messageEl) {
                            messageEl.textContent = 'Error: ' + (data.error || 'Task failed');
                            messageEl.style.display = 'block';
                        }
                        done();
                        return;
                    } else if (data.status === 'timeout' || data.status === 'not_found') {
                        if (progressFill) progressFill.style.background = '#ff9800';
                        if (messageEl) {
                            messageEl.textContent = data.status === 'timeout' ? 'Connection timed out' : 'Task not found';
                            messageEl.style.display = 'block';
                        }
                        done();
                        return;
                    }
                }
            }
            done();
        } else {
            throw new Error(result.message || 'Unknown error');
        }
    } catch (error) {
        console.error('Failed to start SigmaRef embedding:', error);
        if (messageEl) {
            messageEl.textContent = 'Error: ' + error.message;
            messageEl.style.display = 'block';
        }
        if (progressFill) progressFill.style.width = '0%';
        if (progressText) progressText.textContent = '0%';
    } finally {
        if (btnIndexDocs) btnIndexDocs.disabled = false;
    }
}

// Initialize on load
document.addEventListener('DOMContentLoaded', loadVectorDB);
