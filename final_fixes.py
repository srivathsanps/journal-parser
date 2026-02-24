# Fix 3 issues:
# 1. Timeline: Show model open/close times
# 2. Parser: Exclude "Crash Notify" from fatal errors
# 3. Already done: Session info shows only model names

import re

# ===== FIX 2: Parser - Exclude "Crash Notify" from fatal errors =====
print("Fixing parser...")
with open(r'c:\Users\Admin\Desktop\Journal Parser\parser.py', 'r', encoding='utf-8') as f:
    parser_content = f.read()

# Find and replace the FATAL ERROR pattern to exclude "Crash Notify"
old_pattern = """        # === FATAL ERRORS ===
        for m in re.finditer(r'(?:FATAL\\s+ERROR|Unrecoverable|TaskDialog_Serious_Error)[^\\n]*', content, re.IGNORECASE):"""

new_pattern = """        # === FATAL ERRORS ===
        # Exclude "Crash Notify" which is a plugin action, not a real crash
        for m in re.finditer(r'(?:FATAL\\s+ERROR|Unrecoverable|TaskDialog_Serious_Error)[^\\n]*', content, re.IGNORECASE):
            # Skip if this is just a "Crash Notify" plugin action
            if 'Crash Notify' in m.group(0) or 'CrashNotify' in m.group(0):
                continue"""

parser_content = parser_content.replace(old_pattern, new_pattern)

# Also need to indent the timeline.append block
old_append = """            timeline.append({
                'line': line_num,
                'timestamp': timestamp,
                'type': 'crash',
                'description': 'Fatal Error',
                'text': m.group(0)[:100]
            })"""

new_append = """                timeline.append({
                    'line': line_num,
                    'timestamp': timestamp,
                    'type': 'crash',
                    'description': 'Fatal Error',
                    'text': m.group(0)[:100]
                })"""

parser_content = parser_content.replace(old_append, new_append)

with open(r'c:\Users\Admin\Desktop\Journal Parser\parser.py', 'w', encoding='utf-8') as f:
    f.write(parser_content)

print("✓ Parser fixed - Crash Notify excluded from fatal errors")

# ===== FIX 1: Timeline - Show model open/close times =====
print("\nFixing timeline...")
with open(r'c:\Users\Admin\Desktop\Journal Parser\static\script.js', 'r', encoding='utf-8') as f:
    js_content = f.read()

# Find the timeline rendering section and update it to show times for model events
old_timeline = """        // Show model name prominently if available
        const modelDisplay = modelName ? ` <span class="timeline-model" style="color: #3b82f6; font-weight: 600;">- ${escapeHtml(modelName)}</span>` : '';

        return `
            <div class="timeline-item ${typeClass}">
                <div class="timeline-marker"></div>
                <div class="timeline-content">
                    <div class="timeline-header">
                        <span class="timeline-type">${escapeHtml(event.description)}${modelDisplay}</span>
                        <span class="timeline-line">Line ${event.line}</span>
                    </div>
                    ${timestampDisplay}
                    ${textDisplay}
                </div>
            </div>
        `;"""

new_timeline = """        // Show model name and time for model open/close events
        let modelDisplay = '';
        if (modelName) {
            // For model open/close events, show model name with timestamp
            if (event.type === 'model_open' || event.type === 'file_open' || event.type === 'document_close') {
                const time = event.timestamp ? escapeHtml(event.timestamp) : 'N/A';
                modelDisplay = ` <span class="timeline-model" style="color: #3b82f6; font-weight: 600;">- ${escapeHtml(modelName)} (${time})</span>`;
            } else {
                modelDisplay = ` <span class="timeline-model" style="color: #3b82f6; font-weight: 600;">- ${escapeHtml(modelName)}</span>`;
            }
        }

        return `
            <div class="timeline-item ${typeClass}">
                <div class="timeline-marker"></div>
                <div class="timeline-content">
                    <div class="timeline-header">
                        <span class="timeline-type">${escapeHtml(event.description)}${modelDisplay}</span>
                        <span class="timeline-line">Line ${event.line}</span>
                    </div>
                    ${timestampDisplay}
                    ${textDisplay}
                </div>
            </div>
        `;"""

js_content = js_content.replace(old_timeline, new_timeline)

with open(r'c:\Users\Admin\Desktop\Journal Parser\static\script.js', 'w', encoding='utf-8') as f:
    f.write(js_content)

print("✓ Timeline fixed - Model open/close times now displayed")

print("\n✅ All fixes applied successfully!")
print("\nChanges made:")
print("1. Session Info: Shows only model names (already done)")
print("2. Timeline: Model open/close events now show time")
print("3. Parser: 'Crash Notify' excluded from fatal errors")
