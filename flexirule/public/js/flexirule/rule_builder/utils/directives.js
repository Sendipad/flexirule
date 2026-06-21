export const fieldRevealDirective = {
	mounted(el, binding) {
		const fieldname = binding.value;
		if (fieldname) {
			el.setAttribute("data-fxr-fieldname", fieldname);
		}
	},
	updated(el, binding) {
		const fieldname = binding.value;
		if (fieldname) {
			el.setAttribute("data-fxr-fieldname", fieldname);
		} else {
			el.removeAttribute("data-fxr-fieldname");
		}
	},
};
