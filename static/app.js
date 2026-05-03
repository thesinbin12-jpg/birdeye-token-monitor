/**
 * Birdeye Token Safety Radar - Frontend JavaScript
 * Handles token scanning, UI updates, and API communication
 */

// DOM Elements
const scanBtn = document.getElementById('scanBtn');
const loadingContainer = document.querySelector('.loading-container');
const resultsContainer = document.querySelector('.results-container');
const tokensGrid = document.getElementById('tokensGrid');
const resultsCount = document.getElementById('resultsCount');
const apiCounterValue = document.getElementById('apiCounterValue');
const errorMessage = document.querySelector('.error-message');

// State
let isScanning = false;

/**
 * Format a wallet address for display (truncate middle)
 */
function formatAddress(address) {
    if (!address) return 'N/A';
    if (address.length <= 16) return address;
    return `${address.slice(0, 6)}...${address.slice(-4)}`;
}

/**
 * Format liquidity in human-readable format
 */
function formatLiquidity(liquidity, formatted) {
    if (formatted && formatted !== 'N/A') return formatted;
    if (!liquidity) return '$0';
    if (liquidity >= 1000000) return `$${(liquidity / 1000000).toFixed(2)}M`;
    if (liquidity >= 1000) return `$${(liquidity / 1000).toFixed(2)}K`;
    return `$${liquidity.toFixed(2)}`;
}

/**
 * Get verdict class for styling
 */
function getVerdictClass(verdict) {
    if (!verdict) return 'unknown';
    return verdict.toLowerCase();
}

/**
 * Get metric class based on value
 */
function getMetricClass(field, value) {
    if (value === true) return 'success';
    if (value === false) return 'danger';
    if (field === 'liquidity') {
        if (value >= 10000) return 'success';
        if (value >= 1000) return 'warning';
        return 'danger';
    }
    if (field === 'top10') {
        if (value <= 40) return 'success';
        if (value <= 60) return 'warning';
        return 'danger';
    }
    if (field === 'age') {
        if (value >= 24) return 'success';
        return 'warning';
    }
    return 'neutral';
}

/**
 * Create a token card HTML element
 */
function createTokenCard(token) {
    const verdictClass = getVerdictClass(token.verdict);
    const scoreClass = verdictClass;

    // Determine authority status display
    const mintStatus = token.mint_authority_revoked
        ? '<span class="metric-value success">Revoked</span>'
        : '<span class="metric-value danger">Active</span>';

    const freezeStatus = token.freeze_authority_revoked
        ? '<span class="metric-value success">Revoked</span>'
        : '<span class="metric-value danger">Active</span>';

    // Birdeye links
    const birdeyeTokenUrl = `https://birdeye.so/token/${token.address}`;
    const birdeyeHolderUrl = `https://birdeye.so/holder/${token.address}`;

    return `
        <div class="token-card">
            <div class="card-header">
                <div class="token-info">
                    <h3>${token.name || 'Unknown Token'}</h3>
                    <span class="token-symbol">${token.symbol || '???'}</span>
                </div>
                <span class="verdict-badge ${verdictClass}">${token.verdict || 'UNKNOWN'}</span>
            </div>

            <div class="score-section">
                <div class="score-label">Safety Score</div>
                <div class="score-value ${scoreClass}">${token.score ?? '?'}/100</div>
            </div>

            <div class="metrics-grid">
                <div class="metric">
                    <div class="metric-label">Mint Auth</div>
                    ${mintStatus}
                </div>
                <div class="metric">
                    <div class="metric-label">Freeze Auth</div>
                    ${freezeStatus}
                </div>
                <div class="metric">
                    <div class="metric-label">Liquidity</div>
                    <span class="metric-value ${getMetricClass('liquidity', token.liquidity)}">${token.liquidity_formatted || formatLiquidity(token.liquidity)}</span>
                </div>
                <div class="metric">
                    <div class="metric-label">Top 10 Holders</div>
                    <span class="metric-value ${getMetricClass('top10', token.top_10_holders_pct)}">${token.top_10_holders_pct ? token.top_10_holders_pct.toFixed(1) + '%' : 'N/A'}</span>
                </div>
                <div class="metric">
                    <div class="metric-label">Contract Age</div>
                    <span class="metric-value ${getMetricClass('age', token.contract_age_hours)}">${token.contract_age_hours ? token.contract_age_hours.toFixed(1) + 'h' : '< 1h'}</span>
                </div>
                <div class="metric">
                    <div class="metric-label">Price</div>
                    <span class="metric-value neutral">${token.price_formatted || 'N/A'}</span>
                </div>
            </div>

            <div class="card-footer">
                <a href="${birdeyeTokenUrl}" target="_blank" rel="noopener noreferrer" class="card-link">
                    View on Birdeye
                </a>
                <a href="${birdeyeHolderUrl}" target="_blank" rel="noopener noreferrer" class="card-link">
                    Holders
                </a>
            </div>
        </div>
    `;
}

/**
 * Render all token cards in the grid
 */
function renderTokens(tokens) {
    if (!tokens || tokens.length === 0) {
        tokensGrid.innerHTML = '<p style="text-align: center; color: var(--text-muted); grid-column: 1/-1; padding: 2rem;">No tokens found. Try scanning again.</p>';
        return;
    }

    tokensGrid.innerHTML = tokens.map(createTokenCard).join('');
    resultsCount.textContent = `${tokens.length} tokens scanned`;
}

/**
 * Show loading state
 */
function showLoading() {
    scanBtn.disabled = true;
    scanBtn.innerHTML = '<span class="icon">⏳</span> Scanning...';
    loadingContainer.classList.add('active');
    resultsContainer.classList.remove('active');
    errorMessage.classList.remove('active');
}

/**
 * Hide loading state
 */
function hideLoading() {
    scanBtn.disabled = false;
    scanBtn.innerHTML = '<span class="icon">🔍</span> Scan Latest 15 Tokens';
    loadingContainer.classList.remove('active');
    resultsContainer.classList.add('active');
}

/**
 * Show error message
 */
function showError(message) {
    errorMessage.textContent = message;
    errorMessage.classList.add('active');
    hideLoading();
}

/**
 * Update API counter display
 */
function updateApiCounter(count) {
    if (apiCounterValue && count !== undefined) {
        apiCounterValue.textContent = count;
    }
}

/**
 * Main scan function
 */
async function scanTokens() {
    if (isScanning) return;

    isScanning = true;
    showLoading();

    try {
        const response = await fetch('/api/scan-new-tokens', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        if (data.error) {
            throw new Error(data.error);
        }

        // Update API counter
        if (data.total_api_calls !== undefined) {
            updateApiCounter(data.total_api_calls);
        }

        // Render results
        renderTokens(data.tokens);

        console.log(`Scan complete: ${data.tokens_scanned} tokens, ${data.total_api_calls} API calls`);

    } catch (error) {
        console.error('Scan failed:', error);
        showError(`Scan failed: ${error.message}. Please check your API key and try again.`);
    } finally {
        isScanning = false;
    }
}

/**
 * Check API health on page load
 */
async function checkHealth() {
    try {
        const response = await fetch('/api/health');
        const data = await response.json();
        updateApiCounter(data.api_calls_made);
    } catch (error) {
        console.error('Health check failed:', error);
    }
}

// Event Listeners
if (scanBtn) {
    scanBtn.addEventListener('click', scanTokens);
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    checkHealth();
});

// Keyboard shortcut: Press 'S' to scan
document.addEventListener('keydown', (e) => {
    if (e.key === 's' && !e.ctrlKey && !e.metaKey && !e.altKey) {
        const activeElement = document.activeElement;
        const isInput = activeElement.tagName === 'INPUT' || activeElement.tagName === 'TEXTAREA';
        if (!isInput && !isScanning) {
            scanTokens();
        }
    }
});