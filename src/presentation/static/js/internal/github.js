(() => {
	new RepoBrowser({
		apiBase: "/api/v1/github",
		treeEl: "github-tree",
		countEl: "github-count",
		secondaryBtnId: "download-ref-btn",
		secondaryBtnLabel: "Download Ref",
		discoveryWorkers: [
			"github_discovery",
			"local_discovery",
			"sigmaref_discovery",
		],
		useSelectedEndpoint: false,
		repoCardClass: "card repo-card",
		onSecondaryClick: async () => {
			document.getElementById("download-ref-btn").textContent = "References...";
			const response = await fetch("/api/v1/dispatcher/ask", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({
					worker_type: "sigmaref_discovery",
					task_params: {},
				}),
			});
			if (response.status === 409) return {};
			const result = await response.json();
			if (result.task_id) return result;
			throw new Error(result.error || "No task");
		},
	});

	const indexBtn = document.getElementById("index-btn");
	if (indexBtn) {
		indexBtn.addEventListener("click", async () => {
			indexBtn.textContent = "Indexing...";
			indexBtn.disabled = true;
			try {
				const response = await fetch("/api/v1/qdrant", {
					method: "POST",
					headers: { "Content-Type": "application/json" },
					body: JSON.stringify({
						action: "index_all",
						payload: { action: "index_all", group: "docs" },
					}),
				});
				const result = await response.json();
				if (result.status === "success") {
					const total =
						result.data?.results?.reduce((s, r) => s + (r.processed || 0), 0) ||
						0;
					indexBtn.textContent = `Indexed ${total} docs`;
				} else {
					indexBtn.textContent = "Index failed";
				}
			} catch {
				indexBtn.textContent = "Index failed";
			}
			setTimeout(() => {
				indexBtn.textContent = "Index";
				indexBtn.disabled = false;
			}, 3000);
		});
	}
})();
