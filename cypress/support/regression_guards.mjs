/**
 * Shared regression guard patterns and matchers for Cypress UI tests.
 */
export const REGRESSION_CONSOLE_PATTERN =
	/could not find grid field|grid field.*not found|cannot set property hasResolvedOutputSchema/i;

/**
 * Checks whether a console message matches a known Rule Builder regression.
 *
 * @param {string} message
 * @returns {boolean}
 */
export function isConsoleRegressionMessage(message) {
	if (!message || typeof message !== "string") return false;
	return REGRESSION_CONSOLE_PATTERN.test(message);
}
