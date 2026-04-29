export function copyText(text) {
	if (!text) return;
	
	// Try native API first
	if (navigator?.clipboard && window.isSecureContext) {
		navigator.clipboard.writeText(text).then(() => {
			if (window.frappe) {
				frappe.show_alert({ message: __("Copied to clipboard"), indicator: "blue" }, 2);
			}
		}).catch(() => {
			fallbackCopy(text);
		});
	} else {
		fallbackCopy(text);
	}
}

function fallbackCopy(text) {
	const textArea = document.createElement("textarea");
	textArea.value = text;
	textArea.style.position = "fixed";
	textArea.style.left = "-9999px";
	textArea.style.top = "0";
	document.body.appendChild(textArea);
	textArea.focus();
	textArea.select();
	try {
		document.execCommand("copy");
		if (window.frappe) {
			frappe.show_alert({ message: __("Copied to clipboard"), indicator: "blue" }, 2);
		}
	} catch (err) {
		console.error("Copy failed", err);
	}
	document.body.removeChild(textArea);
}
