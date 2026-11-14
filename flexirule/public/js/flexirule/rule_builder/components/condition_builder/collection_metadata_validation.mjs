/**
 * Child-table condition metadata is required to select the correct DocType.
 * An unresolved child schema must never fall back to the parent DocType.
 */
export function getResolvedCollectionDocType(collectionNode, metadataById) {
	const metadata = metadataById?.get(collectionNode?.id);
	return metadata?.status === "loaded" && metadata.childDocType
		? metadata.childDocType
		: "";
}

export function getCollectionMetadataIssues(tree, metadataById) {
	const issues = [];
	const visit = (node) => {
		if (!node || typeof node !== "object") return;
		if (node.type === "collection" && node.collection) {
			const scope = node.source?.scope || String(node.collection).split(".")[0];
			if (scope !== "vars") {
				const metadata = metadataById?.get(node.id);
				if (metadata?.status !== "loaded" || !metadata.childDocType) {
					issues.push(
						metadata?.status === "loading"
							? "Waiting for the selected child table DocType metadata to load."
							: metadata?.error ||
								"Child table DocType metadata is unavailable. Retry metadata loading before saving."
					);
				}
			}
		}
		if (Array.isArray(node.children)) node.children.forEach(visit);
	};
	visit(tree);
	return [...new Set(issues)];
}
