const API_BASE = "/api/v1/qdrant";

/**
 * Unified helper for Qdrant API actions.
 * Handles the structure required by QdrantActionRequest.
 */
async function qdrantAction(action, payload = {}) {
	// The backend expects the 'action' discriminator to be present inside the payload object
	const enrichedPayload = { action, ...payload };

	const response = await fetch(API_BASE, {
		method: "POST",
		headers: { "Content-Type": "application/json" },
		body: JSON.stringify({ action, payload: enrichedPayload }),
	});

	if (!response.ok) {
		const errorText = await response.text();
		throw new Error(
			`API error (${response.status}): ${errorText || response.statusText}`,
		);
	}

	const data = await response.json();

	// Handle both success and api_success patterns
	if (data.status !== "success" && data.status !== "api_success") {
		throw new Error(data.message || "Action failed");
	}

	return data;
}

/**
 * Fetches the status of the Qdrant service.
 */
async function _getQdrantStatus() {
	const response = await fetch(`${API_BASE}/status`);
	if (!response.ok) throw new Error("Failed to fetch Qdrant status");
	return await response.json();
}

/**
 * Lists all collections in the database.
 */
async function _listCollections() {
	const result = await qdrantAction("collection_management", {
		operation: "list",
	});
	return result.data || [];
}

/**
 * Gets details for a specific collection.
 */
async function _getCollectionDetails(name) {
	const result = await qdrantAction("collection_management", {
		operation: "get",
		collection_name: name,
	});
	return result.data;
}

/**
 * Deletes a collection from the database.
 */
async function _deleteCollection(name) {
	await qdrantAction("collection_management", {
		operation: "delete",
		collection_name: name,
	});
}

/**
 * Re-creates a collection with default configuration.
 */
async function _createCollection(name, vectorSize = 384) {
	await qdrantAction("collection_management", {
		operation: "create",
		collection_name: name,
		config: { vector_size: vectorSize },
	});
}
