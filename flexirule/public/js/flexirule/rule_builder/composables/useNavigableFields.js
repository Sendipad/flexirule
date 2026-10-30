import { ref, computed, watch } from "vue";
import { useMetaStore } from "../stores/useMetaStore";

/**
 * Manage navigable field browsing for Query Records controls.
 *
 * Metadata requests can overlap when a DocType, selected path, or navigation
 * target changes quickly. A monotonically increasing generation prevents any
 * older request from overwriting state produced by a newer user action.
 */
export function useNavigableFields(rootDoctype, selectedValue = null) {
	const metaStore = useMetaStore();
	const navStack = ref([]);
	const currentFields = ref([]);
	const loading = ref(false);
	let requestGeneration = 0;

	const rootDt = computed(() => {
		if (typeof rootDoctype === "function") return rootDoctype();
		if (rootDoctype && typeof rootDoctype === "object" && "value" in rootDoctype) {
			return rootDoctype.value;
		}
		return rootDoctype || "";
	});

	const targetValue = computed(() => {
		if (typeof selectedValue === "function") return selectedValue();
		if (selectedValue && typeof selectedValue === "object" && "value" in selectedValue) {
			return selectedValue.value;
		}
		return selectedValue || "";
	});

	const currentContext = computed(() => {
		if (navStack.value.length === 0) return null;
		return navStack.value[navStack.value.length - 1];
	});

	function isCurrentRequest(generation) {
		return generation === requestGeneration;
	}

	function clearState(generation) {
		if (!isCurrentRequest(generation)) return;
		currentFields.value = [];
		loading.value = false;
	}

	async function loadCurrentContextFields(generation = requestGeneration) {
		const ctx = currentContext.value;
		if (!ctx || !ctx.doctype) {
			clearState(generation);
			return;
		}

		if (isCurrentRequest(generation)) loading.value = true;
		try {
			await metaStore.fetch_metadata(ctx.doctype);
			if (!isCurrentRequest(generation)) return;

			const latestContext = currentContext.value;
			if (
				!latestContext ||
				latestContext.doctype !== ctx.doctype ||
				latestContext.pathPrefix !== ctx.pathPrefix
			) {
				return;
			}

			const rawFields = metaStore.doc_meta[ctx.doctype] || [];
			const options = [];
			for (const field of rawFields) {
				const isLink = field.fieldtype === "Link" && field.options;
				const isTable =
					(field.fieldtype === "Table" || field.fieldtype === "Table MultiSelect") &&
					field.options;
				const isNavigable = isLink || isTable;
				const fieldPath = ctx.pathPrefix
					? `${ctx.pathPrefix}.${field.fieldname}`
					: field.fieldname;

				let navType = null;
				if (isLink) navType = "link";
				if (isTable) navType = "table";

				const isSpecial =
					field.fieldname === "docstatus" || field.fieldname === "name" || field.is_std;
				const rawLabel = field.original_label || field.label || field.fieldname;
				const translatedLabel = typeof window.__ === "function" ? __(rawLabel) : rawLabel;

				options.push({
					value: fieldPath,
					label: `${translatedLabel} (${field.fieldname})`,
					description: isNavigable
						? `${field.fieldtype} → ${field.options}`
						: field.fieldtype || "",
					fieldname: field.fieldname,
					fieldtype: field.fieldtype,
					icon: isNavigable
						? isLink
							? "fa fa-link"
							: "fa fa-table"
						: isSpecial
							? "fa fa-asterisk"
							: "fa fa-columns",
					navigable: isNavigable,
					navType,
					targetDoctype: field.options,
					raw: {
						...field,
						navigable: isNavigable,
						navType,
						targetDoctype: field.options,
						fieldPath,
					},
				});
			}
			if (isCurrentRequest(generation)) currentFields.value = options;
		} catch (error) {
			if (isCurrentRequest(generation)) {
				console.warn("useNavigableFields: Failed to load fields for context", ctx, error);
				currentFields.value = [];
			}
		} finally {
			if (isCurrentRequest(generation)) loading.value = false;
		}
	}

	async function syncStackToValue(value) {
		const generation = ++requestGeneration;
		const doctype = rootDt.value;
		if (!doctype) {
			navStack.value = [];
			clearState(generation);
			return;
		}

		const valueString = String(value || "").trim();
		const root = {
			doctype,
			fieldname: "",
			label: doctype,
			pathPrefix: "",
		};
		if (!valueString || !valueString.includes(".")) {
			navStack.value = [root];
			await loadCurrentContextFields(generation);
			return;
		}

		const parts = valueString.split(".");
		let currentDoctype = doctype;
		let prefix = "";
		const stack = [root];

		for (let index = 0; index < parts.length - 1; index += 1) {
			if (!isCurrentRequest(generation)) return;
			const part = parts[index];
			try {
				await metaStore.fetch_metadata(currentDoctype);
				if (!isCurrentRequest(generation)) return;
				const rawFields = metaStore.doc_meta[currentDoctype] || [];
				const matchField = rawFields.find((field) => field.fieldname === part);
				if (!matchField || !matchField.options) break;

				prefix = prefix ? `${prefix}.${part}` : part;
				currentDoctype = matchField.options;
				const rawLabel =
					matchField.original_label || matchField.label || matchField.fieldname;
				const label = typeof window.__ === "function" ? __(rawLabel) : rawLabel;
				stack.push({
					doctype: currentDoctype,
					fieldname: part,
					label,
					pathPrefix: prefix,
				});
			} catch {
				break;
			}
		}

		if (!isCurrentRequest(generation)) return;
		navStack.value = stack;
		await loadCurrentContextFields(generation);
	}

	async function resetStack() {
		const generation = ++requestGeneration;
		const doctype = rootDt.value;
		if (!doctype) {
			navStack.value = [];
			clearState(generation);
			return;
		}

		navStack.value = [
			{
				doctype,
				fieldname: "",
				label: doctype,
				pathPrefix: "",
			},
		];
		await loadCurrentContextFields(generation);
	}

	async function handleNavigate(option) {
		const raw = option?.raw || option;
		if (!raw || !raw.navigable || !raw.targetDoctype) return;

		const generation = ++requestGeneration;
		const currentPrefix = currentContext.value?.pathPrefix || "";
		const nextPrefix =
			raw.fieldPath || (currentPrefix ? `${currentPrefix}.${raw.fieldname}` : raw.fieldname);

		navStack.value.push({
			doctype: raw.targetDoctype,
			fieldname: raw.fieldname,
			label: raw.original_label || raw.label || raw.fieldname || raw.targetDoctype,
			pathPrefix: nextPrefix,
		});
		await loadCurrentContextFields(generation);
	}

	async function handleBack(index) {
		if (index < 0 || index >= navStack.value.length) return;
		const generation = ++requestGeneration;
		navStack.value = navStack.value.slice(0, index + 1);
		await loadCurrentContextFields(generation);
	}

	watch(
		() => [rootDt.value, targetValue.value],
		async ([newDoctype, newValue]) => {
			if (newDoctype && newValue && String(newValue).includes(".")) {
				await syncStackToValue(newValue);
			} else {
				await resetStack();
			}
		},
		{ immediate: true }
	);

	return {
		navStack,
		currentFields,
		loading,
		currentContext,
		resetStack,
		syncStackToValue,
		handleNavigate,
		handleBack,
	};
}
