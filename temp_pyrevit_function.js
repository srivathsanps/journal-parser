function renderAddinListHierarchical(containerId, items) {
    const container = document.getElementById(containerId);

    if (!items || items.length === 0) {
        container.innerHTML = '<li class="no-items">None</li>';
        return;
    }

    let html = '';

    items.slice(0, 50).forEach(item => {
        const versionText = item.version ? ` <span style="color: #6b7280; font-size: 0.85em;">(v${escapeHtml(item.version)})</span>` : '';

        // Check if this is a parent with children (PyRevitLoader)
        if (item.is_parent && item.children && item.children.length > 0) {
            // Display parent (PyRevitLoader) as a normal bold item
            html += `<li class="pyrevit-parent" title="Line ${item.line}"><strong>${escapeHtml(item.name)}${versionText}</strong></li>`;

            // Display children as indented items
            item.children.forEach(child => {
                const childVersionText = child.version ? ` <span style="color: #6b7280; font-size: 0.85em;">(v${escapeHtml(child.version)})</span>` : '';
                html += `<li class="pyrevit-child" title="Line ${child.line}">\u21b3 ${escapeHtml(truncate(child.name, 60))}${childVersionText}</li>`;
            });
        } else {
            // Regular add-in
            html += `<li title="Line ${item.line}">${escapeHtml(truncate(item.name, 60))}${versionText}</li>`;
        }
    });

    container.innerHTML = html;
}
