/**
 * tgc_focus.js
 *
 * Lightweight cross-component signal that lets InputPanel (or any sibling)
 * insert an expression into whichever TextGeneratorControl was last focused —
 * without touching the Pinia store or adding prop-drilling.
 *
 * Usage:
 *   TextGeneratorControl  → calls setActiveTGC(insertFn)  on focus
 *                         → calls clearActiveTGC(insertFn) on blur/unmount
 *   InputPanel (or other) → calls insertIntoActiveTGC(path) on click
 */

/** @type {((path: string) => void) | null} */
let _activeFn = null;

export function setActiveTGC(fn) {
	_activeFn = fn;
}

export function clearActiveTGC(fn) {
	// Only clear if the currently registered fn is ours (avoid race on tab switch)
	if (_activeFn === fn) _activeFn = null;
}

/**
 * Insert a Jinja expression into the currently focused TextGeneratorControl.
 * Returns true if a TGC was active, false if nothing is focused.
 */
export function insertIntoActiveTGC(path) {
	if (_activeFn) {
		_activeFn(path);
		return true;
	}
	return false;
}
