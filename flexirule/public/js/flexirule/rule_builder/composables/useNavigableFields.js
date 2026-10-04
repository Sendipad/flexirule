import { ref, computed, watch } from "vue";
import { useMetaStore } from "../stores/useMetaStore";

/**
 * Composable to manage navigable field browsing for Query Records controls.
 * Transforms Frappe DocType metadata into generic ComboBox options with navigation support.
 *
 * @param {Ref<string>|Function|string} rootDoctype - Root DocType name (e.g., "Sales Invoice")
 */
export function useNavigableFields(rootDoctype) {
	const metaStore = useMetaStore();

	const navStack = ref([]);
	const currentFields = ref([]);
	const loading = ref(false);

	const rootDt = computed(() => {
		if (typeof rootDoctype === "function") return rootDoctype();
		if (rootDoctype && typeof rootDoctype === "object" && "value" in rootDoctype) {
			return rootDoctype.value;
		}
		return rootDoctype || "";
	});

	const currentContext = computed(() => {
		if (navStack.value.length === 0) return null;
		return navStack.value[navStack.value.length - 1];
	});

	async function loadCurrentContextFields() {
		const ctx = currentContext.value;
		if (!ctx || !ctx.doctype) {
			currentFields.value = [];
			return;
		}

		loading.value = true;
		try {
			await metaStore.fetch_metadata(ctx.doctype);
			const rawFields = metaStore.doc_meta[ctx.doctype] || [];

			const options = [];
			for (const f of rawFields) {
				const isLink = f.fieldtype === "Link" && f.options;
				const isTable =
					(f.fieldtype === "Table" || f.fieldtype === "Table MultiSelect") && f.options;
				const isNavigable = isLink || isTable;

				const fieldPath = ctx.pathPrefix ? `${ctx.pathPrefix}.${f.fieldname}` : f.fieldname;

				let navType = null;
				if (isLink) navType = "link";
				if (isTable) navType = "table";

				const isSpecial = f.fieldname === "docstatus" || f.fieldname === "name" || f.is_std;

				options.push({
					value: fieldPath,
					label: `${f.original_label || f.label || f.fieldname} (${f.fieldname})`,
					description: isNavigable ? `${f.fieldtype} → ${f.options}` : f.fieldtype || "",
					fieldname: f.fieldname,
					fieldtype: f.fieldtype,
					icon: isNavigable
						? isLink
							? "fa fa-link"
							: "fa fa-table"
						: isSpecial
						? "fa fa-asterisk"
						: "fa fa-columns",
					navigable: isNavigable,
					navType,
					targetDoctype: f.options,
					raw: {
						...f,
						navigable: isNavigable,
						navType,
						targetDoctype: f.options,
						fieldPath,
					},
				});
			}

			currentFields.value = options;
		} catch (e) {
			console.warn("useNavigableFields: Failed to load fields for context", ctx, e);
			currentFields.value = [];
		} finally {
			loading.value = false;
		}
	}

	async function resetStack() {
		const dt = rootDt.value;
		if (!dt) {
			navStack.value = [];
			currentFields.value = [];
			return;
		}

		navStack.value = [
			{
				doctype: dt,
				fieldname: "",
				label: dt,
				pathPrefix: "",
			},
		];
		await loadCurrentContextFields();
	}

	async function handleNavigate(option) {
		const raw = option.raw || option;
		if (!raw || !raw.navigable || !raw.targetDoctype) return;

		const currentPrefix = currentContext.value?.pathPrefix || "";
		const nextPrefix =
			raw.fieldPath || (currentPrefix ? `${currentPrefix}.${raw.fieldname}` : raw.fieldname);

		navStack.value.push({
			doctype: raw.targetDoctype,
			fieldname: raw.fieldname,
			label: raw.original_label || raw.label || raw.fieldname || raw.targetDoctype,
			pathPrefix: nextPrefix,
		});

		await loadCurrentContextFields();
	}

	async function handleBack(idx) {
		if (idx < 0 || idx >= navStack.value.length) return;
		navStack.value = navStack.value.slice(0, idx + 1);
		await loadCurrentContextFields();
	}

	watch(
		() => rootDt.value,
		async (newDt) => {
			if (newDt) {
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
		handleNavigate,
		handleBack,
	};
}
