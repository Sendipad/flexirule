import { reactive, watch } from "vue";
import { INSPECT_MODIFIER } from "../constants";

const state = reactive({
	isModifierDown: false,
});

// High-visibility logging for debugging
console.log("[field-inspect] Directive module loading...");
console.log("[field-inspect] Configured Modifier:", INSPECT_MODIFIER);

window.addEventListener(
	"keydown",
	(e) => {
		if (e.key === INSPECT_MODIFIER || e.key === "Shift" || e.shiftKey) {
			if (!state.isModifierDown) {
				console.log(`[field-inspect] Modifier ${INSPECT_MODIFIER} is now DOWN`);
			}
			state.isModifierDown = true;
		}
	},
	true
);

window.addEventListener(
	"keyup",
	(e) => {
		if (e.key === INSPECT_MODIFIER || e.key === "Shift") {
			console.log(`[field-inspect] Modifier ${INSPECT_MODIFIER} is now UP`);
			state.isModifierDown = false;
		}
	},
	true
);

window.addEventListener("blur", () => {
	if (state.isModifierDown) {
		console.log("[field-inspect] Modifier reset due to window blur");
		state.isModifierDown = false;
	}
});

const activeInstances = new Set();

watch(
	() => state.isModifierDown,
	(isDown) => {
		activeInstances.forEach((instance) => {
			if (instance._isHovered) {
				instance._updateVisuals(isDown);
			}
		});
	}
);

export default {
	mounted(el, binding) {
		el._isHovered = false;
		el._bindingValue = binding.value;
		el._originalLabel = undefined;
		el._badge = null;

		// console.log("[field-inspect] Directive mounted on element", el, binding.value);

		const updateVisuals = (active) => {
			const name = el._bindingValue?.name;
			if (!name) return;

			// Search for label elements with common FlexiRule classes
			const labelEl = el.querySelector(".fxr-label, .label-area, .control-label, label");
			if (labelEl) {
				if (active) {
					if (el._originalLabel === undefined) el._originalLabel = labelEl.innerText;
					labelEl.innerText = name;
					labelEl.style.fontFamily = "var(--font-mono, monospace)";
					labelEl.style.color = "var(--fxr-accent, #2563eb)";
					labelEl.style.fontWeight = "bold";
				} else {
					if (el._originalLabel !== undefined) {
						labelEl.innerText = el._originalLabel;
						labelEl.style.fontFamily = "";
						labelEl.style.color = "";
						labelEl.style.fontWeight = "";
					}
					el._originalLabel = undefined;
				}
			} else {
				// Labelless / Fallback Badge
				if (active) {
					if (!el._badge) {
						el._badge = document.createElement("div");
						el._badge.className = "fxr-inspect-badge";
						el._badge.innerText = name;
						Object.assign(el._badge.style, {
							position: "absolute",
							top: "2px",
							right: "2px",
							zIndex: "9999",
							fontFamily: "var(--font-mono, monospace)",
							fontSize: "10px",
							color: "var(--fxr-text-muted, #64748b)",
							backgroundColor: "var(--fxr-surface-2, #f1f5f9)",
							padding: "1px 4px",
							borderRadius: "4px",
							border: "1px solid var(--fxr-border-subtle, #e2e8f0)",
							pointerEvents: "none",
							lineHeight: "1.2",
							boxShadow: "0 1px 2px rgba(0,0,0,0.05)",
						});
						if (getComputedStyle(el).position === "static") {
							el.style.position = "relative";
						}
						el.appendChild(el._badge);
					}
				} else {
					if (el._badge) {
						el._badge.remove();
						el._badge = null;
					}
				}
			}
		};

		el._updateVisuals = updateVisuals;

		const handleMouseEnter = () => {
			el._isHovered = true;
			if (state.isModifierDown) updateVisuals(true);
		};

		const handleMouseLeave = () => {
			el._isHovered = false;
			updateVisuals(false);
		};

		const handleClick = (e) => {
			if (state.isModifierDown) {
				const name = el._bindingValue?.name;
				if (!name) return;

				e.preventDefault();
				e.stopPropagation();

				navigator.clipboard.writeText(name).then(() => {
					if (window.frappe?.show_alert) {
						window.frappe.show_alert(
							{
								message: `Copied: ${name}`,
								indicator: "green",
							},
							2
						);
					}
				});
			}
		};

		el.addEventListener("mouseenter", handleMouseEnter);
		el.addEventListener("mouseleave", handleMouseLeave);
		el.addEventListener("click", handleClick, true);

		el._cleanupInspect = () => {
			el.removeEventListener("mouseenter", handleMouseEnter);
			el.removeEventListener("mouseleave", handleMouseLeave);
			el.removeEventListener("click", handleClick, true);
			if (el._badge) el._badge.remove();
			activeInstances.delete(el);
		};

		activeInstances.add(el);
	},
	updated(el, binding) {
		el._bindingValue = binding.value;
		if (el._isHovered && state.isModifierDown) {
			el._updateVisuals(true);
		}
	},
	unmounted(el) {
		if (el._cleanupInspect) el._cleanupInspect();
	},
};
