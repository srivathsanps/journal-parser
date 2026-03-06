/**
 * Revit Journal Analyzer - Frontend JavaScript
 * Handles file upload, API communication, and dashboard rendering
 */

// ======================
// DOM Elements
// ======================
const dropArea = document.getElementById('drop-area');
const fileInput = document.getElementById('fileInput');
const fileInfo = document.getElementById('file-info');
const fileName = document.getElementById('file-name');
const clearFileBtn = document.getElementById('clear-file');
const analyzeBtn = document.getElementById('analyzeBtn');
const loading = document.getElementById('loading');
const errorMessage = document.getElementById('error-message');
const uploadSection = document.getElementById('upload-section');
const resultsSection = document.getElementById('results-section');
const newAnalysisBtn = document.getElementById('newAnalysisBtn');
const downloadPdfBtn = document.getElementById('downloadPdfBtn');
const crashBanner = document.getElementById('crash-banner');

// State
let selectedFile = null;
let analysisData = null;

// ======================
// File Selection
// ======================

// Click to select
dropArea.addEventListener('click', () => {
    fileInput.click();
});

fileInput.addEventListener('change', () => {
    if (fileInput.files.length > 0) {
        selectFile(fileInput.files[0]);
    }
});

// Clear file button
clearFileBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    clearSelection();
});

function selectFile(file) {
    selectedFile = file;
    fileName.textContent = file.name;
    fileInfo.classList.remove('hidden');
    dropArea.classList.add('has-file');
    hideError();
}

function clearSelection() {
    selectedFile = null;
    fileInput.value = '';
    fileInfo.classList.add('hidden');
    dropArea.classList.remove('has-file');
}

// ======================
// Drag & Drop
// ======================

['dragenter', 'dragover', 'dragleave', 'drop'].forEach(event => {
    dropArea.addEventListener(event, (e) => {
        e.preventDefault();
        e.stopPropagation();
    });
});

dropArea.addEventListener('dragover', () => {
    dropArea.classList.add('highlight');
});

dropArea.addEventListener('dragleave', () => {
    dropArea.classList.remove('highlight');
});

dropArea.addEventListener('drop', (e) => {
    dropArea.classList.remove('highlight');
    const files = e.dataTransfer.files;
    if (files.length > 0) {
        selectFile(files[0]);
    }
});

// ======================
// Analysis
// ======================

analyzeBtn.addEventListener('click', analyzeFile);

function analyzeFile() {
    if (!selectedFile) {
        showError('Please select a journal file first');
        return;
    }

    hideError();
    showLoading();

    const formData = new FormData();
    formData.append('file', selectedFile);

    // Use XMLHttpRequest for upload progress tracking
    const xhr = new XMLHttpRequest();

    // Reset progress tracking for new upload
    lastProgress = 0;

    // Start smooth progress from 1% to 95% (94 steps)
    let currentProgress = 1;
    const progressInterval = setInterval(() => {
        if (currentProgress < 95) {
            currentProgress += 1;
            const messages = [
                'Uploading file...',
                'Processing journal...',
                'Analyzing journal...',
                'Extracting session info...',
                'Parsing errors...',
                'Processing timeline...',
                'Analyzing add-ins...',
                'Finalizing analysis...'
            ];
            const messageIndex = Math.floor((currentProgress / 95) * messages.length);
            const message = messages[Math.min(messageIndex, messages.length - 1)];
            updateProgress(currentProgress, message);
        }
    }, 200); // Update every 200ms (1% per 200ms = 94 steps * 200ms = ~19 seconds total)

    // Handle response
    xhr.addEventListener('load', () => {
        clearInterval(progressInterval);

        if (xhr.status === 200) {
            // Stay at 95% while processing
            updateProgress(95, 'Preparing results...');

            try {
                console.log('Parsing response...');
                const data = JSON.parse(xhr.responseText);
                console.log('Data parsed successfully');
                analysisData = data;

                // Jump to 100% only when rendering is done
                updateProgress(100, 'Complete!');

                // Increased delay to ensure UI updates before rendering
                setTimeout(() => {
                    console.log('Starting render...');
                    renderResults(data);
                    console.log('Render complete, showing results...');
                    showResults();
                    hideLoading();
                }, 500);
            } catch (error) {
                console.error('Parse error:', error);
                showError('Error parsing server response');
                hideLoading();
            }
        } else {
            try {
                const data = JSON.parse(xhr.responseText);
                showError(data.error || 'Server error');
            } catch {
                showError('Server error');
            }
            hideLoading();
        }
    });

    xhr.addEventListener('error', () => {
        clearInterval(progressInterval);
        showError('Network error occurred');
        hideLoading();
    });

    xhr.open('POST', '/upload');
    xhr.send(formData);
}

let lastProgress = 0; // Track last progress to prevent going backwards

function updateProgress(percent, text) {
    const progressFill = document.getElementById('progress-fill');
    const progressText = document.getElementById('progress-text');
    const progressPercent = document.getElementById('progress-percent');

    // Only update if progress is moving forward
    if (percent >= lastProgress) {
        lastProgress = percent;
        if (progressFill) progressFill.style.width = percent + '%';
        if (progressText) progressText.textContent = text;
        if (progressPercent) progressPercent.textContent = percent + '%';
    }
}

function simulateAnalysisProgress(start, end, durationSeconds, callback) {
    // Progress from 35% to 95% = 60 steps (1% per step)
    const steps = end - start;  // 60 steps for smooth 1% increments
    const stepDuration = 250;  // Fixed 250ms per step for consistent speed
    let current = start;
    let step = 0;

    const messages = [
        'Analyzing journal...',
        'Extracting session info...',
        'Parsing errors...',
        'Processing timeline...',
        'Analyzing add-ins...',
        'Finalizing analysis...'
    ];

    const interval = setInterval(() => {
        step++;
        current = start + step;  // Increment by exactly 1% each time

        // Change message periodically
        const messageIndex = Math.floor((step / steps) * messages.length);
        const message = messages[Math.min(messageIndex, messages.length - 1)];

        updateProgress(current, message);

        if (step >= steps) {
            clearInterval(interval);
            // Stay at 95% until callback completes
            updateProgress(95, 'Preparing results...');
            setTimeout(callback, 200);
        }
    }, stepDuration);
}

// ======================
// UI State Management
// ======================

function showLoading() {
    loading.classList.remove('hidden');
    analyzeBtn.disabled = true;
}

function hideLoading() {
    loading.classList.add('hidden');
    analyzeBtn.disabled = false;
}

function showError(message) {
    errorMessage.textContent = message;
    errorMessage.classList.remove('hidden');
}

function hideError() {
    errorMessage.classList.add('hidden');
}

function showResults() {
    uploadSection.classList.add('hidden');
    resultsSection.classList.remove('hidden');
}

function showUpload() {
    resultsSection.classList.add('hidden');
    uploadSection.classList.remove('hidden');
    clearSelection();
    analysisData = null;
}

// New Analysis button
newAnalysisBtn.addEventListener('click', showUpload);

// ======================
// PDF Download
// ======================

downloadPdfBtn.addEventListener('click', downloadPdf);

async function downloadPdf() {
    if (!analysisData) {
        showError('No analysis data available');
        return;
    }

    downloadPdfBtn.disabled = true;
    downloadPdfBtn.innerHTML = `
        <div class="spinner-small"></div>
        Generating PDF...
    `;

    try {
        const response = await fetch('/generate-pdf', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(analysisData)
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to generate PDF');
        }

        // Download the PDF
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${analysisData.filename || 'journal'}_report.pdf`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);

    } catch (error) {
        console.error('PDF generation error:', error);
        alert('Error generating PDF: ' + error.message);
    } finally {
        downloadPdfBtn.disabled = false;
        downloadPdfBtn.innerHTML = `
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                <polyline points="7 10 12 15 17 10"/>
                <line x1="12" y1="15" x2="12" y2="3"/>
            </svg>
            Export Analysis Report
        `;
    }
}

// ======================
// Results Rendering
// ======================

function renderResults(data) {
    // OPTIMIZATION: Break rendering into chunks to prevent UI freeze

    // Store data globally for access in other functions
    window.analysisData = data;

    // Crash banner - show only for 'Crashed' status
    if (data.summary?.session_status === 'Crashed') {
        crashBanner.classList.remove('hidden');
    } else {
        crashBanner.classList.add('hidden');
    }

    // Render in chunks using requestAnimationFrame
    requestAnimationFrame(() => {
        renderSummaryCards(data);

        requestAnimationFrame(() => {
            renderSessionInfo(data.session_info, data);

            requestAnimationFrame(() => {
                renderIssues(data.errors);
                renderTimeline(data.timeline);

                requestAnimationFrame(() => {
                    renderAddins(data.addins);
                    renderWorkflow(data.workflow);
                    renderKbArticles(data.kb_articles);
                });
            });
        });
    });
}

// ======================
// Summary Cards
// ======================

function renderSummaryCards(data) {
    const summary = data.summary || {};
    const session = data.session_info || {};

    // Determine status display properties
    const status = summary.session_status || 'Unknown';
    const statusConfig = {
        'Crashed': { icon: 'alert-circle', class: 'card-critical' },
        'Active': { icon: 'alert-triangle', class: 'card-warning' },
        'Closed': { icon: 'check-circle', class: 'card-success' }
    };
    const statusProps = statusConfig[status] || { icon: 'help-circle', class: '' };

    const cards = [
        {
            label: 'Status',
            value: status,
            icon: statusProps.icon,
            class: statusProps.class
        },
        {
            label: 'Revit Version',
            value: session.revit_version || 'Unknown',
            icon: 'box'
        },
        {
            label: 'Total Errors',
            value: summary.total_errors || 0,
            icon: 'x-circle',
            class: (summary.total_errors > 0) ? 'card-error' : ''
        },
        {
            label: 'UNSAVED WORK',
            value: summary.unsaved_work_duration || 'N/A',
            icon: 'alert-triangle',
            class: summary.unsaved_work_duration ? 'card-warning' : ''
        },
        {
            label: 'Session Duration',
            value: session.session_duration || 'N/A',
            icon: 'clock'
        }
    ];

    const grid = document.getElementById('summary-grid');
    grid.innerHTML = cards.map(card => `
        <div class="summary-card ${card.class || ''}">
            <div class="card-icon">
                ${getIcon(card.icon)}
            </div>
            <div class="card-content">
                <span class="card-label">${card.label}</span>
                <span class="card-value">${card.value}</span>
            </div>
        </div>
    `).join('');
}

function getIcon(name) {
    const icons = {
        'alert-circle': '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>',
        'check-circle': '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>',
        'box': '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/></svg>',
        'x-circle': '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>',
        'alert-triangle': '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>',
        'file-text': '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>',
        'clock': '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>'
    };
    return icons[name] || '';
}

// ======================
// Session Info
// ======================

function renderSessionInfo(session, fullData) {
    if (!session) return;

    console.log('renderSessionInfo called', session);
    console.log('Full data:', fullData);

    const fields = [
        { label: 'Revit Version', value: session.revit_version },
        { label: 'Build Number', value: session.build_number },
        { label: 'Computer', value: session.computer_name },
        { label: 'Username', value: session.username },
        { label: 'OS', value: session.operating_system },
        { label: 'Available Memory', value: session.ram },
        { label: 'Graphics Card', value: session.graphics_card },
        { label: 'Processor', value: session.processor },
        { label: 'Journal Name', value: session.journal_name },
        { label: 'Session Start', value: session.session_start },
        { label: 'Session End', value: session.session_end },
        { label: 'Session Duration', value: session.session_duration },
        {
            label: 'Session Status',
            value: session.session_status,
            class: session.session_status === 'Crashed' ? 'value-error' :
                session.session_status === 'Active' ? 'value-warning' :
                    'value-success'

        }
    ];

    const grid = document.getElementById('session-info-grid');
    grid.innerHTML = fields
        .filter(f => f.value)
        .map(f => `
            <div class="info-item">
                <span class="info-label">${f.label}</span>
                <span class="info-value ${f.class || ''}">${escapeHtml(f.value)}</span>
            </div>
        `).join('');

    // Primary Model
    const primaryModelSection = document.getElementById('primary-model-section');
    const primaryModelDisplay = document.getElementById('primary-model-display');

    if (session.primary_model) {
        primaryModelSection.classList.remove('hidden');
        primaryModelDisplay.innerHTML = `
            <div class="primary-model-card">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                    <polyline points="14 2 14 8 20 8"/>
                </svg>
                <span class="model-name">${escapeHtml(session.primary_model)}</span>
            </div>
        `;
    } else {
        primaryModelSection.classList.add('hidden');
    }

    // All Models opened with timeline information
    const modelsSection = document.getElementById('models-list');
    const modelsUl = document.getElementById('models-ul');

    console.log('Models section element:', modelsSection);
    console.log('Models opened:', session.models_opened);
    console.log('Primary model:', session.primary_model);

    // Filter to only clean .rvt filenames (reject raw journal text that ends with .rvt)
    const rvtModels = (session.models_opened || []).filter(m =>
        m.toLowerCase().endsWith('.rvt') && m.length <= 150 && !m.includes('::') && !m.includes('0:<')
    );

    if (rvtModels.length > 0) {
        modelsSection.classList.remove('hidden');

        // Sort models: primary model first, then others
        const primaryModel = session.primary_model;
        const sortedModels = [];

        if (primaryModel && rvtModels.includes(primaryModel)) {
            sortedModels.push(primaryModel);
        }

        rvtModels.forEach(model => {
            if (model !== primaryModel) {
                sortedModels.push(model);
            }
        });

        modelsUl.innerHTML = sortedModels.map(modelName => {
            return `<li>${escapeHtml(modelName)}</li>`;
        }).join('');
    } else {
        modelsSection.classList.add('hidden');
    }


    // Unsaved Work Actions
    const unsavedWorkSection = document.getElementById('unsaved-work-section');
    const unsavedActionsCount = document.getElementById('unsaved-actions-count');
    const unsavedDurationDisplay = document.getElementById('unsaved-duration-display');
    const lastSaveTimeDisplay = document.getElementById('last-save-time-display');
    const unsavedActionsList = document.getElementById('unsaved-actions-list');

    console.log('===UNSAVED ACTIONS DEBUG===');
    console.log('session.unsaved_actions:', session.unsaved_actions);
    console.log('session.unsaved_actions_count:', session.unsaved_actions_count);
    console.log('session.unsaved_work_duration:', session.unsaved_work_duration);
    console.log('session.unsaved_work:', session.unsaved_work);

    if (session.unsaved_actions && session.unsaved_actions.length > 0) {
        console.log('✓ Showing unsaved actions section');
        unsavedWorkSection.classList.remove('hidden');
        unsavedActionsCount.textContent = session.unsaved_actions_count || session.unsaved_actions.length;
        unsavedDurationDisplay.textContent = session.unsaved_work_duration || 'N/A';
        lastSaveTimeDisplay.textContent = session.unsaved_work || 'N/A';

        // OPTIMIZATION: Only render first 20 actions initially to avoid browser freeze
        const maxInitial = 20;
        const actionsToShow = session.unsaved_actions.slice(0, maxInitial);

        // Render actions list with formatted timestamps
        unsavedActionsList.innerHTML = actionsToShow.map((action, index) => `
            <div class="unsaved-action-item">
                <div class="action-header">
                    <span class="action-number">#${index + 1}</span>
                    <span class="action-category">${escapeHtml(action.category)}</span>
                    <span class="action-timestamp">${escapeHtml(formatTimestamp(action.timestamp))}</span>
                </div>
                <div class="action-detail">${escapeHtml(action.action)}</div>
                <div class="action-line">Line ${action.line}</div>
            </div>
        `).join('');

        // Add "Show More" button if there are more actions
        if (session.unsaved_actions.length > maxInitial) {
            const showMoreBtn = document.createElement('button');
            showMoreBtn.className = 'show-more-btn';
            showMoreBtn.textContent = `Show ${session.unsaved_actions.length - maxInitial} more actions...`;
            showMoreBtn.style.cssText = 'margin-top: 1rem; padding: 0.5rem 1rem; background: #3b82f6; color: white; border: none; border-radius: 4px; cursor: pointer;';
            showMoreBtn.onclick = () => {
                // Render all actions with formatted timestamps
                unsavedActionsList.innerHTML = session.unsaved_actions.map((action, index) => `
                    <div class="unsaved-action-item">
                        <div class="action-header">
                            <span class="action-number">#${index + 1}</span>
                            <span class="action-category">${escapeHtml(action.category)}</span>
                            <span class="action-timestamp">${escapeHtml(formatTimestamp(action.timestamp))}</span>
                        </div>
                        <div class="action-detail">${escapeHtml(action.action)}</div>
                        <div class="action-line">Line ${action.line}</div>
                    </div>
                `).join('');
            };
            unsavedActionsList.appendChild(showMoreBtn);
        }
    } else {
        console.log('✗ Hiding unsaved actions section (no data)');
        unsavedWorkSection.classList.add('hidden');
    }

    // Model Details Section (show only if there are .rvt models)
    const modelDetailsSection = document.getElementById('model-details-section');
    if (session.primary_model || rvtModels.length > 0) {
        modelDetailsSection.classList.remove('hidden');
    } else {
        modelDetailsSection.classList.add('hidden');
    }

    // Views & Sheets Section
    const viewsSheetsSection = document.getElementById('views-sheets-section');
    const viewsListSection = document.getElementById('views-list-section');
    const sheetsListSection = document.getElementById('sheets-list-section');
    const viewsCountBadge = document.getElementById('views-count-badge');
    const sheetsCountBadge = document.getElementById('sheets-count-badge');
    const viewsSheetsTotalBadge = document.getElementById('views-sheets-total');
    const viewsUl = document.getElementById('views-ul');
    const sheetsUl = document.getElementById('sheets-ul');

    const hasViews = session.views && session.views.length > 0;
    const hasSheets = session.sheets && session.sheets.length > 0;

    // Render views
    if (hasViews) {
        viewsListSection.classList.remove('hidden');
        viewsCountBadge.textContent = session.views_count || session.views.length;
        viewsUl.innerHTML = session.views.map(view => {
            const count = view.count > 1 ? ` <span class="views-open-count">(${view.count}x)</span>` : '';
            return `<li>${escapeHtml(view.name)}${count}</li>`;
        }).join('');
    } else {
        viewsListSection.classList.add('hidden');
    }

    // Render sheets
    if (hasSheets) {
        sheetsListSection.classList.remove('hidden');
        sheetsCountBadge.textContent = session.sheets_count || session.sheets.length;
        sheetsUl.innerHTML = session.sheets.map(sheet => {
            const count = sheet.count > 1 ? ` <span class="views-open-count">(${sheet.count}x)</span>` : '';
            return `<li>${escapeHtml(sheet.name)}${count}</li>`;
        }).join('');
    } else {
        sheetsListSection.classList.add('hidden');
    }

    // Show/hide the whole section and update the summary total badge
    if (hasViews || hasSheets) {
        viewsSheetsSection.classList.remove('hidden');
        const total = (session.views_count || (session.views ? session.views.length : 0))
                    + (session.sheets_count || (session.sheets ? session.sheets.length : 0));
        viewsSheetsTotalBadge.textContent = total;
        viewsSheetsTotalBadge.classList.remove('hidden');
    } else {
        viewsSheetsSection.classList.add('hidden');
    }
}

// ======================
// Issues & Errors
// ======================

function deduplicateItems(items) {
    if (!items) return [];
    const seen = new Map();
    items.forEach(item => {
        const text = item.text.trim();
        const existing = seen.get(text);
        if (!existing || item.line > existing.line) {
            seen.set(text, item);
        }
    });
    return Array.from(seen.values());
}

function renderIssues(errors) {
    if (!errors) return;

    // Update counts with deduplicated totals
    document.getElementById('fatal-count').textContent = deduplicateItems(errors.fatal).length;
    document.getElementById('errors-count').textContent = deduplicateItems(errors.errors).length;
    document.getElementById('warnings-count').textContent = deduplicateItems(errors.warnings).length;
    document.getElementById('exceptions-count').textContent = deduplicateItems(errors.exceptions).length;

    // Render lists
    renderIssueList('issues-fatal', errors.fatal, 'critical');
    renderIssueList('issues-errors', errors.errors, 'error');
    renderIssueList('issues-warnings', errors.warnings, 'warning');
    renderIssueList('issues-exceptions', errors.exceptions, 'info');
}

function renderIssueList(containerId, items, severity) {
    const container = document.getElementById(containerId);

    if (!items || items.length === 0) {
        container.innerHTML = '<p class="no-items">No items found</p>';
        return;
    }

    // Deduplicate by text content, keeping the latest (highest) line number
    const seen = new Map();
    items.forEach(item => {
        const text = item.text.trim();
        const existing = seen.get(text);
        if (!existing || item.line > existing.line) {
            seen.set(text, item);
        }
    });
    const uniqueItems = Array.from(seen.values());

    const maxItems = 100;
    const displayItems = uniqueItems.slice(0, maxItems);

    container.innerHTML = displayItems.map(item => `
        <div class="issue-item issue-${severity}">
            <span class="issue-line">Line ${item.line}</span>
            <span class="issue-text">${escapeHtml(truncate(item.text, 200))}</span>
        </div>
    `).join('');

    if (uniqueItems.length > maxItems) {
        container.innerHTML += `<p class="more-items">... and ${uniqueItems.length - maxItems} more</p>`;
    }
}

// Issue tabs
document.querySelectorAll('.issue-tab').forEach(tab => {
    tab.addEventListener('click', () => {
        // Update active tab
        document.querySelectorAll('.issue-tab').forEach(t => t.classList.remove('active'));
        tab.classList.add('active');

        // Show corresponding list
        const issueType = tab.dataset.issue;
        document.querySelectorAll('.issue-list').forEach(list => list.classList.remove('active'));
        document.getElementById(`issues-${issueType}`).classList.add('active');
    });
});

// ======================
// Timeline
// ======================

function renderTimeline(timeline) {
    const container = document.getElementById('timeline-container');

    if (!timeline || timeline.length === 0) {
        container.innerHTML = '<p class="no-items">No timeline events recorded</p>';
        return;
    }

    // Only allow required event types
    const allowedTypes = [
        'session_start',
        'model_open',
        'file_open',
        'save',
        'sync',
        'error'
    ];

    const filtered = timeline.filter(event =>
        allowedTypes.includes(event.type)
    );

    if (filtered.length === 0) {
        container.innerHTML = '<p class="no-items">No relevant session events found</p>';
        return;
    }

    container.innerHTML = filtered.map(event => {
        const typeClass = getTimelineTypeClass(event.type);

        return `
            <div class="timeline-item ${typeClass}">
                <div class="timeline-marker"></div>
                <div class="timeline-content">
                    <div class="timeline-header">
                        <span class="timeline-type">
                            ${escapeHtml(event.description)}
                        </span>
                    </div>
                    <span class="timeline-timestamp">
                        ${escapeHtml(formatTimestamp(event.timestamp))}
                    </span>
                </div>
            </div>
        `;
    }).join('');
}


function getTimelineTypeClass(type) {
    const classes = {
        'crash': 'timeline-critical',
        'error': 'timeline-error',
        'session_start': 'timeline-success',
        'session_end': 'timeline-info',
        'model_open': 'timeline-info',
        'model_close': 'timeline-info',
        'file_open': 'timeline-info',
        'save': 'timeline-info',
        'save_as': 'timeline-info',
        'sync': 'timeline-warning',
        'reload': 'timeline-warning',
        'document_close': 'timeline-info',
        'revit_close': 'timeline-info'
    };
    return classes[type] || 'timeline-default';
}

// ======================
// Add-ins
// ======================

function renderAddins(addins) {
    if (!addins) return;

    // Show actual total count
    document.getElementById('failed-addins-count').textContent = addins.failed?.length || 0;

    // Calculate Third-Party count including ALL PyRevit plugins
    let thirdPartyCount = 0;
    if (addins.third_party) {
        addins.third_party.forEach(item => {
            thirdPartyCount++; // Count parent
            if (item.children && item.children.length > 0) {
                thirdPartyCount += item.children.length; // Count ALL children
            }
        });
    }
    document.getElementById('thirdparty-addins-count').textContent = thirdPartyCount;

    // Show actual total count
    document.getElementById('autodesk-addins-count').textContent = addins.autodesk?.length || 0;

    renderAddinListWithVersion('failed-addins-list', addins.failed);
    renderAddinListHierarchical('thirdparty-addins-list', addins.third_party);
    renderAddinListWithVersion('autodesk-addins-list', addins.autodesk);
}

function renderAddinListWithVersion(containerId, items) {
    const container = document.getElementById(containerId);

    if (!items || items.length === 0) {
        container.innerHTML = '<li class="no-items">None</li>';
        return;
    }

    // Show ALL items, no limit
    container.innerHTML = items.map(item => {
        const versionText = item.version ? ` <span style="color: #6b7280; font-size: 0.85em;">(v${escapeHtml(item.version)})</span>` : '';
        return `<li title="Line ${item.line}">${escapeHtml(truncate(item.name, 60))}${versionText}</li>`;
    }).join('');
}

function renderAddinListHierarchical(containerId, items) {
    const container = document.getElementById(containerId);

    if (!items || items.length === 0) {
        container.innerHTML = '<li class="no-items">None</li>';
        return;
    }

    let html = '';

    // Show ALL items, no limit
    items.forEach(item => {
        const versionText = item.version ? ` <span style="color: #6b7280; font-size: 0.85em;">(v${escapeHtml(item.version)})</span>` : '';

        // Check if this is a parent with children (PyRevitLoader)
        if (item.is_parent && item.children && item.children.length > 0) {
            // Display parent (PyRevitLoader) as a normal bold item
            html += `<li class="pyrevit-parent" title="Line ${item.line}"><strong>${escapeHtml(item.name)}${versionText}</strong></li>`;

            // Display children as indented items
            item.children.forEach(child => {
                const childVersionText = child.version ? ` <span style="color: #6b7280; font-size: 0.85em;">(v${escapeHtml(child.version)})</span>` : '';
                html += `<li class="pyrevit-child" title="Line ${child.line}">↳ ${escapeHtml(truncate(child.name, 60))}${childVersionText}</li>`;
            });
        } else {
            // Regular add-in
            html += `<li title="Line ${item.line}">${escapeHtml(truncate(item.name, 60))}${versionText}</li>`;
        }
    });

    container.innerHTML = html;
}

// ======================
// Workflow
// ======================

function renderWorkflow(workflow) {
    if (!workflow) return;

    // Render longest delays FIRST (above workflow events)
    if (workflow.longest_delays && workflow.longest_delays.length > 0) {
        renderLongestDelays(workflow.longest_delays);
    }

    renderWorkflowList('sync-ops-list', workflow.sync_operations);
    renderWorkflowList('file-ops-list', workflow.file_operations);
    renderWorkflowList('link-ops-list', workflow.link_operations);
}

function renderLongestDelays(delays) {
    // Delays section now exists in HTML, just populate the list
    const delaysList = document.getElementById('longest-delays-list');
    if (!delaysList) return;

    delaysList.innerHTML = delays.map((delay, index) => {
        // Determine severity based on duration
        let severityClass = 'delay-normal';
        let severityIcon = '⏱️';
        let severityLabel = '';

        if (delay.duration_seconds >= 300) { // 5+ minutes
            severityClass = 'delay-critical';
            severityIcon = '🔴';
            severityLabel = 'CRITICAL DELAY';
        } else if (delay.duration_seconds >= 120) { // 2+ minutes
            severityClass = 'delay-severe';
            severityIcon = '🟠';
            severityLabel = 'SEVERE DELAY';
        } else if (delay.duration_seconds >= 60) { // 1+ minute
            severityClass = 'delay-high';
            severityIcon = '🟡';
            severityLabel = 'HIGH DELAY';
        } else if (delay.duration_seconds >= 30) { // 30+ seconds
            severityClass = 'delay-moderate';
            severityIcon = '⚠️';
            severityLabel = 'MODERATE DELAY';
        }

        return `
        <li class="delay-item ${severityClass}" style="padding: 0.75rem; border-left: 3px solid; margin-bottom: 0.5rem; border-radius: 4px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                <strong style="display: flex; align-items: center; gap: 0.5rem;">
                    <span class="delay-icon">${severityIcon}</span>
                    <span>#${index + 1}: ${delay.duration_formatted}</span>
                    ${severityLabel ? `<span class="severity-badge">${severityLabel}</span>` : ''}
                </strong>
                <span style="font-size: 0.85em; color: #6b7280;">Lines ${delay.from_line}-${delay.to_line}</span>
            </div>
            <div style="font-size: 0.9em; color: #374151;">
                <div style="margin-bottom: 0.25rem;">
                    <span style="color: #6b7280;">From:</span> ${escapeHtml(truncate(delay.from_action, 80))}
                </div>
                <div>
                    <span style="color: #6b7280;">To:</span> ${escapeHtml(truncate(delay.to_action, 80))}
                </div>
            </div>
        </li>
    `}).join('');
}


function renderWorkflowList(containerId, items) {
    const container = document.getElementById(containerId);

    if (!items || items.length === 0) {
        container.innerHTML = '<li class="no-items">None recorded</li>';
        return;
    }

    // Initially show only first 20 items
    const maxInitial = 20;
    const showAll = container.dataset.showAll === 'true';
    const displayItems = showAll ? items : items.slice(0, maxInitial);

    container.innerHTML = displayItems.map(item =>
        `<li><span class="workflow-line">Line ${item.line}</span> ${escapeHtml(truncate(item.text, 80))}</li>`
    ).join('');

    if (items.length > maxInitial && !showAll) {
        const moreLink = document.createElement('li');
        moreLink.className = 'more-items clickable';
        moreLink.innerHTML = `... and ${items.length - maxInitial} more`;
        moreLink.style.cursor = 'pointer';
        moreLink.style.color = '#3b82f6';
        moreLink.addEventListener('click', () => {
            container.dataset.showAll = 'true';
            renderWorkflowList(containerId, items);
        });
        container.appendChild(moreLink);
    }
}

// ======================
// KB Articles
// ======================

function renderKbArticles(matchedIssues) {
    const container = document.getElementById('kb-articles-container');

    if (!matchedIssues || matchedIssues.length === 0) {
        container.innerHTML = '<p class="no-items">No known issues detected</p>';
        return;
    }

    // Filter to only those with KB links
    const kbIssues = matchedIssues.filter(m => m.kb_article);

    if (kbIssues.length === 0) {
        container.innerHTML = '<p class="no-items">No KB articles found for detected issues</p>';
        return;
    }

    const priorityOrder = { high: 0, medium: 1, low: 2 };
    const sortedIssues = [...kbIssues].sort((a, b) => {
        const pa = priorityOrder[a.severity] ?? 3;
        const pb = priorityOrder[b.severity] ?? 3;
        return pa - pb;
    });

    container.innerHTML = sortedIssues.slice(0, 50).map(issue => {
        const severityClass = `severity-${issue.severity}`;
        return `
            <div class="kb-article ${severityClass}">
                <div class="kb-header">
                    <span class="kb-severity">${issue.severity.toUpperCase()}</span>
                    <span class="kb-line">Line ${issue.line}</span>
                </div>
                <p class="kb-pattern">${escapeHtml(truncate(issue.pattern, 100))}</p>
                <p class="kb-matched">${escapeHtml(truncate(issue.matched_text, 150))}</p>
                <a href="${escapeHtml(issue.kb_article)}" target="_blank" rel="noopener" class="kb-link">
                    View Autodesk Solution
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>
                        <polyline points="15 3 21 3 21 9"/>
                        <line x1="10" y1="14" x2="21" y2="3"/>
                    </svg>
                </a>
            </div>
        `;
    }).join('');
}

// ======================
// Timeline
// ======================

function renderTimeline(timeline) {
    const container = document.getElementById('timeline-container');

    if (!timeline || timeline.length === 0) {
        container.innerHTML = '<p class="no-items">No timeline events recorded</p>';
        return;
    }

    container.innerHTML = timeline.map(event => {
        const typeClass = getTimelineTypeClass(event.type);
        const timestampDisplay = event.timestamp ? `<span class="timeline-timestamp">${escapeHtml(event.timestamp)}</span>` : '';
        const textDisplay = event.text ? `<p class="timeline-text">${escapeHtml(truncate(event.text, 150))}</p>` : '';
        // Show model name in description if available
        const modelDisplay = event.model ? ` <span class="timeline-model">(${escapeHtml(event.model)})</span>` : '';
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
        `;
    }).join('');
}

function getTimelineTypeClass(type) {
    const classes = {
        'crash': 'timeline-critical',
        'error': 'timeline-error',
        'session_start': 'timeline-success',
        'session_end': 'timeline-info',
        'model_open': 'timeline-info',
        'file_open': 'timeline-info',
        'save': 'timeline-info',
        'save_as': 'timeline-info',
        'sync': 'timeline-warning',
        'reload': 'timeline-warning',
        'document_close': 'timeline-info',
        'revit_close': 'timeline-info'
    };
    return classes[type] || 'timeline-default';
}

// ======================
// KB Articles
// ======================

function renderKbArticles(matchedIssues) {
    const container = document.getElementById('kb-articles-container');

    if (!matchedIssues || matchedIssues.length === 0) {
        container.innerHTML = '<p class="no-items">No known issues detected</p>';
        return;
    }

    // Filter to only those with KB links
    const kbIssues = matchedIssues.filter(m => m.kb_article);

    if (kbIssues.length === 0) {
        container.innerHTML = '<p class="no-items">No KB articles found for detected issues</p>';
        return;
    }

    const priorityOrder = { high: 0, medium: 1, low: 2 };
    const sortedIssues = [...kbIssues].sort((a, b) => {
        const pa = priorityOrder[a.severity] ?? 3;
        const pb = priorityOrder[b.severity] ?? 3;
        return pa - pb;
    });

    container.innerHTML = sortedIssues.slice(0, 50).map(issue => {
        const severityClass = `severity-${issue.severity}`;
        return `
            <div class="kb-article ${severityClass}">
                <div class="kb-header">
                    <span class="kb-severity">${issue.severity.toUpperCase()}</span>
                    <span class="kb-line">Line ${issue.line}</span>
                </div>
                <p class="kb-pattern">${escapeHtml(truncate(issue.pattern, 100))}</p>
                <p class="kb-matched">${escapeHtml(truncate(issue.matched_text, 150))}</p>
                <a href="${escapeHtml(issue.kb_article)}" target="_blank" rel="noopener" class="kb-link">
                    View Autodesk Solution
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>
                        <polyline points="15 3 21 3 21 9"/>
                        <line x1="10" y1="14" x2="21" y2="3"/>
                    </svg>
                </a>
            </div>
        `;
    }).join('');
}

// ======================
// Tab Navigation
// ======================

document.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', () => {
        const tabName = tab.dataset.tab;

        // Update active tab
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        tab.classList.add('active');

        // Show corresponding panel
        document.querySelectorAll('.tab-panel').forEach(panel => panel.classList.remove('active'));
        document.getElementById(`panel-${tabName}`).classList.add('active');
    });
});

// ======================
// Utilities
// ======================

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function truncate(text, maxLength) {
    if (!text) return '';
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
}

/**
 * Format timestamp to remove milliseconds and ensure HH:MM:SS format
 * Handles formats like: "4-Feb-2026 11:53:40.123" -> "4-Feb-2026 11:53:40"
 */
function formatTimestamp(timestamp) {
    if (!timestamp || timestamp === 'N/A') return timestamp;

    // Remove milliseconds if present (anything after the last colon's seconds)
    // Pattern: DD-MMM-YYYY HH:MM:SS.mmm -> DD-MMM-YYYY HH:MM:SS
    const cleaned = timestamp.replace(/(\d{2}:\d{2}:\d{2})\.\d+/, '$1');

    return cleaned;
}
