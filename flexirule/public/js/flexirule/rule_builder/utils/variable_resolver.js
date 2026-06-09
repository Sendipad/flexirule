/**
 * Resolves available variables based on global variables and a stack of local scopes.
 *
 * @param {Object} params
 * @param {Array} params.globalVariables - List of global variable options.
 * @param {Array} params.scopeStack - Stack of local scopes, e.g. [{ iterator: 'i', iterable: 'vars.items' }].
 * @returns {Array} - Merged list of available variables with local scopes having priority.
 */
export function resolveAvailableVariables({ globalVariables = [], scopeStack = [] }) {
	const roots = [...globalVariables];

	// Process scope stack from bottom to top (outermost to innermost)
	// so that innermost (nearest) scopes are added last and can be moved to the top of the list.
	scopeStack.forEach(({ iterator, iterable }) => {
		if (!iterator) return;

		// 1. Resolve children properties of the collection and map them to the iterator
		if (iterable) {
			const iterableSuffix = String(iterable).split(".").pop();
			const prefix1 = iterable + ".";
			const prefix2 = iterableSuffix + ".";

			const childFields = roots.filter((r) => {
				const val = r.value || r;
				return (
					typeof val === "string" && (val.startsWith(prefix1) || val.startsWith(prefix2))
				);
			});

			// Add iterator child fields
			childFields.forEach((child) => {
				const val = child.value || child;
				let suffix = val;
				if (val.startsWith(prefix1)) suffix = val.slice(prefix1.length);
				else if (val.startsWith(prefix2)) suffix = val.slice(prefix2.length);

				const iterValue = `${iterator}.${suffix}`;
				// If it already exists in roots, we might want to "shadow" it or just skip
				// For autocomplete, we want it at the top if it's the nearest scope.
				const existingIdx = roots.findIndex((r) => (r.value || r) === iterValue);
				if (existingIdx !== -1) {
					roots.splice(existingIdx, 1);
				}

				roots.unshift({
					...child,
					label: `${iterator}.${suffix} (${child.label || suffix})`,
					value: iterValue,
					is_iterator_child: true,
					is_iterator: false,
					is_loop_scoped: true,
				});
			});
		}

		// 2. Always add the root iterator variable itself
		const existingIterIdx = roots.findIndex((r) => (r.value || r) === iterator);
		if (existingIterIdx !== -1) {
			roots.splice(existingIterIdx, 1);
		}
		roots.unshift({
			label: iterator,
			value: iterator,
			is_iterator: true,
			is_loop_scoped: true,
		});
	});

	return roots;
}
