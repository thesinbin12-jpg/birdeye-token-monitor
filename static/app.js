/**
 * Birdeye Token Safety Radar - Frontend Logic
 * Enhanced with animations, toasts, and score circles
 */

(function() {
    'use strict';

    const $ = (sel) => document.querySelector(sel);
    const $$ = (sel) => document.querySelectorAll(sel);

    const elements = {
        scanBtn: $('#scanBtn'),
        apiCounterValue: $('#apiCounterValue'),
        resultsSection: $('#resultsSection'),
        tokensGrid: $('#tokensGrid'),
        resultsCount: $('#resultsCount'),
        emptyState: $('#emptyState'),
        toastContainer: $('#toastContainer')
    };

    let isScanning = false;

    function showToast(message, type = 'info', duration = 5000) {
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;

        const iconSvg = type === 'error'
            ? '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M15 9l-6 6M9 9l6 6"/></svg>'
            : '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/></svg>';

        toast.innerHTML = `
            <span class="toast-icon">${iconSvg}</span>
            <span class="toast-message">${message}</span>
            <button class="toast-close" aria-label="Close">
                <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M18 6L6 18M6 6l12 12"/>
                </svg>
            </button>
        `;

        toast.querySelector('.toast-close').addEventListener('click', () => removeToast(toast));
        elements.toastContainer.appendChild(toast);

        if (duration > 0) {
            setTimeout(() => removeToast(toast), duration);
        }

        return toast;
    }

    function removeToast(toast) {
        toast.style.animation = 'toastSlideIn 0.3s ease-out reverse';
        setTimeout(() => toast.remove(), 300);
    }

    function animateCounter(element, target, duration = 500) {
        const start = parseInt(element.textContent) || 0;
        const diff = target - start;
        const startTime = performance.now();

        function update(currentTime) {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);
            const eased = 1 - Math.pow(1 - progress, 3);
            const current = Math.round(start + diff * eased);
            element.textContent = current;

            if (progress < 1) {
                requestAnimationFrame(update);
            }
        }

        requestAnimationFrame(update);
    }

    function getVerdictClass(verdict) {
        if (!verdict) return 'risky';
        return verdict.toLowerCase();
    }

    function formatAddress(address) {
        if (!address) return '';
        if (address.length <= 16) return address;
        return `${address.slice(0, 6)}...${address.slice(-4)}`;
    }

    function createScoreCircle(score, verdict) {
        const circumference = 2 * Math.PI * 34;
        const offset = circumference - (score / 100) * circumference;
        const verdictClass = getVerdictClass(verdict);

        return `
            <div class="score-circle">
                <svg width="80" height="80" viewBox="0 0 80 80">
                    <circle class="score-circle-bg" cx="40" cy="40" r="34"/>
                    <circle class="score-circle-progress ${verdictClass}"
                        cx="40" cy="40" r="34"
                        stroke-dasharray="${circumference}"
                        stroke-dashoffset="${circumference}"
                        data-target="${offset}"/>
                </svg>
                <div class="score-circle-text">
                    <span class="score-value ${verdictClass}">${score ?? '?'}</span>
                    <span class="score-label">Score</span>
                </div>
            </div>
        `;
    }

    function createMetricIcon(type) {
        const icons = {
            liquidity: '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2v20M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6"/></svg>',
            mint: '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0110 0v4"/></svg>',
            freeze: '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/></svg>',
            holders: '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 00-3-3.87M16 3.13a4 4 0 010 7.75"/></svg>',
            age: '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>'
        };
        return icons[type] || '';
    }

    function createMetricBar(value, max, colorClass) {
        const percentage = Math.min((value / max) * 100, 100);
        return `<div class="metric-bar"><div class="metric-bar-fill ${colorClass}" style="width: 0%" data-width="${percentage}"></div></div>`;
    }

    function getMetricColorClass(field, value) {
        if (field === 'liquidity') {
            if (value >= 10000) return 'success';
            if (value >= 1000) return 'warning';
            return 'danger';
        }
        if (field === 'holders') {
            if (value <= 40) return 'success';
            if (value <= 60) return 'warning';
            return 'danger';
        }
        if (field === 'age') {
            if (value >= 24) return 'success';
            return 'warning';
        }
        if (typeof value === 'boolean') {
            return value ? 'success' : 'danger';
        }
        return 'neutral';
    }

    function formatLiquidity(liquidity, formatted) {
        if (formatted && formatted !== 'N/A') return formatted;
        if (!liquidity) return '$0';
        if (liquidity >= 1000000) return `$${(liquidity / 1000000).toFixed(2)}M`;
        if (liquidity >= 1000) return `$${(liquidity / 1000).toFixed(2)}K`;
        return `$${liquidity.toFixed(2)}`;
    }

    function formatAge(hours) {
        if (!hours || hours < 1) return '< 1h';
        if (hours < 24) return `${Math.round(hours)}h`;
        const days = Math.round(hours / 24);
        return `${days}d`;
    }

    function createTokenCard(token) {
        const verdict = token.verdict || 'UNKNOWN';
        const verdictClass = getVerdictClass(verdict);
        const score = token.score ?? 0;
        const birdeyeUrl = `https://birdeye.so/token/${token.address}`;
        const birdeyeHolderUrl = `https://birdeye.so/holder/${token.address}`;

        const verificados = {
            mint: token.mint_authority_revoked,
            freeze: token.freeze_authority_revoked
        };

        const liquidityFormatted = formatLiquidity(token.liquidity, token.liquidity_formatted);

        return `
            <article class="token-card" data-address="${token.address}">
                <div class="card-header">
                    <div class="token-info">
                        <h4 class="token-name">${token.name || 'Unknown Token'}</h4>
                        <span class="token-symbol">${token.symbol || '???'}</span>
                        <span class="token-address">${formatAddress(token.address)}</span>
                    </div>
                    <div class="verdict-badge ${verdictClass}">
                        ${verdict === 'SAFE' ? '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><path d="M20 6L9 17l-5-5"/></svg>' : ''}
                        ${verdict === 'CAUTION' ? '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><path d="M12 9v4M12 17h.01"/><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/></svg>' : ''}
                        ${verdict === 'RISKY' ? '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><path d="M18 6L6 18M6 6l12 12"/></svg>' : ''}
                        ${verdict === 'UNKNOWN' ? '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><circle cx="12" cy="12" r="10"/><path d="M12 8v4M12 16h.01"/></svg>' : ''}
                        <span>${verdict}</span>
                    </div>
                </div>

                <div class="score-section">
                    ${createScoreCircle(score, verdict)}
                    <div class="score-details">
                        <p class="score-title">Safety Analysis</p>
                        <p class="score-subtitle">Based on 6 risk factors</p>
                    </div>
                </div>

                <div class="metrics-grid">
                    <div class="metric">
                        <div class="metric-header">
                            <span class="metric-icon">${createMetricIcon('liquidity')}</span>
                            <span class="metric-label">Liquidity</span>
                        </div>
                        <span class="metric-value ${getMetricColorClass('liquidity', token.liquidity)}">${liquidityFormatted}</span>
                        ${createMetricBar(token.liquidity || 0, 100000, getMetricColorClass('liquidity', token.liquidity))}
                    </div>

                    <div class="metric">
                        <div class="metric-header">
                            <span class="metric-icon">${createMetricIcon('mint')}</span>
                            <span class="metric-label">Mint Auth</span>
                        </div>
                        <span class="metric-value ${getMetricColorClass('mint', verificados.mint)}">
                            ${verificados.mint ? 'Revoked' : 'Active'}
                        </span>
                    </div>

                    <div class="metric">
                        <div class="metric-header">
                            <span class="metric-icon">${createMetricIcon('freeze')}</span>
                            <span class="metric-label">Freeze Auth</span>
                        </div>
                        <span class="metric-value ${getMetricColorClass('freeze', verificados.freeze)}">
                            ${verificados.freeze ? 'Revoked' : 'Active'}
                        </span>
                    </div>

                    <div class="metric">
                        <div class="metric-header">
                            <span class="metric-icon">${createMetricIcon('holders')}</span>
                            <span class="metric-label">Top 10 Holders</span>
                        </div>
                        <span class="metric-value ${getMetricColorClass('holders', token.top_10_holders_pct)}">
                            ${token.top_10_holders_pct ? token.top_10_holders_pct.toFixed(1) + '%' : 'N/A'}
                        </span>
                        ${createMetricBar(token.top_10_holders_pct || 0, 100, getMetricColorClass('holders', token.top_10_holders_pct))}
                    </div>

                    <div class="metric">
                        <div class="metric-header">
                            <span class="metric-icon">${createMetricIcon('age')}</span>
                            <span class="metric-label">Contract Age</span>
                        </div>
                        <span class="metric-value ${getMetricColorClass('age', token.contract_age_hours)}">
                            ${formatAge(token.contract_age_hours)}
                        </span>
                    </div>

                    <div class="metric">
                        <div class="metric-header">
                            <span class="metric-icon">
                                <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
                                    <path d="M12 2v20M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6"/>
                                </svg>
                            </span>
                            <span class="metric-label">Price</span>
                        </div>
                        <span class="metric-value neutral">${token.price_formatted || 'N/A'}</span>
                    </div>
                </div>

                <div class="card-footer">
                    <a href="${birdeyeUrl}" target="_blank" rel="noopener noreferrer" class="card-link">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M18 13v6a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2h6"/>
                            <polyline points="15,3 21,3 21,9"/>
                            <line x1="10" y1="14" x2="21" y2="3"/>
                        </svg>
                        View on Birdeye
                    </a>
                    <a href="${birdeyeHolderUrl}" target="_blank" rel="noopener noreferrer" class="card-link">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/>
                            <circle cx="9" cy="7" r="4"/>
                            <path d="M23 21v-2a4 4 0 00-3-3.87M16 3.13a4 4 0 010 7.75"/>
                        </svg>
                        Holders
                    </a>
                </div>
            </article>
        `;
    }

    function renderTokens(tokens) {
        if (!tokens || tokens.length === 0) {
            elements.tokensGrid.innerHTML = `
                <div class="empty-state">
                    <svg width="64" height="64" viewBox="0 0 64 64" fill="none">
                        <circle cx="32" cy="32" r="28" stroke="currentColor" stroke-width="2" opacity="0.2"/>
                        <circle cx="32" cy="32" r="20" stroke="currentColor" stroke-width="2" opacity="0.3"/>
                        <circle cx="32" cy="32" r="12" stroke="currentColor" stroke-width="2" opacity="0.4"/>
                        <path d="M20 32 L28 40 L44 24" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" opacity="0.5"/>
                    </svg>
                    <p class="empty-text">No tokens found</p>
                    <p class="empty-subtext">Try scanning again</p>
                </div>
            `;
            return;
        }

        elements.tokensGrid.innerHTML = tokens.map(createTokenCard).join('');
        elements.resultsCount.textContent = `${tokens.length} tokens analyzed`;

        setTimeout(animateScoreCircles, 100);
        setTimeout(animateMetricBars, 100);
    }

    function animateScoreCircles() {
        $$('.score-circle-progress').forEach(circle => {
            const target = parseFloat(circle.dataset.target);
            circle.style.strokeDashoffset = target;
        });
    }

    function animateMetricBars() {
        $$('.metric-bar-fill').forEach(bar => {
            const width = bar.dataset.width;
            setTimeout(() => {
                bar.style.width = width + '%';
            }, 100);
        });
    }

    function setLoading(loading) {
        if (loading) {
            elements.scanBtn.classList.add('is-loading');
            elements.scanBtn.disabled = true;
        } else {
            elements.scanBtn.classList.remove('is-loading');
            elements.scanBtn.disabled = false;
        }
    }

    async function scanTokens() {
        if (isScanning) return;

        isScanning = true;
        setLoading(true);
        elements.resultsSection.classList.add('is-visible');

        try {
            const response = await fetch('/api/scan-new-tokens', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });

            const data = await response.json();

            if (data.error) {
                if (data.error.includes('API key')) {
                    showToast('API key not configured. Set BIRDEYE_API_KEY in Vercel settings.', 'error');
                } else {
                    showToast(data.error, 'error');
                }
                renderTokens([]);
                return;
            }

            if (data.total_api_calls !== undefined) {
                animateCounter(elements.apiCounterValue, data.total_api_calls);
            }

            renderTokens(data.tokens);

            const riskyCount = data.tokens.filter(t => t.verdict === 'RISKY').length;
            const safeCount = data.tokens.filter(t => t.verdict === 'SAFE').length;

            if (riskyCount > 0) {
                showToast(`Found ${riskyCount} risky token${riskyCount > 1 ? 's' : ''}!`, 'error', 4000);
            } else if (safeCount > 0) {
                showToast(`All ${safeCount} tokens passed safety check!`, 'info', 3000);
            }

        } catch (error) {
            console.error('Scan failed:', error);
            showToast('Scan failed. Check your connection and try again.', 'error');
            renderTokens([]);
        } finally {
            isScanning = false;
            setLoading(false);
        }
    }

    async function checkHealth() {
        try {
            const response = await fetch('/api/health');
            const data = await response.json();

            if (data.api_calls_made !== undefined) {
                elements.apiCounterValue.textContent = data.api_calls_made;
            }
        } catch (error) {
            console.warn('Health check failed:', error);
        }
    }

    if (elements.scanBtn) {
        elements.scanBtn.addEventListener('click', scanTokens);
    }

    document.addEventListener('keydown', (e) => {
        if (e.key === 's' && !e.ctrlKey && !e.metaKey && !e.altKey) {
            const activeElement = document.activeElement;
            const isInput = activeElement.tagName === 'INPUT' || activeElement.tagName === 'TEXTAREA';
            if (!isInput && !isScanning) {
                scanTokens();
            }
        }
    });

    checkHealth();

    if (window.location.hash === '#scan') {
        scanTokens();
    }

})();