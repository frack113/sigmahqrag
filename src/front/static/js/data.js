// Data Sources - GitHub Repository Management

document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('repo_list')) {
        loadRepoList();
        setInterval(loadRepoList, 5000);
    }
});

async function loadRepoList() {
    const tbody = document.getElementById('repo_list_body');
    const statusEl = document.getElementById('repos_status');
    if (!tbody) return;
    try {
        const response = await fetch('/api/v1/github/repos');
        const repos = await response.json();
        if (repos.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5">No repositories managed</td></tr>';
            statusEl.textContent = 'No repositories';
            return;
        }
        tbody.innerHTML = repos.map(repo => `
            <tr>
                <td>${repo.org}/${repo.name}</td>
                <td>${repo.url || '-'}</td>
                <td><span class="status-${repo.repo_status}">${repo.repo_status}</span></td>
                <td>${repo.last_synced || '-'}</td>
                <td class="actions">
                    <button onclick="syncRepo('${repo.org}', '${repo.name}')" class="sync-btn">Sync</button>
                    <button onclick="deleteRepo('${repo.org}', '${repo.name}')" class="delete-btn">Delete</button>
                </td>
            </tr>
        `).join('');
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