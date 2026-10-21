/** @odoo-module **/

// navigator.clipboard is unavailable in non-secure contexts (http, non-localhost domains),
// web_tour tour_helpers_clipboard accesses writeText at load and throws,
// which cascades and prevents @web_tour/tour_interactive/tour_interactive from starting.
// This file runs before the core clipboard file via the manifest before directive.
if (!window.navigator.clipboard) {
    Object.defineProperty(window.navigator, "clipboard", {
        value: {
            writeText: () => Promise.resolve(),
            readText: () => Promise.reject(new Error("Clipboard API unavailable in insecure context")),
        },
        configurable: true,
    });
}
