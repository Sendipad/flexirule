/**
 * Shared regression guard patterns and matchers for Cypress UI suites and unit tests.
 */
export const REGRESSION_CONSOLE_PATTERN =
	/could not find grid field|grid field.*not found|cannot set property hasResolvedOutputSchema/i;

/**
 * Checks if a console message matches known Rule Builder console regressions.
 *
 * @param {string} message
 * @returns {boolean}
 */
export function isConsoleRegressionMessage(message) {
	if (!message || typeof message !== "string") return false;
	return REGRESSION_CONSOLE_PATTERN.test(message);
}
