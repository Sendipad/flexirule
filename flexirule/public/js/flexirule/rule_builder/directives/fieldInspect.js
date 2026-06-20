import { reactive, watch } from "vue";
import { INSPECT_MODIFIER } from "../constants";

const state = reactive({
	isModifierDown: false,
});

window.addEventListener(
	"keydown",
	(e) => {
		if (e.key === INSPECT_MODIFIER || e.shiftKey) state.isModifierDown = true;
	},
	true
);

window.addEventListener(
	"keyup",
	(e) => {
		if (e.key === INSPECT_MODIFIER) state.isModifierDown = false;
		if (e.key === "Shift") state.isModifierDown = false;
	},
	true
);

const activeInstances = new Set();

// Synchronize all hovered instances when the modifier key is toggled
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
		const { name, label } = binding.value;
		if (!name) return;

		let originalLabel = null;
		let badge = null;
		el._isHovered = false;

		const updateVisuals = (active) => {
			const labelEl = el.querySelector(".fxr-label");
			if (labelEl) {
				if (active) {
					if (originalLabel === null) originalLabel = labelEl.innerText;
					labelEl.innerText = name;
					labelEl.style.fontFamily = "var(--font-mono, monospace)";
					labelEl.style.color = "var(--fxr-accent, #2563eb)";
				} else {
					if (originalLabel !== null) {
						labelEl.innerText = originalLabel;
						labelEl.style.fontFamily = "";
						labelEl.style.color = "";
					}
					originalLabel = null;
				}
			} else {
				// Labelless / Fallback Badge
				if (active) {
					if (!badge) {
						badge = document.createElement("div");
						badge.className = "fxr-inspect-badge";
						badge.innerText = name;
						Object.assign(badge.style, {
							position: "absolute",
							top: "2px",
							right: "2px",
							zIndex: "99",
							fontFamily: "var(--font-mono, monospace)",
							fontSize: "10px",
							color: "var(--text-muted)",
							backgroundColor: "var(--bg-light-gray, var(--gray-100))",
							padding: "1px 4px",
							borderRadius: "4px",
							border: "1px solid var(--border-color)",
							pointerEvents: "none",
							lineHeight: "1.2",
							boxShadow: "0 1px 2px rgba(0,0,0,0.05)",
						});
						if (getComputedStyle(el).position === "static") {
							el.style.position = "relative";
						}
						el.appendChild(badge);
					}
				} else {
					if (badge) {
						badge.remove();
						badge = null;
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
				e.preventDefault();
				e.stopPropagation();

				navigator.clipboard.writeText(name).then(() => {
					window.frappe?.show_alert(
						{
							message: __("Copied fieldname: {0}").replace("{0}", name),
							indicator: "green",
						},
						2
					);
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
			if (badge) badge.remove();
			activeInstances.delete(el);
		};

		activeInstances.add(el);
	},
	unmounted(el) {
		if (el._cleanupInspect) el._cleanupInspect();
	},
};
