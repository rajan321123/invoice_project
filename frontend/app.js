// Config - In a real app, this might come from env vars
const API_BASE = 'http://127.0.0.1:8000';

// State
let currentReport = null; // { summary: ..., details: [] }
let displayData = []; // Filtered/Sorted list

// DOM Elements
const els = {
    apiStatus: document.getElementById('api-status'),
    tabPdf: document.getElementById('tab-pdf'),
    tabJson: document.getElementById('tab-json'),
    panelPdf: document.getElementById('panel-pdf'),
    panelJson: document.getElementById('panel-json'),
    fileInput: document.getElementById('file-input'),
    fileCount: document.getElementById('file-count'),
    btnUpload: document.getElementById('btn-upload'),
    jsonInput: document.getElementById('json-input'),
    btnValidateJson: document.getElementById('btn-validate-json'),
    progressContainer: document.getElementById('progress-container'),
    progressBar: document.getElementById('progress-bar'),
    resultsControls: document.getElementById('results-controls'),
    resultsContainer: document.getElementById('results-container'),
    resultsBody: document.getElementById('results-body'),
    resultsCount: document.getElementById('results-count'),
    emptyState: document.getElementById('empty-state'),
    toggleInvalid: document.getElementById('toggle-invalid'),
    sortSelect: document.getElementById('sort-select'),
    dataModal: document.getElementById('data-modal'),
    modalContent: document.getElementById('modal-content'),
    closeModal: document.getElementById('close-modal')
};

// --- Initialization ---
init();

function init() {
    checkHealth();
    setupTabs();
    setupInputs();
    setupActions();
    setupFilters();
}

async function checkHealth() {
    try {
        const res = await fetch(`${API_BASE}/health`);
        if (res.ok) {
            els.apiStatus.textContent = "Online";
            els.apiStatus.className = "font-semibold text-green-600";
        } else {
            throw new Error("Health check failed");
        }
    } catch (e) {
        els.apiStatus.textContent = "Offline";
        els.apiStatus.className = "font-semibold text-red-600";
        console.error("API Error", e);
    }
}

// --- UI Logic ---

function setupTabs() {
    els.tabPdf.addEventListener('click', () => switchTab('pdf'));
    els.tabJson.addEventListener('click', () => switchTab('json'));
}

function switchTab(tab) {
    if (tab === 'pdf') {
        els.tabPdf.classList.add('text-indigo-600', 'bg-white', 'border-slate-300', 'shadow-sm');
        els.tabPdf.classList.remove('text-slate-600', 'hover:text-slate-900', 'border-transparent');

        els.tabJson.classList.remove('text-indigo-600', 'bg-white', 'border-slate-300', 'shadow-sm');
        els.tabJson.classList.add('text-slate-600', 'hover:text-slate-900');

        els.panelPdf.classList.remove('hidden');
        els.panelJson.classList.add('hidden');
    } else {
        els.tabJson.classList.add('text-indigo-600', 'bg-white', 'border-slate-300', 'shadow-sm');
        els.tabJson.classList.remove('text-slate-600', 'hover:text-slate-900');

        els.tabPdf.classList.remove('text-indigo-600', 'bg-white', 'border-slate-300', 'shadow-sm');
        els.tabPdf.classList.add('text-slate-600', 'hover:text-slate-900');

        els.panelJson.classList.remove('hidden');
        els.panelPdf.classList.add('hidden');
    }
}

function setupInputs() {
    els.fileInput.addEventListener('change', (e) => {
        const count = e.target.files.length;
        if (count > 0) {
            els.fileCount.textContent = `${count} file${count > 1 ? 's' : ''} selected`;
            els.fileCount.classList.remove('hidden');
            els.btnUpload.disabled = false;
        } else {
            els.fileCount.classList.add('hidden');
            els.btnUpload.disabled = true;
        }
    });

    els.jsonInput.addEventListener('input', (e) => {
        els.btnValidateJson.disabled = !e.target.value.trim();
    });
}

function setupActions() {
    els.btnUpload.addEventListener('click', handleUpload);
    els.btnValidateJson.addEventListener('click', handleJsonValidation);
    els.closeModal.addEventListener('click', () => els.dataModal.classList.add('hidden'));
}

function setupFilters() {
    els.toggleInvalid.addEventListener('change', renderTable);
    els.sortSelect.addEventListener('change', renderTable);
}

// --- API Interactions ---

async function handleUpload() {
    const files = els.fileInput.files;
    if (!files.length) return;

    showProgress(true);
    els.btnUpload.disabled = true;

    const formData = new FormData();
    for (let i = 0; i < files.length; i++) {
        formData.append('files', files[i]);
    }

    try {
        simulateProgress(); // Fake progress since fetch doesn't support it easily for upload
        const res = await fetch(`${API_BASE}/extract-and-validate-pdfs`, {
            method: 'POST',
            body: formData
        });

        if (!res.ok) throw new Error("Upload failed");

        const data = await res.json();
        processResults(data);
    } catch (e) {
        alert("Error processing files: " + e.message);
    } finally {
        showProgress(false);
        els.btnUpload.disabled = false;
    }
}

async function handleJsonValidation() {
    const rawJson = els.jsonInput.value;
    let invoices;

    try {
        invoices = JSON.parse(rawJson);
        if (!Array.isArray(invoices)) throw new Error("Input must be a JSON list");
    } catch (e) {
        alert("Invalid JSON: " + e.message);
        return;
    }

    showProgress(true);
    els.btnValidateJson.disabled = true;

    try {
        simulateProgress();
        const res = await fetch(`${API_BASE}/validate-json`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ invoices })
        });

        if (!res.ok) throw new Error("Validation failed");

        const data = await res.json();
        processResults(data);
    } catch (e) {
        alert("Error validating JSON: " + e.message);
    } finally {
        showProgress(false);
        els.btnValidateJson.disabled = false;
    }
}

// --- Rendering & Logic ---

function processResults(report) {
    currentReport = report;
    els.emptyState.classList.add('hidden');
    els.resultsControls.classList.remove('hidden');
    els.resultsContainer.classList.remove('hidden');
    renderTable();
}

function renderTable() {
    if (!currentReport || !currentReport.details) return;

    // Filter
    let items = [...currentReport.details];
    if (els.toggleInvalid.checked) {
        items = items.filter(i => !i.is_valid);
    }

    // Sort
    const sortMode = els.sortSelect.value;
    items.sort((a, b) => {
        if (sortMode === 'status') {
            // Priority: REJECTED > WARNING > APPROVED
            const priority = { 'REJECTED': 0, 'WARNING': 1, 'APPROVED': 2 };
            return priority[a.status] - priority[b.status];
        } else {
            // Invoice Number
            return (a.invoice_number || '').localeCompare(b.invoice_number || '');
        }
    });

    // Update Count
    els.resultsCount.textContent = items.length;

    // Render Rows
    els.resultsBody.innerHTML = '';
    items.forEach(item => {
        const row = document.createElement('tr');
        row.className = 'hover:bg-slate-50 transition-colors cursor-pointer group';
        row.onclick = (e) => {
            // Don't trigger if text selected
            if (window.getSelection().toString().length) return;
            showDataModal(item);
        };

        // Status Badge
        let statusBadge = '';
        if (item.status === 'APPROVED') {
            statusBadge = '<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">Approved</span>';
        } else if (item.status === 'WARNING') {
            statusBadge = '<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">Warning</span>';
        } else {
            statusBadge = '<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">Rejected</span>';
        }

        // Issues
        let issuesHtml = '';
        if (item.errors.length) {
            issuesHtml += `<div class="text-red-600 text-xs font-medium">${item.errors[0]} ${item.errors.length > 1 ? `(+${item.errors.length - 1} more)` : ''}</div>`;
        }
        if (item.warnings.length) {
            issuesHtml += `<div class="text-yellow-600 text-xs">${item.warnings[0]} ${item.warnings.length > 1 ? `(+${item.warnings.length - 1} more)` : ''}</div>`;
        }
        if (!issuesHtml) issuesHtml = '<span class="text-slate-400 text-xs">No issues</span>';

        const invNum = item.invoice_number || '<span class="italic text-slate-400">Missing</span>';
        const invDate = item.original_data.invoice_date || '<span class="text-slate-400">-</span>';
        const seller = item.original_data.seller_name || '<span class="italic text-slate-400">Unknown</span>';
        const amount = item.original_data.gross_total
            ? `${item.original_data.currency || ''} ${item.original_data.gross_total}`
            : '<span class="text-slate-400">-</span>';

        row.innerHTML = `
            <td class="px-6 py-4 whitespace-nowrap">${statusBadge}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-slate-900">${invNum}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-slate-500">${invDate}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-slate-500">${seller}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-slate-900 text-right font-mono">${amount}</td>
            <td class="px-6 py-4 text-sm">${issuesHtml}</td>
        `;

        els.resultsBody.appendChild(row);
    });
}

function showDataModal(item) {
    els.modalContent.textContent = JSON.stringify(item, null, 2);
    els.dataModal.classList.remove('hidden');
}

// --- Utils ---

function showProgress(show) {
    if (show) {
        els.progressContainer.classList.remove('hidden');
        els.progressBar.style.width = '10%';
    } else {
        els.progressBar.style.width = '100%';
        setTimeout(() => {
            els.progressContainer.classList.add('hidden');
            els.progressBar.style.width = '0%';
        }, 500);
    }
}

function simulateProgress() {
    let w = 10;
    const int = setInterval(() => {
        if (w >= 90) clearInterval(int);
        w += Math.random() * 10;
        if (w > 90) w = 90;
        els.progressBar.style.width = `${w}%`;
    }, 200);
}
