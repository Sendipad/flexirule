/**
 * Wrap Frappe Workspace.show_page so a missing page in an initialized workspace
 * is treated as an invalid route rather than dereferenced by Frappe's renderer.
 *
 * This guard deliberately does not catch exceptions from the original method:
 * legitimate rendering failures must remain visible to callers and Cypress.
 *
 * @param {Function} originalShowPage
 * @returns {Function}
 */
export function guardWorkspaceShowPage(originalShowPage) {
	if (typeof originalShowPage !== "function") {
		throw new TypeError("originalShowPage must be a function");
	}

	return async function guardedShowPage(page) {
		// A missing page cannot be rendered. Avoid calling Frappe's method with
		// an absent argument, which may dereference page.name/page.public.
		if (!page) return;

		const allPages = this?.all_pages;

		// Preserve Frappe's original startup behavior while page lists have not
		// loaded yet. Its standard implementation is already a no-op if empty.
		if (!Array.isArray(allPages) || allPages.length === 0) {
			return originalShowPage.apply(this, arguments);
		}

		// Mirror Frappe v15's page-list selection.
		const pages =
			page.public && Array.isArray(this.public_pages) && this.public_pages.length
				? this.public_pages
				: this.private_pages;

		// If the workspace object is not in the expected shape, preserve the
		// original behavior instead of hiding a structural/runtime error.
		if (!Array.isArray(pages)) {
			return originalShowPage.apply(this, arguments);
		}

		const currentPage = pages.find((candidate) => candidate?.title === page.name);
		if (!currentPage) {
			// An initialized workspace has no matching page for this route.
			// Do not call the original method: Frappe dereferences current_page.
			return;
		}

		// Do not catch errors here. Errors from a real page render must propagate.
		return originalShowPage.apply(this, arguments);
	};
}
