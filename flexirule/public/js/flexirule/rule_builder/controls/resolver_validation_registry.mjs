/**
 * Tracks mounted resolver controls so their asynchronous validation participates
 * in the owning FlexValueControl's save validation.
 */
export function createResolverValidationRegistry() {
	const validators = new Set();

	return {
		register(validator) {
			if (typeof validator !== "function") return () => {};
			validators.add(validator);
			let registered = true;
			return () => {
				if (!registered) return;
				registered = false;
				validators.delete(validator);
			};
		},

		async validate() {
			const results = await Promise.all(
				Array.from(validators, async (validator) => {
					try {
						return await validator();
					} catch (error) {
						return {
							valid: false,
							errors: [error?.message || "Nested resolver validation failed."],
						};
					}
				})
			);
			const errors = results.flatMap((result) =>
				result?.valid === false
					? result.errors || ["Nested resolver validation failed."]
					: []
			);
			return { valid: errors.length === 0, errors };
		},
	};
}
