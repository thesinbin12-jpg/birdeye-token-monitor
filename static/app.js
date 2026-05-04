(function() {
'use strict';

var $ = function(s) { return document.querySelector(s); };
var $$ = function(s) { return document.querySelectorAll(s); };

var els = {
scanBtn: $('#scanBtn'),
searchBtn: $('#searchBtn'),
searchInput: $('#tokenSearch'),
apiCounter: $('#apiCounterValue'),
callsThisScan: $('#callsThisScan'),
results: $('#resultsSection'),
grid: $('#tokensGrid'),
count: $('#resultsCount'),
empty: $('#emptyState'),
toasts: $('#toastContainer'),
filterVerdict: $('#filterVerdict'),
sortBy: $('#sortBy'),
recentSearches: $('#recentSearches'),
recentList: $('#recentList'),
};

var allTokens = [];
var recentAddresses = [];
var isScanning = false;

function showToast(msg, type, dur) {
dur = dur || 5000;
type = type || 'info';
var t = document.createElement('div');
t.className = 'toast ' + type;
var ico = type === 'error'
? '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="20" height="20"><circle cx="12" cy="12" r="10"/><path d="M15 9l-6 6M9 9l6 6"/></svg>'
: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="20" height="20"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/></svg>';
t.innerHTML = '<span>' + ico + '</span><span class="toast-message">' + msg + '</span><button class="toast-close" aria-label="Close"><svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 6L6 18M6 6l12 12"/></svg></button>';
t.querySelector('.toast-close').addEventListener('click', function() { rmToast(t); });
els.toasts.appendChild(t);
if (dur > 0) setTimeout(function() { rmToast(t); }, dur);
}

function rmToast(t) {
t.style.animation = 'toastSlideIn .3s ease-out reverse';
setTimeout(function() { t.remove(); }, 300);
}

function animCtr(el, target, dur) {
dur = dur || 500;
var start = parseInt(el.textContent) || 0;
var diff = target - start;
if (diff === 0) { el.textContent = target; return; }
var t0 = performance.now();
function upd(now) {
var p = Math.min((now - t0) / dur, 1);
var e = 1 - Math.pow(1 - p, 3);
el.textContent = Math.round(start + diff * e);
if (p < 1) requestAnimationFrame(upd);
}
requestAnimationFrame(upd);
}

function vc(verdict) {
if (!verdict) return 'risky';
var v = verdict.toUpperCase();
if (v === 'STRONG BUY' || v === 'BUY') return 'safe';
if (v === 'HOLD' || v === 'CAUTION' || v === 'UNKNOWN' || v === 'ERROR') return 'caution';
return 'risky';
}

function fmtAddr(a) {
if (!a) return '';
if (a.length <= 16) return a;
return a.slice(0, 6) + '...' + a.slice(-4);
}

function fmtAge(h) {
if (!h || h < 1) return '< 1h';
if (h < 24) return Math.round(h) + 'h';
return Math.round(h / 24) + 'd';
}

function verdictIcon(verdict) {
var v = (verdict || '').toUpperCase();
if (v === 'STRONG BUY' || v === 'BUY') return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><path d="M20 6L9 17l-5-5"/></svg>';
if (v === 'HOLD' || v === 'CAUTION') return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><path d="M12 9v4M12 17h.01"/><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/></svg>';
return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><path d="M18 6L6 18M6 6l12 12"/></svg>';
}

function warningIcon(level) {
if (level === 'critical') return '&#x1F6A8;';
if (level === 'warning') return '&#x26A0;';
return '&#x2705;';
}

function metricIcon(type) {
var icons = {
liquidity: '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2v20M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6"/></svg>',
mint: '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0110 0v4"/></svg>',
freeze: '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/></svg>',
holders: '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 00-3-3.87M16 3.13a4 4 0 010 7.75"/></svg>',
age: '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>',
price: '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2v20M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6"/></svg>',
};
return icons[type] || '';
}

function getMetricClass(field, value) {
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
if (typeof value === 'boolean') return value ? 'success' : 'danger';
return 'neutral';
}

function categoryBarClass(score, max) {
var pct = score / max;
if (pct >= 0.7) return 'safe';
if (pct >= 0.4) return 'caution';
return 'risky';
}

function escHtml(s) {
var d = document.createElement('div');
d.textContent = s || '';
return d.innerHTML;
}

window.generateShareLink = function(idx) {
var token = allTokens[idx];
if (!token) return;
var rec = token.recommendation || {};
var text = token.name + ' (' + token.symbol + ') scored ' + token.score + '/100 on Token Safety Radar.\n' + (rec.label || '') + ': ' + (rec.text || '') + '\nTry it: ' + window.location.origin;
var url = 'https://twitter.com/intent/tweet?text=' + encodeURIComponent(text);
window.open(url, '_blank');
};

function buildAISection(token) {
if (!token.ai_insight) return '';
var src = token.ai_source || 'rules';
var badgeClass = src === 'groq' ? 'groq' : (src === 'unavailable' ? 'unavailable' : 'rules');
var badgeText = src === 'groq' ? 'AI' : (src === 'unavailable' ? 'N/A' : 'RULES');
var html = '<div class="card-section">';
html += '<div class="card-section-title"><svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2a7 7 0 017 7c0 2.38-1.19 4.47-3 5.74V17a2 2 0 01-2 2h-4a2 2 0 01-2-2v-2.26C6.19 13.47 5 11.38 5 9a7 7 0 017-7z"/><path d="M9 21h6"/></svg>AI Insight <span class="ai-badge ' + badgeClass + '">' + badgeText + '</span></div>';
html += '<div class="ai-insight">' + escHtml(token.ai_insight) + '</div>';
html += '</div>';
return html;
}

function buildSimSection(token) {
var sim = token.simulation;
if (!sim) return '';
var roiClass = sim.estimated_roi_24h >= 0 ? 'positive' : 'negative';
var riskClass = sim.risk_level === 'LOW' ? 'positive' : (sim.risk_level === 'EXTREME' || sim.risk_level === 'HIGH' ? 'negative' : 'neutral');
var html = '<div class="card-section">';
html += '<div class="card-section-title"><svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2v20M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6"/></svg>$100 Simulation</div>';
html += '<div class="sim-grid">';
html += '<div class="sim-item"><span class="sim-label">Tokens</span><span class="sim-value neutral">' + (sim.tokens_received || 0).toLocaleString() + '</span></div>';
html += '<div class="sim-item"><span class="sim-label">Est. 24h Value</span><span class="sim-value ' + roiClass + '">$' + (sim.estimated_value_24h || 0).toFixed(2) + '</span></div>';
html += '<div class="sim-item"><span class="sim-label">Est. ROI</span><span class="sim-value ' + roiClass + '">' + (sim.estimated_roi_24h >= 0 ? '+' : '') + (sim.estimated_roi_24h || 0) + '%</span></div>';
html += '<div class="sim-item"><span class="sim-label">Risk</span><span class="sim-value ' + riskClass + '">' + (sim.risk_level || 'N/A') + '</span></div>';
html += '<div class="sim-item"><span class="sim-label">Best Case</span><span class="sim-value positive">+' + (sim.best_case_roi || 0) + '%</span></div>';
html += '<div class="sim-item"><span class="sim-label">Worst Case</span><span class="sim-value negative">' + (sim.worst_case_roi || 0) + '%</span></div>';
html += '<div class="sim-item"><span class="sim-label">Exit Possible</span><span class="sim-value ' + (sim.exit_possible ? 'positive' : 'negative') + '">' + (sim.exit_possible ? 'Yes' : 'No') + '</span></div>';
html += '<div class="sim-item"><span class="sim-label">Prob. Loss</span><span class="sim-value ' + ((sim.prob_loss || 0) > 50 ? 'negative' : 'neutral') + '">' + (sim.prob_loss || 0) + '%</span></div>';
html += '</div>';
if (sim.scenario) html += '<div class="sim-scenario">' + escHtml(sim.scenario) + '</div>';
html += '</div>';
return html;
}

function buildPatternsSection(token) {
var pat = token.patterns;
if (!pat) return '';
var html = '<div class="card-section">';
html += '<div class="card-section-title"><svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>Pattern Detection</div>';
html += '<div class="pattern-list">';
var patterns = [pat.rug_pull, pat.honeypot, pat.pump_dump];
var names = ['Rug Pull', 'Honeypot', 'Pump & Dump'];
for (var i = 0; i < patterns.length; i++) {
var p = patterns[i];
if (!p) continue;
html += '<div class="pattern-item ' + (p.risk || 'NONE') + '"><span class="pattern-name">' + names[i] + '</span><span class="pattern-risk">' + (p.risk || 'NONE') + '</span></div>';
}
html += '</div>';
if (pat.overall_summary) html += '<div style="font-size:.75rem;color:var(--text2);margin-top:.35rem;padding-top:.35rem;border-top:1px solid var(--border)">' + escHtml(pat.overall_summary) + '</div>';
html += '</div>';
return html;
}

function buildComparativeSection(token) {
var comp = token.comparative;
if (!comp) return '';
var pctClass = comp.percentile >= 75 ? 'safe' : (comp.percentile >= 25 ? 'caution' : 'risky');
var html = '<div class="card-section comparative-section">';
html += '<div class="card-section-title"><svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 20V10M12 20V4M6 20v-6"/></svg>Batch Comparison</div>';
html += '<div style="display:flex;align-items:center;gap:.5rem;margin-bottom:.5rem"><span class="comp-percentile ' + pctClass + '">P' + (comp.percentile || 50) + '</span><span style="font-size:.85rem;color:var(--text2)">' + escHtml(comp.percentile_label || '') + '</span></div>';
if (comp.comparisons && comp.comparisons.length) {
for (var i = 0; i < comp.comparisons.length; i++) {
html += '<div class="comp-item">' + escHtml(comp.comparisons[i]) + '</div>';
}
}
html += '</div>';
return html;
}

function createTokenCard(token, idx) {
var verdict = token.verdict || 'UNKNOWN';
var vClass = vc(verdict);
var score = token.score || 0;
var birdeyeUrl = 'https://birdeye.so/token/' + token.address;
var holderUrl = 'https://birdeye.so/holder/' + token.address;
var rec = token.recommendation || { label: verdict, text: '' };
var recClass = vClass;
var warnings = token.warnings || [];

var circumference = 2 * Math.PI * 34;
var offset = circumference - (score / 100) * circumference;

var logoHtml = token.logo_uri
? '<img class="token-logo" src="' + token.logo_uri + '" alt="" onerror="this.style.display=\'none\'">'
: '<div class="token-logo" style="background:var(--bg2);display:flex;align-items:center;justify-content:center;font-size:.7rem;color:var(--muted)">' + (token.symbol || '?').slice(0, 2) + '</div>';

var warningsHtml = '';
if (warnings.length > 0) {
warningsHtml = '<div class="warnings-list">';
for (var w = 0; w < warnings.length; w++) {
var warn = warnings[w];
warningsHtml += '<div class="warning-item ' + warn.level + '"><span class="warning-icon">' + warningIcon(warn.level) + '</span><span>' + warn.text + '</span></div>';
}
warningsHtml += '</div>';
}

var secScore = token.security_score || 0;
var distScore = token.distribution_score || 0;
var liqScore = token.liquidity_score || 0;
var momScore = token.momentum_score || 0;

var catHtml = '';
var categories = [
{ label: 'Security', score: secScore, max: 40 },
{ label: 'Distribution', score: distScore, max: 25 },
{ label: 'Liquidity', score: liqScore, max: 20 },
{ label: 'Momentum', score: momScore, max: 15 },
];
for (var c = 0; c < categories.length; c++) {
var cat = categories[c];
var pct = Math.round((cat.score / cat.max) * 100);
var barClass = categoryBarClass(cat.score, cat.max);
catHtml += '<div class="category-score">' +
'<span class="category-label">' + cat.label + '</span>' +
'<div class="category-bar-bg"><div class="category-bar-fill ' + barClass + '" style="width:0%" data-width="' + pct + '"></div></div>' +
'<span class="category-val">' + cat.score + '/' + cat.max + '</span>' +
'</div>';
}

var aiHtml = buildAISection(token);
var simHtml = buildSimSection(token);
var patHtml = buildPatternsSection(token);
var compHtml = buildComparativeSection(token);

return '<article class="token-card" data-address="' + token.address + '" data-verdict="' + verdict + '" data-score="' + score + '" data-liq="' + (token.liquidity || 0) + '" data-holders="' + (token.top_10_holders_pct || 0) + '" data-age="' + (token.contract_age_hours || 0) + '">' +
'<div class="card-header">' +
'<div class="token-info">' +
logoHtml +
'<div class="token-info-text">' +
'<h4 class="token-name" title="' + escHtml(token.name || 'Unknown') + '">' + escHtml(token.name || 'Unknown') + '</h4>' +
'<span class="token-symbol">' + escHtml(token.symbol || '???') + '</span>' +
'<span class="token-address" title="Click to copy" onclick="navigator.clipboard.writeText(\'' + token.address + '\')">' + fmtAddr(token.address) + '</span>' +
'</div>' +
'</div>' +
'<div class="verdict-badge ' + vClass + '">' + verdictIcon(verdict) + '<span>' + verdict + '</span></div>' +
'</div>' +
'<div class="recommendation-bar ' + recClass + '">' +
'<span>' + rec.label + ':</span> <span>' + rec.text + '</span>' +
'</div>' +
'<div class="score-section">' +
'<div class="score-circle">' +
'<svg width="80" height="80" viewBox="0 0 80 80">' +
'<circle class="score-circle-bg" cx="40" cy="40" r="34"/>' +
'<circle class="score-circle-progress ' + vClass + '" cx="40" cy="40" r="34" stroke-dasharray="' + circumference + '" stroke-dashoffset="' + circumference + '" data-target="' + offset + '"/>' +
'</svg>' +
'<div class="score-circle-text">' +
'<span class="score-value ' + vClass + '">' + score + '</span>' +
'<span class="score-label">Score</span>' +
'</div>' +
'</div>' +
'<div class="score-details">' + catHtml + '</div>' +
'</div>' +
'<div class="metrics-grid">' +
'<div class="metric"><div class="metric-header"><span class="metric-icon">' + metricIcon('liquidity') + '</span><span class="metric-label">Liquidity</span></div><span class="metric-value ' + getMetricClass('liquidity', token.liquidity) + '">' + (token.liquidity_formatted || 'N/A') + '</span></div>' +
'<div class="metric"><div class="metric-header"><span class="metric-icon">' + metricIcon('mint') + '</span><span class="metric-label">Mint Auth</span></div><span class="metric-value ' + getMetricClass('mint', token.mint_authority_revoked) + '">' + (token.mint_authority_revoked ? 'Revoked' : 'Active') + '</span></div>' +
'<div class="metric"><div class="metric-header"><span class="metric-icon">' + metricIcon('freeze') + '</span><span class="metric-label">Freeze Auth</span></div><span class="metric-value ' + getMetricClass('freeze', token.freeze_authority_revoked) + '">' + (token.freeze_authority_revoked ? 'Revoked' : 'Active') + '</span></div>' +
'<div class="metric"><div class="metric-header"><span class="metric-icon">' + metricIcon('holders') + '</span><span class="metric-label">Top 10 Holders</span></div><span class="metric-value ' + getMetricClass('holders', token.top_10_holders_pct) + '">' + (token.top_10_holders_pct ? token.top_10_holders_pct.toFixed(1) + '%' : 'N/A') + '</span></div>' +
'<div class="metric"><div class="metric-header"><span class="metric-icon">' + metricIcon('age') + '</span><span class="metric-label">Contract Age</span></div><span class="metric-value ' + getMetricClass('age', token.contract_age_hours) + '">' + fmtAge(token.contract_age_hours) + '</span></div>' +
'<div class="metric"><div class="metric-header"><span class="metric-icon">' + metricIcon('price') + '</span><span class="metric-label">Price</span></div><span class="metric-value neutral">' + (token.price_formatted || 'N/A') + '</span></div>' +
'</div>' +
aiHtml +
simHtml +
patHtml +
compHtml +
warningsHtml +
'<div class="card-footer">' +
'<a href="' + birdeyeUrl + '" target="_blank" rel="noopener noreferrer" class="card-link"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 13v6a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2h6"/><polyline points="15,3 21,3 21,9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>Birdeye</a>' +
'<a href="' + holderUrl + '" target="_blank" rel="noopener noreferrer" class="card-link"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 00-3-3.87M16 3.13a4 4 0 010 7.75"/></svg>Holders</a>' +
'<button onclick="generateShareLink(' + idx + ')" class="card-link share-btn"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 12v8a2 2 0 002 2h12a2 2 0 002-2v-8"/><polyline points="16,6 12,2 8,6"/><line x1="12" y1="2" x2="12" y2="15"/></svg>Share</button>' +
'</div>' +
'</article>';
}

function renderTokens(tokens) {
if (!tokens || tokens.length === 0) {
els.grid.innerHTML = '<div class="empty-state"><svg width="64" height="64" viewBox="0 0 64 64" fill="none"><circle cx="32" cy="32" r="28" stroke="currentColor" stroke-width="2" opacity="0.2"/><circle cx="32" cy="32" r="20" stroke="currentColor" stroke-width="2" opacity="0.3"/><circle cx="32" cy="32" r="12" stroke="currentColor" stroke-width="2" opacity="0.4"/><path d="M20 32 L28 40 L44 24" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" opacity="0.5"/></svg><p class="empty-text">No tokens found</p><p class="empty-subtext">Try scanning again or search a specific token</p></div>';
return;
}

var html = '';
for (var i = 0; i < tokens.length; i++) {
var globalIdx = allTokens.indexOf(tokens[i]);
if (globalIdx < 0) globalIdx = i;
html += createTokenCard(tokens[i], globalIdx);
}
els.grid.innerHTML = html;
els.count.textContent = tokens.length + ' tokens analyzed';

setTimeout(animateScoreCircles, 100);
setTimeout(animateCategoryBars, 150);
}

function animateScoreCircles() {
$$('.score-circle-progress').forEach(function(circle) {
var target = parseFloat(circle.dataset.target);
circle.style.strokeDashoffset = target;
});
}

function animateCategoryBars() {
$$('.category-bar-fill').forEach(function(bar) {
var width = bar.dataset.width;
setTimeout(function() { bar.style.width = width + '%'; }, 50);
});
}

function setLoading(loading) {
if (loading) {
els.scanBtn.classList.add('is-loading');
els.scanBtn.disabled = true;
els.searchBtn.disabled = true;
} else {
els.scanBtn.classList.remove('is-loading');
els.scanBtn.disabled = false;
els.searchBtn.disabled = false;
}
}

function applyFiltersAndSort() {
var verdictFilter = els.filterVerdict.value;
var sortVal = els.sortBy.value;

var filtered = allTokens.slice();

if (verdictFilter !== 'all') {
filtered = filtered.filter(function(t) {
return (t.verdict || '').toUpperCase() === verdictFilter;
});
}

filtered.sort(function(a, b) {
switch (sortVal) {
case 'score-desc': return (b.score || 0) - (a.score || 0);
case 'score-asc': return (a.score || 0) - (b.score || 0);
case 'age-asc': return (a.contract_age_hours || 9999) - (b.contract_age_hours || 9999);
case 'liq-desc': return (b.liquidity || 0) - (a.liquidity || 0);
case 'holders-asc': return (a.top_10_holders_pct || 999) - (b.top_10_holders_pct || 999);
default: return 0;
}
});

renderTokens(filtered);
}

async function scanTokens() {
if (isScanning) return;
isScanning = true;
setLoading(true);
els.results.classList.add('is-visible');

try {
var response = await fetch('/api/scan-new-tokens', { method: 'POST', headers: { 'Content-Type': 'application/json' } });
var data = await response.json();

if (data.error) {
showToast(data.error.includes('API key') ? 'API key not configured. Set BIRDEYE_API_KEY in Vercel settings.' : data.error, 'error');
renderTokens([]);
return;
}

if (data.total_api_calls !== undefined) animCtr(els.apiCounter, data.total_api_calls);
if (data.calls_this_scan !== undefined) els.callsThisScan.textContent = data.calls_this_scan + ' calls';

allTokens = data.tokens || [];
applyFiltersAndSort();

var riskyCount = allTokens.filter(function(t) { return (t.verdict || '').indexOf('AVOID') >= 0; }).length;
var safeCount = allTokens.filter(function(t) { return (t.verdict || '') === 'STRONG BUY' || (t.verdict || '') === 'BUY'; }).length;

if (riskyCount > 0) showToast('Found ' + riskyCount + ' token' + (riskyCount > 1 ? 's' : '') + ' to AVOID!', 'error', 4000);
else if (safeCount > 0) showToast(safeCount + ' token' + (safeCount > 1 ? 's' : '') + ' look safe!', 'info', 3000);

} catch (error) {
console.error('Scan failed:', error);
showToast('Scan failed. Check your connection and try again.', 'error');
renderTokens([]);
} finally {
isScanning = false;
setLoading(false);
}
}

async function searchToken() {
var address = els.searchInput.value.trim();
if (!address) {
showToast('Please enter a token address', 'error', 3000);
return;
}
if (address.length < 32) {
showToast('Address must be at least 32 characters', 'error', 3000);
return;
}

if (isScanning) return;
isScanning = true;
setLoading(true);
els.results.classList.add('is-visible');

try {
var response = await fetch('/api/analyze-token/' + encodeURIComponent(address));
var data = await response.json();

if (data.error) {
showToast(data.error, 'error');
return;
}

if (data.total_api_calls !== undefined) animCtr(els.apiCounter, data.total_api_calls);
if (data.calls_this_scan !== undefined) els.callsThisScan.textContent = data.calls_this_scan + ' calls';

var newTokens = data.tokens || [];
var existing = allTokens.findIndex(function(t) { return t.address === address; });
if (existing >= 0) {
allTokens[existing] = newTokens[0];
} else {
allTokens = newTokens.concat(allTokens);
}

addRecentSearch(address, newTokens[0]);
applyFiltersAndSort();

if (newTokens.length > 0 && newTokens[0].verdict) {
var v = newTokens[0].verdict;
if (v.indexOf('AVOID') >= 0) showToast('This token has red flags!', 'error', 4000);
else if (v === 'STRONG BUY' || v === 'BUY') showToast('This token looks safe!', 'info', 3000);
}

} catch (error) {
console.error('Search failed:', error);
showToast('Search failed. Check the address and try again.', 'error');
} finally {
isScanning = false;
setLoading(false);
els.searchInput.value = '';
}
}

function addRecentSearch(address, token) {
var existing = recentAddresses.findIndex(function(r) { return r.address === address; });
if (existing >= 0) recentAddresses.splice(existing, 1);

recentAddresses.unshift({
address: address,
symbol: token ? (token.symbol || '???') : '???',
});

if (recentAddresses.length > 5) recentAddresses = recentAddresses.slice(0, 5);
renderRecentSearches();

try { localStorage.setItem('recentSearches', JSON.stringify(recentAddresses)); } catch (e) {}
}

function renderRecentSearches() {
if (recentAddresses.length === 0) {
els.recentSearches.style.display = 'none';
return;
}
els.recentSearches.style.display = 'flex';
els.recentList.innerHTML = recentAddresses.map(function(r) {
return '<span class="recent-chip" data-address="' + r.address + '">' + r.symbol + '</span>';
}).join('');

$$('.recent-chip').forEach(function(chip) {
chip.addEventListener('click', function() {
els.searchInput.value = chip.dataset.address;
searchToken();
});
});
}

function loadRecentSearches() {
try {
var stored = localStorage.getItem('recentSearches');
if (stored) {
recentAddresses = JSON.parse(stored);
renderRecentSearches();
}
} catch (e) {}
}

async function checkHealth() {
try {
var response = await fetch('/api/health');
var data = await response.json();
if (data.api_calls_made !== undefined) els.apiCounter.textContent = data.api_calls_made;
} catch (e) {
console.warn('Health check failed:', e);
}
}

els.scanBtn.addEventListener('click', scanTokens);
els.searchBtn.addEventListener('click', searchToken);
els.searchInput.addEventListener('keydown', function(e) {
if (e.key === 'Enter') searchToken();
});

els.filterVerdict.addEventListener('change', applyFiltersAndSort);
els.sortBy.addEventListener('change', applyFiltersAndSort);

document.addEventListener('keydown', function(e) {
if (e.key === 's' && !e.ctrlKey && !e.metaKey && !e.altKey) {
var active = document.activeElement;
var isInput = active.tagName === 'INPUT' || active.tagName === 'TEXTAREA' || active.tagName === 'SELECT';
if (!isInput && !isScanning) scanTokens();
}
});

loadRecentSearches();
checkHealth();

if (window.location.hash === '#scan') scanTokens();

})();
