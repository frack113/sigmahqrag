// Admin UI interactions
document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('health-status')) {
        pollHealthStatus();
    }
    initBulkActions();
    if (document.getElementById('repo_list')) {
        loadRepoList();
        setInterval(loadRepoList, 5000);
    }
});

async function pollHealthStatus() {
    try {
        const response = await fetch('/api/v1/admin/status');
        const data = await response.json();
        updateGlobalStatusBar(data);
        updateSidebarDots(data);
    } catch (error) {
        console.error('Health poll failed:', error);
    } finally {
        setTimeout(pollHealthStatus, 30000);
    }
}

function updateGlobalStatusBar(data) {
    const statusBar = document.getElementById('global-status-bar');
    if (!statusBar) return;
    const isHealthy = data.llm_available && data.qdrant_available;
    statusBar.className = `status-bar ${isHealthy ? 'status-ok' : 'status-error'}`;
    statusBar.style.display = 'block';
    statusBar.textContent = isHealthy ? 'All systems operational' : 'System issues detected';
}

function updateSidebarDots(data) {
    const dotDashboard = document.getElementById('dot-dashboard');
    if (dotDashboard) {
        dotDashboard.className = `status-dot ${data.llm_available && data.qdrant_available ? 'status-ok' : 'status-error'}`;
    }
    const dotModels = document.getElementById('dot-models');
    if (dotModels) {
        dotModels.className = `status-dot ${data.installed_models_count > 0 ? 'status-ok' : 'status-warning'}`;
    }
}

function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
}

function initBulkActions() {
    const selectAll = document.getElementById('select-all-models');
    if (!selectAll) return;
    selectAll.addEventListener('change', (e) => {
        document.querySelectorAll('.model-checkbox').forEach(cb => cb.checked = e.target.checked);
        updateBulkDeleteButton();
    });
    document.querySelectorAll('.model-checkbox').forEach(cb => {
        cb.addEventListener('change', updateBulkDeleteButton);
    });
}

function updateBulkDeleteButton() {
    const checked = document.querySelectorAll('.model-checkbox:checked');
    const btn = document.getElementById('bulk-delete-btn');
    if (btn) {
        btn.disabled = checked.length === 0;
        btn.textContent = `Delete (${checked.length})`;
    }
}

async function bulkDeleteModels() {
    const checked = document.querySelectorAll('.model-checkbox:checked');
    if (checked.length === 0 || !confirm(`Delete ${checked.length} model(s)?`)) return;
    const payload = Array.from(checked).map(cb => {
        const row = cb.closest('tr');
        return { repo_id: row.dataset.repoId, filename: row.dataset.filename };
    });
    try {
        const response = await fetch('/api/v1/admin/bulk-delete-models', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const result = await response.json();
        if (result.deleted.length) {
            showToast(`Deleted ${result.deleted.length} model(s)`, 'success');
            checked.forEach(cb => cb.closest('tr').remove());
        }
        result.errors.forEach(err => showToast(err, 'error'));
    } catch (error) {
        showToast('Bulk delete failed', 'error');
    } finally {
        updateBulkDeleteButton();
    }
}

async function loadRepoList() {
    const tbody = document.getElementById('repo_list_body');
    const statusEl = document.getElementById('repos_status');
    if (!tbody) return;
    try {
        const response = await fetch('/api/v1/github/repos');
        const repos = await response.json();
        if (repos.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5">No repositories managed</td></tr>';
            return;
        }
        tbody.innerHTML = repos.map(repo => {
            const org = repo.org || '';
            const name = repo.name || '';
            const orgEsc = org.replace(/[<>&"']/g, c => ({'<':'&lt;','>':'&gt;','&':'&amp;','"':'&quot;',"'":'&#39;'})[c]);
            const nameEsc = name.replace(/[<>&"']/g, c => ({'<':'&lt;','>':'&gt;','&':'&amp;','"':'&quot;',"'":'&#39;'})[c]);
            const urlEsc = (repo.url || '-').replace(/[<>&"']/g, c => ({'<':'&lt;','>':'&gt;','&':'&amp;','"':'&quot;',"'":'&#39;'})[c]);
            const statusEsc = (repo.repo_status || '-').replace(/[<>&"']/g, c => ({'<':'&lt;','>':'&gt;','&':'&amp;','"':'&quot;',"'":'&#39;'})[c]);
            return `<tr>
                <td>${orgEsc}/${nameEsc}</td>
                <td>${urlEsc}</td>
                <td><span class="status-${statusEsc}">${statusEsc}</span></td>
                <td>${repo.last_synced || '-'}</td>
                <td>
                    <button onclick="syncRepo('${orgEsc}', '${nameEsc}')">Sync</button>
                    <button onclick="deleteRepo('${orgEsc}', '${nameEsc}')">Delete</button>
                </td>
            </tr>`;
        }).join('');
        statusEl.textContent = `${repos.length} repository(s)`;
    } catch (error) {
        console.error('Failed to load repos:', error);
        statusEl.textContent = 'Error loading repositories';
    }
}

async function addRepo() {
    const urlInput = document.getElementById('repo_url');
    const url = urlInput?.value?.trim();
    if (!url) {
        showToast('Please enter a repository URL', 'error');
        return;
    }
    try {
        const response = await fetch('/api/v1/github/repos', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url, branch: 'main' })
        });
        const result = await response.json();
        if (result.success) {
            showToast('Repository added successfully', 'success');
            urlInput.value = '';
            loadRepoList();
        } else {
            showToast(result.error || 'Failed to add repository', 'error');
        }
    } catch (error) {
        showToast('Failed to add repository', 'error');
    }
}

async function syncRepo(org, name) {
    try {
        const response = await fetch(`/api/v1/github/repos/${org}/${name}/sync`, {
            method: 'POST'
        });
        const result = await response.json();
        if (result.success) {
            showToast('Repository syncing...', 'success');
        } else {
            showToast(result.error || 'Failed to sync', 'error');
        }
    } catch (error) {
        showToast('Failed to sync repository', 'error');
    }
}

async function deleteRepo(org, name) {
    if (!confirm(`Delete repository ${org}/${name}?`)) return;
    try {
        const response = await fetch(`/api/v1/github/repos/${org}/${name}`, {
            method: 'DELETE'
        });
        const result = await response.json();
        if (result.success) {
            showToast('Repository deleted', 'success');
            loadRepoList();
        } else {
            showToast(result.error || 'Failed to delete', 'error');
        }
    } catch (error) {
        showToast('Failed to delete repository', 'error');
    }
}
