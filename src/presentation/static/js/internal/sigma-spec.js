(() => {
	const API_BASE = "/api/v1/spec";
	let currentRepo = null;
	let detailContainer = null;

	function formatDate(isoString) {
		if (!isoString) return "Unknown";
		try {
			const date = new Date(isoString);
			return date.toLocaleDateString() + " " + date.toLocaleTimeString();
		} catch {
			return "Unknown";
		}
	}

	async function loadRepos() {
		try {
			const response = await fetch(API_BASE + "/repos");
			if (!response.ok) throw new Error("API error");
			const data = await response.json();
			const repos = Array.isArray(data) ? data : data.repos || [];
			const container = document.getElementById("repos-list");
			const prompt = document.getElementById("select-repo-prompt");
			if (!container) return;

			if (repos.length === 0) {
				container.innerHTML = "<p>No repositories managed</p>";
				if (prompt) prompt.style.display = "none";
				return;
			}

			if (prompt) prompt.style.display = "block";

			container.innerHTML = repos
				.map((repo) =>
					[
						'<div class="repo-card">',
						"  <h3>" + escHtml(repo.org) + "/" + escHtml(repo.name) + "</h3>",
						"  <p>Last commit: " +
							escHtml(formatDate(repo.last_commit)) +
							"</p>",
						'  <div class="repo-actions">',
						'    <button data-action="sync" data-org="' +
							escAttr(repo.org) +
							'" data-name="' +
							escAttr(repo.name) +
							'" class="btn btn-sm ' +
							escAttr(repo.sync_class || "btn-unknown") +
							'">Sync</button>',
						'    <button data-action="browse" data-org="' +
							escAttr(repo.org) +
							'" data-name="' +
							escAttr(repo.name) +
							'" class="btn btn-sm btn-secondary">Browse</button>',
						'    <button data-action="delete" data-org="' +
							escAttr(repo.org) +
							'" data-name="' +
							escAttr(repo.name) +
							'" class="btn btn-danger btn-sm">Delete</button>',
						"  </div>",
						"</div>",
					].join("\n"),
				)
				.join("\n");
		} catch (error) {
			console.error("Failed to load repos:", error);
			const container = document.getElementById("repos-list");
			if (container) container.innerHTML = "<p>Error loading repositories</p>";
		}
	}

	document.getElementById("repos-list").addEventListener("click", (e) => {
		const btn = e.target.closest("button[data-action]");
		if (!btn) return;
		const org = btn.dataset.org;
		const name = btn.dataset.name;
		switch (btn.dataset.action) {
			case "sync":
				syncRepo(org, name);
				break;
			case "browse":
				openRepoDetail(org, name);
				break;
			case "delete":
				deleteRepo(org, name);
				break;
		}
	});

	async function openRepoDetail(org, name) {
		currentRepo = { org: org, name: name };
		document.getElementById("selected-repo-name").textContent =
			org + "/" + name;

		if (detailContainer) {
			detailContainer.destroy();
			detailContainer = null;
		}

		const tree = document.getElementById("spec-tree");
		tree.innerHTML = '<p class="dir-browser-empty">Loading directories...</p>';

		document.getElementById("repo-detail").style.display = "block";
		document.getElementById("spec-count").textContent = "";

		detailContainer = new DirBrowser("spec-tree", {
			mode: "tree",
			endpoints: {
				list: API_BASE + "/repos/" + org + "/" + name + "/tree",
				save: API_BASE + "/repos/" + org + "/" + name + "/select-dirs",
				selected: API_BASE + "/repos/" + org + "/" + name + "/selected-dirs",
			},
			saveMethod: "POST",
			saveOnChange: true,
			selectedCountEl: "spec-count",
		});
		detailContainer.load();
	}

	function closeRepoDetail() {
		if (detailContainer) {
			detailContainer.destroy();
			detailContainer = null;
		}
		document.getElementById("repo-detail").style.display = "none";
		currentRepo = null;
		document.getElementById("spec-tree").innerHTML =
			'<p class="dir-browser-empty">Loading directories...</p>';
	}

	function closeModal() {
		document.getElementById("add-repo-modal").style.display = "none";
		document.getElementById("add-repo-form").reset();
	}

	async function syncRepo(org, name) {
		if (!confirm("Sync repository " + org + "/" + name + "?")) return;
		try {
			const response = await fetch(
				API_BASE + "/repos/" + org + "/" + name + "/sync",
				{
					method: "POST",
					headers: { "Content-Type": "application/json" },
				},
			);
			const result = await response.json();
			if (result.success) {
				alert("Syncing repository...");
				loadRepos();
			} else {
				alert(result.error || "Failed to sync");
			}
		} catch {
			alert("Failed to sync repository");
		}
	}

	async function deleteRepo(org, name) {
		if (!confirm("Delete repository " + org + "/" + name + "?")) return;
		try {
			const response = await fetch(API_BASE + "/repos/" + org + "/" + name, {
				method: "DELETE",
			});
			const result = await response.json();
			if (result.success) {
				if (
					currentRepo &&
					currentRepo.org === org &&
					currentRepo.name === name
				) {
					closeRepoDetail();
				}
				loadRepos();
			} else {
				alert(result.error || "Failed to delete");
			}
		} catch {
			alert("Failed to delete repository");
		}
	}

	const DISCOVERY_WORKERS = [
		"github_discovery",
		"local_discovery",
		"sigmaref_discovery",
		"spec_discovery",
	];
	let _discoveryPollInterval = null;

	function isWorkerActive(status) {
		return status === "running" || status === "waiting";
	}

	async function pollWorkerStatus(workerType) {
		try {
			const resp = await fetch("/api/v1/dispatcher/status/" + workerType);
			if (!resp.ok) return null;
			return await resp.json();
		} catch {
			return null;
		}
	}

	async function checkAnyWorkerActive() {
		const results = await Promise.all(DISCOVERY_WORKERS.map(pollWorkerStatus));
		return results.some((s) => s && isWorkerActive(s.status));
	}

	function setButtonText(id, text) {
		const btn = document.getElementById(id);
		if (btn) btn.textContent = text;
	}

	function setButtonsDisabled(disabled) {
		["list-document-btn", "index-btn"].forEach((id) => {
			const btn = document.getElementById(id);
			if (btn) btn.disabled = disabled;
		});
	}

	function stopDiscoveryPolling() {
		if (_discoveryPollInterval) {
			clearInterval(_discoveryPollInterval);
			_discoveryPollInterval = null;
		}
	}

	function startDiscoveryPolling(onIdle) {
		stopDiscoveryPolling();
		setButtonsDisabled(true);
		_discoveryPollInterval = setInterval(async () => {
			const results = await Promise.all(
				DISCOVERY_WORKERS.map(pollWorkerStatus),
			);

			const gh = results[0],
				local = results[1],
				sr = results[2],
				spec = results[3];
			const ghActive = gh && isWorkerActive(gh.status);
			const localActive = local && isWorkerActive(local.status);
			const srActive = sr && isWorkerActive(sr.status);
			const specActive = spec && isWorkerActive(spec.status);
			const anyActive = ghActive || localActive || srActive || specActive;

			if (!anyActive) {
				stopDiscoveryPolling();
				setButtonsDisabled(false);
				setButtonText("list-document-btn", "List document");
				setButtonText("index-btn", "Index");
				if (onIdle) onIdle();
				return;
			}

			if (ghActive || localActive) {
				const src = ghActive ? gh : local;
				const pct =
					src.progress_percent > 0
						? Math.round(src.progress_percent)
						: undefined;
				setButtonText(
					"list-document-btn",
					pct !== undefined ? "Scanning " + pct + "%.." : "Scanning...",
				);
			} else {
				setButtonText("list-document-btn", "List document");
			}
		}, 2000);
	}

	async function checkRunningWorkersOnLoad() {
		const active = await checkAnyWorkerActive();
		if (active) {
			startDiscoveryPolling(() => {
				loadRepos();
			});
		}
	}

	document.getElementById("add-repo-btn").addEventListener("click", () => {
		document.getElementById("add-repo-modal").style.display = "block";
	});

	document
		.getElementById("modal-cancel-btn")
		.addEventListener("click", closeModal);

	document
		.getElementById("close-detail-btn")
		.addEventListener("click", closeRepoDetail);

	document
		.getElementById("sync-all-btn")
		.addEventListener("click", async function () {
			this.disabled = true;
			this.textContent = "Syncing...";
			try {
				const response = await fetch(API_BASE + "/repos/sync-all", {
					method: "POST",
					headers: { "Content-Type": "application/json" },
				});
				const result = await response.json();
				if (result.success) {
					alert("Sync started for all repositories...");
					loadRepos();
				} else {
					alert(result.error || "Failed to sync all");
				}
			} catch {
				alert("Failed to sync all repositories");
			} finally {
				this.disabled = false;
				this.textContent = "Sync All";
			}
		});

	document.getElementById("refresh-btn").addEventListener("click", loadRepos);

	document
		.getElementById("list-document-btn")
		.addEventListener("click", async () => {
			setButtonText("list-document-btn", "Scanning...");
			try {
				const response = await fetch("/api/v1/files/list", {
					method: "POST",
				});
				const result = await response.json();
				if (result.success) {
					startDiscoveryPolling(() => {
						loadRepos();
					});
				} else {
					setButtonText("list-document-btn", "List document");
				}
			} catch {
				setButtonText("list-document-btn", "List document");
			}
		});

	document.getElementById("index-btn").addEventListener("click", async () => {
		setButtonText("index-btn", "Indexing...");
		try {
			const response = await fetch("/api/v1/qdrant", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({
					action: "index_all",
					payload: {
						action: "index_all",
						group: "spec",
					},
				}),
			});
			const result = await response.json();
			if (result.status === "success") {
				var processed = 0;
				if (result.data && result.data.results && result.data.results[0]) {
					processed = result.data.results[0].processed || 0;
				}
				alert("Indexed " + processed + " document(s) successfully");
			} else {
				alert(result.message || "Index failed");
			}
		} catch {
			alert("Index request failed");
		} finally {
			setButtonText("index-btn", "Index");
		}
	});

	document
		.getElementById("add-repo-form")
		.addEventListener("submit", async (e) => {
			e.preventDefault();
			const url = document.getElementById("repo-url").value.trim();
			const branch =
				document.getElementById("repo-branch").value.trim() || "main";

			if (!url) {
				alert("Please enter a repository");
				return;
			}

			let repoUrl = url;
			if (!url.startsWith("http") && !url.endsWith(".git")) {
				repoUrl = "https://github.com/" + url + ".git";
			} else if (!url.endsWith(".git")) {
				repoUrl = url + ".git";
			}

			try {
				const response = await fetch(API_BASE + "/repos", {
					method: "POST",
					headers: { "Content-Type": "application/json" },
					body: JSON.stringify({ url: repoUrl, branch: branch }),
				});
				const result = await response.json();
				if (result.success) {
					closeModal();
					loadRepos();
				} else {
					alert(result.error || "Failed to add repository");
				}
			} catch {
				alert("Failed to add repository");
			}
		});

	loadRepos();
	checkRunningWorkersOnLoad();
})();
