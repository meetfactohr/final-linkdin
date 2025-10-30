// Corporate Contact Finder - Frontend JavaScript

let searchResults = [];
let isSearching = false;
let currentEventSource = null;
let currentSessionId = null;

// DOM Elements
const domainsTextarea = document.getElementById('domains');
const rolesTextarea = document.getElementById('roles');
const startBtn = document.getElementById('startBtn');
const stopBtn = document.getElementById('stopBtn');
const downloadBtn = document.getElementById('downloadBtn');
const progressSection = document.getElementById('progressSection');
const progressBar = document.getElementById('progressBar');
const progressText = document.getElementById('progressText');
const progressCount = document.getElementById('progressCount');
const statusLog = document.getElementById('statusLog');
const logContent = document.getElementById('logContent');
const resultsSection = document.getElementById('resultsSection');
const resultsBody = document.getElementById('resultsBody');
const totalResults = document.getElementById('totalResults');
const successCount = document.getElementById('successCount');

// Event Listeners
startBtn.addEventListener('click', startSearch);
stopBtn.addEventListener('click', stopSearch);
downloadBtn.addEventListener('click', downloadCSV);

// Add log entry
function addLog(message, type = 'info') {
    const logEntry = document.createElement('div');
    logEntry.className = `log-entry log-${type}`;
    const timestamp = new Date().toLocaleTimeString();
    logEntry.textContent = `[${timestamp}] ${message}`;
    logContent.appendChild(logEntry);
    logContent.scrollTop = logContent.scrollHeight;
}

// Update progress
function updateProgress(current, total, message) {
    const percentage = total > 0 ? (current / total) * 100 : 0;
    progressBar.style.width = `${percentage}%`;
    progressText.textContent = message;
    progressCount.textContent = `${current} / ${total}`;
}

// Add single result to table
function addResultToTable(result) {
    const row = document.createElement('tr');
    const index = resultsBody.children.length;
    row.className = index % 2 === 0 ? 'bg-white' : 'bg-gray-50';
    
    // Domain
    const domainCell = document.createElement('td');
    domainCell.className = 'px-4 py-3 text-sm text-gray-900';
    domainCell.textContent = result.domain;
    row.appendChild(domainCell);
    
    // Name
    const nameCell = document.createElement('td');
    nameCell.className = 'px-4 py-3 text-sm text-gray-900';
    nameCell.textContent = result.name;
    if (result.name === 'Not Found' || result.name === 'Error') {
        nameCell.classList.add('status-not-found');
    }
    row.appendChild(nameCell);
    
    // Title
    const titleCell = document.createElement('td');
    titleCell.className = 'px-4 py-3 text-sm text-gray-700';
    titleCell.textContent = result.title;
    row.appendChild(titleCell);
    
    // Email
    const emailCell = document.createElement('td');
    emailCell.className = 'px-4 py-3 text-sm';
    emailCell.textContent = result.email;
    const isSuccess = result.email !== 'Not Found' && result.email !== 'Error';
    if (isSuccess) {
        emailCell.classList.add('status-success');
    } else if (result.email === 'Error') {
        emailCell.classList.add('status-error');
    } else {
        emailCell.classList.add('status-not-found');
    }
    row.appendChild(emailCell);
    
    // LinkedIn URL
    const linkedinCell = document.createElement('td');
    linkedinCell.className = 'px-4 py-3 text-sm';
    if (result.linkedin_url && result.linkedin_url !== 'Not Found' && result.linkedin_url !== 'Error') {
        const link = document.createElement('a');
        link.href = result.linkedin_url;
        link.target = '_blank';
        link.className = 'linkedin-link';
        link.textContent = 'View Profile';
        linkedinCell.appendChild(link);
    } else {
        linkedinCell.textContent = result.linkedin_url;
        linkedinCell.classList.add('status-not-found');
    }
    row.appendChild(linkedinCell);
    
    // Matched Role
    const roleCell = document.createElement('td');
    roleCell.className = 'px-4 py-3 text-sm text-gray-700 font-medium';
    roleCell.textContent = result.matched_role;
    row.appendChild(roleCell);
    
    resultsBody.appendChild(row);
    
    // Show results section
    resultsSection.classList.remove('hidden');
}

// Update summary statistics
function updateSummary() {
    let successfulMatches = 0;
    searchResults.forEach(result => {
        const isSuccess = result.email !== 'Not Found' && result.email !== 'Error';
        if (isSuccess) successfulMatches++;
    });
    
    totalResults.textContent = searchResults.length;
    successCount.textContent = successfulMatches;
    
    if (searchResults.length > 0) {
        downloadBtn.disabled = false;
    }
}

// Start search with EventSource for reliable SSE
async function startSearch() {
    const domainsText = domainsTextarea.value.trim();
    const rolesText = rolesTextarea.value.trim();
    
    if (!domainsText) {
        alert('Please enter at least one domain');
        return;
    }
    
    if (!rolesText) {
        alert('Please enter at least one role');
        return;
    }
    
    // Parse domains (one per line)
    const domains = domainsText
        .split('\n')
        .map(d => d.trim())
        .filter(d => d.length > 0);
    
    // Parse roles (one per line)
    const roles = rolesText
        .split('\n')
        .map(r => r.trim())
        .filter(r => r.length > 0);
    
    if (domains.length === 0) {
        alert('Please enter valid domains');
        return;
    }
    
    if (roles.length === 0) {
        alert('Please enter valid roles');
        return;
    }
    
    const totalPairs = domains.length * roles.length;
    
    // Reset UI
    searchResults = [];
    resultsBody.innerHTML = '';
    logContent.innerHTML = '';
    
    // Show/hide elements
    isSearching = true;
    startBtn.classList.add('hidden');
    stopBtn.classList.remove('hidden');
    progressSection.classList.remove('hidden');
    statusLog.classList.remove('hidden');
    resultsSection.classList.add('hidden');
    downloadBtn.disabled = true;
    
    // Disable textareas
    domainsTextarea.disabled = true;
    rolesTextarea.disabled = true;
    
    addLog(`Starting search for ${domains.length} domain(s) x ${roles.length} role(s) = ${totalPairs} combinations...`, 'info');
    updateProgress(0, totalPairs, 'Initializing search...');
    
    try {
        // Step 1: Initialize search and get session ID
        const response = await fetch('/search', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ domains, roles })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to start search');
        }
        
        const data = await response.json();
        currentSessionId = data.session_id;
        
        // Step 2: Connect to SSE stream using EventSource
        currentEventSource = new EventSource(`/search/stream/${currentSessionId}`);
        
        currentEventSource.onmessage = function(event) {
            try {
                const data = JSON.parse(event.data);
                handleSSEEvent(data);
            } catch (e) {
                console.error('Failed to parse SSE event:', e);
            }
        };
        
        currentEventSource.onerror = function(error) {
            console.error('EventSource error:', error);
            if (currentEventSource.readyState === EventSource.CLOSED) {
                addLog('Connection closed', 'info');
                finishSearch();
            }
        };
        
    } catch (error) {
        addLog(`Error: ${error.message}`, 'error');
        alert(`Search failed: ${error.message}`);
        finishSearch();
    }
}

// Handle SSE events
function handleSSEEvent(data) {
    switch (data.type) {
        case 'init':
            currentSessionId = data.session_id;
            addLog(`Search initialized. Processing ${data.total} domain-role combinations...`, 'info');
            break;
            
        case 'progress':
            const role = data.role || '';
            updateProgress(data.current, data.total, `Processing: ${role} at ${data.domain}`);
            addLog(`[${data.current}/${data.total}] Searching ${role} at ${data.domain}...`, 'info');
            break;
            
        case 'result':
            searchResults.push(data.data);
            addResultToTable(data.data);
            updateSummary();
            
            const result = data.data;
            if (result.email !== 'Not Found' && result.email !== 'Error') {
                addLog(`✓ Found contact: ${result.name} (${result.matched_role}) at ${result.domain}`, 'success');
            } else {
                addLog(`✗ No verified email for ${result.matched_role} at ${result.domain}`, 'error');
            }
            break;
            
        case 'complete':
            addLog(`Search completed! Processed ${searchResults.length} domains.`, 'success');
            finishSearch();
            break;
            
        case 'stopped':
            addLog('Search stopped by user', 'error');
            finishSearch();
            break;
            
        case 'error':
            addLog(`Error: ${data.message}`, 'error');
            alert(`Search error: ${data.message}`);
            finishSearch();
            break;
    }
}

// Finish search and reset UI
function finishSearch() {
    isSearching = false;
    startBtn.classList.remove('hidden');
    stopBtn.classList.add('hidden');
    domainsTextarea.disabled = false;
    rolesTextarea.disabled = false;
    
    // Close EventSource connection
    if (currentEventSource) {
        currentEventSource.close();
        currentEventSource = null;
    }
    
    currentSessionId = null;
}

// Stop search
async function stopSearch() {
    if (currentSessionId) {
        addLog('Stopping search...', 'info');
        
        try {
            const response = await fetch('/stop-search', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ session_id: currentSessionId })
            });
            
            if (!response.ok) {
                throw new Error('Failed to stop search');
            }
        } catch (error) {
            addLog(`Error stopping search: ${error.message}`, 'error');
        }
    }
}


// Download CSV
async function downloadCSV() {
    if (searchResults.length === 0) {
        alert('No results to download');
        return;
    }
    
    try {
        const response = await fetch('/export-csv', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ results: searchResults })
        });
        
        if (!response.ok) {
            throw new Error('Failed to export CSV');
        }
        
        const data = await response.json();
        
        // Create download link
        const blob = new Blob([data.csv], { type: 'text/csv' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `corporate_contacts_${new Date().toISOString().slice(0, 10)}.csv`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
        
        addLog('CSV exported successfully', 'success');
        
    } catch (error) {
        addLog(`Error exporting CSV: ${error.message}`, 'error');
        alert('Failed to export CSV');
    }
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    addLog('Application initialized. Enter domains to begin.', 'info');
});
