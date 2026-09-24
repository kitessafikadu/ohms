/** @odoo-module **/

import { session } from "@web/session";

export function cleanBackendHref(href) {
    const prefix = session.web_custom_url?.router_prefix;
    if (!href || (prefix !== "/" && prefix !== "")) {
        return href;
    }
    if (href === "/odoo" || href === "/odoo/") {
        return "/";
    }
    if (href.startsWith("/odoo/")) {
        const stripped = href.substring(5);
        return stripped.startsWith("/") ? stripped : `/${stripped}`;
    }
    if (href.startsWith("/odoo?") || href.startsWith("/odoo#")) {
        return href.substring(5) || "/";
    }
    if (href === "/web") {
        return "/";
    }
    if (href.startsWith("/web?") || href.startsWith("/web#")) {
        return href.substring(4) || "/";
    }
    return href;
}
