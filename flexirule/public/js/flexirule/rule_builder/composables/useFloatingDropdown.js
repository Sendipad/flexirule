import { ref, nextTick } from "vue";

export function useFloatingDropdown(config = {}) {
	const {
		offset = 6,
		viewportPadding = 12,
		minWidth = 220,
		maxWidth = 640,
		maxHeight = 360,
		matchTriggerWidth = true,
	} = config;

	const triggerRef = ref(null);
	const dropdownRef = ref(null);
	const isOpen = ref(false);
	const dropdownStyle = ref({});

	function resolveWidth(rect, viewportWidth) {
		const available = Math.max(180, viewportWidth - viewportPadding * 2);
		const triggerWidth = matchTriggerWidth ? rect.width : minWidth;
		const baseWidth = Math.max(minWidth, triggerWidth);
		return Math.min(Math.max(baseWidth, 180), Math.min(maxWidth, available));
	}

	function updatePosition() {
		if (!triggerRef.value || !isOpen.value) return;

		const rect = triggerRef.value.getBoundingClientRect();
		const viewportWidth = window.innerWidth;
		const viewportHeight = window.innerHeight;
		const width = resolveWidth(rect, viewportWidth);

		const clampLeftMin = viewportPadding;
		const clampLeftMax = Math.max(clampLeftMin, viewportWidth - width - viewportPadding);
		const left = Math.min(Math.max(rect.left, clampLeftMin), clampLeftMax);

		const availableBottom = viewportHeight - rect.bottom - offset - viewportPadding;
		const availableTop = rect.top - offset - viewportPadding;

		// Use actual height if known, otherwise fallback to a sensible default for flipping decision
		const dropdownHeight = dropdownRef.value?.offsetHeight || 0;
		const heightToFit = dropdownHeight || 220;

		// We flip if there's not enough room below AND there's more room above than below
		const openUp = availableBottom < heightToFit && availableTop > availableBottom;

		const effectiveMaxHeight = Math.max(
			180,
			Math.min(maxHeight, openUp ? availableTop : availableBottom)
		);

		let top;
		if (openUp) {
			const h = dropdownHeight
				? Math.min(dropdownHeight, effectiveMaxHeight)
				: effectiveMaxHeight;
			top = rect.top - h - offset;
		} else {
			top = rect.bottom + offset;
		}

		dropdownStyle.value = {
			position: "fixed",
			left: `${left}px`,
			top: `${top}px`,
			width: `${width}px`,
			minWidth: `${Math.min(width, Math.max(minWidth, rect.width))}px`,
			maxWidth: `${Math.min(maxWidth, viewportWidth - viewportPadding * 2)}px`,
			maxHeight: `${effectiveMaxHeight}px`,
			zIndex: 15000,
		};
	}

	function openDropdown() {
		isOpen.value = true;
		nextTick(updatePosition);
		window.addEventListener("scroll", updatePosition, true);
		window.addEventListener("resize", updatePosition);
	}

	function closeDropdown() {
		isOpen.value = false;
		window.removeEventListener("scroll", updatePosition, true);
		window.removeEventListener("resize", updatePosition);
	}

	function toggleDropdown() {
		if (isOpen.value) {
			closeDropdown();
			return;
		}
		openDropdown();
	}

	function cleanup() {
		window.removeEventListener("scroll", updatePosition, true);
		window.removeEventListener("resize", updatePosition);
	}

	return {
		triggerRef,
		dropdownRef,
		isOpen,
		dropdownStyle,
		openDropdown,
		closeDropdown,
		toggleDropdown,
		updatePosition,
		cleanup,
	};
}
