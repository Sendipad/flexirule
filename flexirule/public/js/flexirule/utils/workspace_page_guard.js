/**
 * Narrow guard around Frappe v15 Workspace.show_page.
 *
 * Frappe's implementation assumes the requested page exists in the selected
 * workspace list once all workspace pages have loaded. Custom Desk routes can
 * be passed through Workspace.show_page even though they are not workspace
 * pages, which leaves Frappe dereferencing a missing current_page.
 *
 * Only skip that specific missing-page lookup when the workspace list is
 * populated and the selected page list is valid. Do not catch exceptions from
 * the original implementation: unrelated failures must remain visible.
 */

export function isMissingLoadedWorkspacePage(page, workspace) {
	if (!Array.isArray(workspace?.all_pages) || workspace.all_pages.length === 0) {
		return false;
	}
	if (!page || typeof page.name !== "string" || page.name.length === 0) {
		return false;
	}

	let pages;
	if (page.public) {
		// Preserve Frappe's failure behavior if public_pages is unexpectedly absent.
		if (workspace.public_pages == null) return false;
		pages = workspace.public_pages.length ? workspace.public_pages : workspace.private_pages;
	} else {
		pages = workspace.private_pages;
	}

	// If the selected list is malformed or not initialized, delegate to Frappe
	// rather than hiding that independent state error.
	if (!Array.isArray(pages)) return false;

	return !pages.some((candidate) => candidate?.title === page.name);
}

export function createWorkspaceShowPageGuard(originalShowPage) {
	if (typeof originalShowPage !== "function") {
		throw new TypeError("Workspace.show_page must be a function");
	}

	return async function guardedWorkspaceShowPage(page) {
		if (isMissingLoadedWorkspacePage(page, this)) return;
		return originalShowPage.apply(this, arguments);
	};
}
