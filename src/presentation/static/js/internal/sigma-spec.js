(() => {
	new RepoBrowser({
		apiBase: "/api/v1/spec",
		treeEl: "spec-tree",
		countEl: "spec-count",
		secondaryBtnId: "index-btn",
		secondaryBtnLabel: "Index",
		discoveryWorkers: [
			"github_discovery",
			"local_discovery",
			"sigmaref_discovery",
			"spec_discovery",
		],
		useSelectedEndpoint: true,
		secondaryWorkerIndex: -1,
		repoCardClass: "repo-card",
		onSecondaryClick: async () => {
			document.getElementById("index-btn").textContent = "Indexing...";
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
					const total =
						result.data?.results?.reduce((s, r) => s + (r.processed || 0), 0) ||
						0;
					return { indexed: total };
				}
				return {};
			} catch {
				throw new Error("Index request failed");
			}
		},
	});
})();
