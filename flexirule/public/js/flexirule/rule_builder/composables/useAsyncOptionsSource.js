import { ref, watch } from "vue";

export function useAsyncOptionsSource(fetcher, config = {}) {
	const pageSize = Number(config.pageSize || 40);
	const options = ref([]);
	const loading = ref(false);
	const error = ref("");
	const page = ref(0);
	const hasMore = ref(false);
	const lastQuery = ref("");

	let requestId = 0;

	function dedupe(rows = []) {
		const seen = new Set();
		const out = [];
		for (const row of rows) {
			const key = String(row?.value ?? "");
			if (!key || seen.has(key)) continue;
			seen.add(key);
			out.push(row);
		}
		return out;
	}

	async function run(query = "", { append = false } = {}) {
		const token = ++requestId;
		loading.value = true;
		error.value = "";
		if (!append) {
			page.value = 0;
		}

		try {
			const nextPage = append ? page.value + 1 : 0;
			const result =
				(typeof fetcher === "function"
					? await fetcher({
							query,
							start: nextPage * pageSize,
							page: nextPage,
							pageSize,
						})
					: []) || [];

			if (token !== requestId) return options.value;

			const normalized = dedupe(result);
			options.value = append ? dedupe([...(options.value || []), ...normalized]) : normalized;
			page.value = nextPage;
			lastQuery.value = query;
			hasMore.value = normalized.length >= pageSize;
			return options.value;
		} catch (e) {
			if (token !== requestId) return options.value;
			error.value = e?.message || "Unable to fetch options";
			return options.value;
		} finally {
			if (token === requestId) {
				loading.value = false;
			}
		}
	}

	function reset() {
		requestId += 1;
		options.value = [];
		loading.value = false;
		error.value = "";
		page.value = 0;
		hasMore.value = false;
		lastQuery.value = "";
	}

	async function loadMore() {
		if (loading.value || !hasMore.value) return options.value;
		return run(lastQuery.value, { append: true });
	}

	if (config.dependencies) {
		watch(
			config.dependencies,
			() => {
				reset();
			},
			{ deep: true }
		);
	}

	return {
		options,
		loading,
		error,
		page,
		hasMore,
		lastQuery,
		run,
		loadMore,
		reset,
	};
}
