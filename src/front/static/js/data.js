// Data Sources - GitHub Repository Management

document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('repo_list')) {
        loadRepoList();
        setInterval(loadRepoList, 5000);
    }
});

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

async function loadRepoList() {
    var tbody = document.getElementById('repo_list_body');
    var statusEl = document.getElementById('repos_status');
    if (!tbody) return;
    try {
        var response = await fetch('/api/v1/github/repos');
        var repos = await response.json();
        if (repos.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5">No repositories managed</td></tr>';
            statusEl.textContent = 'No repositories';
            return;
        }
        var html = '';
        for (var i = 0; i < repos.length; i++) {
            var repo = repos[i];
            html += '<tr>'
                + '<td>' + esc(repo.org) + '/' + esc(repo.name) + '</td>'
                + '<td>' + esc(repo.url || '-') + '</td>'
                + '<td><span class="status-' + escAttr(repo.repo_status) + '">' + esc(repo.repo_status) + '</span></td>'
                + '<td>' + esc(repo.last_synced || '-') + '</td>'
                + '<td class="actions">'
                + '<button onclick="syncRepo(\x27' + escAttr(repo.org) + '\x27, \x27' + escAttr(repo.name) + '\x27)" class="sync-btn">Sync</button>'
                + '<button onclick="deleteRepo(\x27' + escAttr(repo.org) + '\x27, \x27' + escAttr(repo.name) + '\x27)" class="delete-btn">Delete</button>'
                + '</td>'
                + '</tr>';
        }
        tbody.textContent = html;
        statusEl.textContent = repos.length + ' repository(s)';
    } catch (error) {
        console.error('Failed to load repos:', error);
        statusEl.textContent = 'Error loading repositories';
    }
}

async function addRepo() {
    var urlInput = document.getElementById('repo_url');
    var url = urlInput && urlInput.value.trim();
    if (!url) {
        showToast('Please enter a repository URL', 'error');
        return;
    }
    try {
        var response = await fetch('/api/v1/github/repos', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url: url, branch: 'main' })
        });
        var result = await response.json();
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
        var response = await fetch('/api/v1/github/repos/' + encodeURIComponent(org) + '/' + encodeURIComponent(name) + '/sync', {
            method: 'POST'
        });
        var result = await response.json();
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
    if (!confirm('Delete repository ' + org + '/' + name + '?')) return;
    try {
        var response = await fetch('/api/v1/github/repos/' + encodeURIComponent(org) + '/' + encodeURIComponent(name), {
            method: 'DELETE'
        });
        var result = await response.json();
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