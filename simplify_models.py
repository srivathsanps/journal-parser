# Simplify models display - remove timestamps
import re

# Read the file
with open(r'c:\Users\Admin\Desktop\Journal Parser\static\script.js', 'r', encoding='utf-8') as f:
    content = f.read()

# Find and replace the models display section
# We need to replace from line 574 to 610 (the entire map function)
old_section = """        modelsUl.innerHTML = sortedModels.map(modelName => {
            const isPrimary = modelName === primaryModel;

            // Find timeline events for this model
            const modelEvents = timeline.filter(event =>
                event.text && event.text.includes(modelName)
            );

            // Find open and close events
            const openEvent = modelEvents.find(e =>
                e.type === 'model_open' || e.type === 'file_open' ||
                (e.description && e.description.toLowerCase().includes('open'))
            );
            const closeEvent = modelEvents.find(e =>
                e.type === 'document_close' ||
                (e.description && e.description.toLowerCase().includes('close'))
            );

            // Build timeline info string with formatted timestamps
            let timelineInfo = '';
            if (openEvent) {
                const formattedTime = formatTimestamp(openEvent.timestamp) || 'N/A';
                timelineInfo += `<br><span style="color: #10b981; font-size: 0.85em;">📂 Opened: ${escapeHtml(formattedTime)}</span>`;
            }
            if (closeEvent) {
                const formattedTime = formatTimestamp(closeEvent.timestamp) || 'N/A';
                timelineInfo += `<br><span style="color: #6b7280; font-size: 0.85em;">📁 Closed: ${escapeHtml(formattedTime)}</span>`;
            }

            // Add primary model badge
            const primaryBadge = isPrimary ? '<span style="background: #3b82f6; color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.75em; margin-left: 8px; font-weight: bold;">PRIMARY MODEL</span>' : '';

            return `<li style="margin-bottom: 0.5rem; ${isPrimary ? 'font-weight: 600;' : ''}">${escapeHtml(modelName)}${primaryBadge}${timelineInfo}</li>`;
        }).join('');"""

new_section = """        modelsUl.innerHTML = sortedModels.map(modelName => {
            const isPrimary = modelName === primaryModel;
            
            // Add primary model badge
            const primaryBadge = isPrimary ? '<span style="background: #3b82f6; color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.75em; margin-left: 8px; font-weight: bold;">PRIMARY MODEL</span>' : '';
            
            // Simple display: just model name and badge (no timestamps or metadata)
            return `<li style="margin-bottom: 0.5rem; ${isPrimary ? 'font-weight: 600;' : ''}">${escapeHtml(modelName)}${primaryBadge}</li>`;
        }).join('');"""

# Replace
content = content.replace(old_section, new_section)

# Write back
with open(r'c:\Users\Admin\Desktop\Journal Parser\static\script.js', 'w', encoding='utf-8') as f:
    f.write(content)

print("Models display simplified successfully!")
