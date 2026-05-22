import { computed, ref } from "vue";

export function useResponsiveConfigLayout(breakpoint = 1200, mobileBreakpoint = 768) {
	const activeTab = ref("config");
	const panelScrollState = ref({ input: 0, config: 0, output: 0 });
	const viewportWidth = ref(typeof window !== "undefined" ? window.innerWidth : 1440);

	const isCompact = computed(() => viewportWidth.value < breakpoint);
	const isMobile = computed(() => viewportWidth.value < mobileBreakpoint);
	const tabs = [
		{ key: "input", label: __("Input") },
		{ key: "config", label: __("Config") },
		{ key: "output", label: __("Output") },
	];

	function setActiveTab(tabKey) {
		if (!tabs.find((tab) => tab.key === tabKey)) return;
		activeTab.value = tabKey;
	}

	function updateViewportWidth() {
		viewportWidth.value = window.innerWidth;
	}

	function rememberScroll(panelKey, value) {
		if (!panelKey) return;
		panelScrollState.value = {
			...panelScrollState.value,
			[panelKey]: Number(value || 0),
		};
	}

	function getRememberedScroll(panelKey) {
		return Number(panelScrollState.value?.[panelKey] || 0);
	}

	return {
		activeTab,
		tabs,
		isCompact,
		isMobile,
		updateViewportWidth,
		setActiveTab,
		rememberScroll,
		getRememberedScroll,
	};
}
