/**
 * app.js — Jira Test Plan Generator Frontend
 * Handles: localStorage config, API calls, UI state, download
 */

'use strict';

// ── State ─────────────────────────────────────────────────────────────────
const STORAGE_KEY = 'jira_tpg_config';

let currentMarkdown = '';
let currentIssueId  = '';

// ── DOM References ────────────────────────────────────────────────────────
const jiraIdInput       = document.getElementById('jiraIdInput');
const generateBtn       = document.getElementById('generateBtn');
const generateBtnText   = document.getElementById('generateBtnText');
const generateBtnSpinner= document.getElementById('generateBtnSpinner');

const configBtn         = document.getElementById('configBtn');
const configModal       = document.getElementById('configModal');
const modalClose        = document.getElementById('modalClose');
const saveConfigBtn     = document.getElementById('saveConfigBtn');
const clearConfigBtn    = document.getElementById('clearConfigBtn');
const testConnectionBtn = document.getElementById('testConnectionBtn');

const baseUrlInput      = document.getElementById('baseUrlInput');
const emailInput        = document.getElementById('emailInput');
const tokenInput        = document.getElementById('tokenInput');
const authTypeInput     = document.getElementById('authTypeInput');
const toggleToken       = document.getElementById('toggleToken');
const emailGroup        = document.getElementById('emailGroup');
const tokenHint         = document.getElementById('tokenHint');

const segCloud          = document.getElementById('segCloud');
const segServer         = document.getElementById('segServer');
const validationResult  = document.getElementById('validationResult');

const errorBanner       = document.getElementById('errorBanner');
const errorMessage      = document.getElementById('errorMessage');
const errorClose        = document.getElementById('errorClose');

const resultCard        = document.getElementById('resultCard');
const resultBadge       = document.getElementById('resultBadge');
const resultTitle       = document.getElementById('resultTitle');
const testPlanOutput    = document.getElementById('testPlanOutput');
const downloadBtn       = document.getElementById('downloadBtn');
const copyBtn           = document.getElementById('copyBtn');
const saveFileBtn       = document.getElementById('saveFileBtn');
const saveFilePathInput = document.getElementById('saveFilePathInput');
const saveFileAlert     = document.getElementById('saveFileAlert');

const configStatus      = document.getElementById('configStatus');
const configDot         = document.getElementById('configDot');
const configLabel       = document.getElementById('configLabel');

// ── Config Persistence ────────────────────────────────────────────────────

function loadConfig() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch { return {}; }
}

function saveConfig(cfg) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(cfg));
}

function clearConfig() {
  localStorage.removeItem(STORAGE_KEY);
}

function applyConfigToForm(cfg) {
  baseUrlInput.value     = cfg.base_url  || '';
  emailInput.value       = cfg.email     || '';
  tokenInput.value       = cfg.token     || '';
  authTypeInput.value    = cfg.auth_type || 'cloud';
  setAuthType(cfg.auth_type || 'cloud');
}

function formToConfig() {
  return {
    base_url:  baseUrlInput.value.trim(),
    email:     emailInput.value.trim(),
    token:     tokenInput.value.trim(),
    auth_type: authTypeInput.value,
  };
}

function updateConfigStatusPill() {
  const cfg = loadConfig();
  if (cfg.base_url && cfg.token) {
    configDot.className = 'status-dot dot-configured';
    const user = cfg.email ? ` · ${cfg.email}` : '';
    configLabel.textContent = `Connected to ${cfg.base_url}${user}`;
  } else {
    configDot.className = 'status-dot dot-unconfigured';
    configLabel.textContent = 'Not configured — click ⚙️ Configure to add Jira credentials';
  }
}

// ── Auth Type Toggle ──────────────────────────────────────────────────────

function setAuthType(type) {
  authTypeInput.value = type;
  if (type === 'cloud') {
    segCloud.classList.add('active');
    segServer.classList.remove('active');
    emailGroup.style.display = 'flex';
    tokenHint.innerHTML = `Cloud: Generate at <a href="https://id.atlassian.com/manage-profile/security/api-tokens" target="_blank">Atlassian API Tokens</a>`;
  } else {
    segServer.classList.add('active');
    segCloud.classList.remove('active');
    emailGroup.style.display = 'none';
    tokenHint.innerHTML = `Server/DC: Use your <strong>Personal Access Token (PAT)</strong>`;
  }
}

segCloud.addEventListener('click',  () => setAuthType('cloud'));
segServer.addEventListener('click', () => setAuthType('server'));

// ── Token Visibility Toggle ───────────────────────────────────────────────

toggleToken.addEventListener('click', () => {
  const isPassword = tokenInput.type === 'password';
  tokenInput.type = isPassword ? 'text' : 'password';
  toggleToken.textContent = isPassword ? '🙈' : '👁';
});

// ── Modal Open / Close ────────────────────────────────────────────────────

function openModal() {
  const cfg = loadConfig();
  applyConfigToForm(cfg);
  clearValidationResult();
  configModal.classList.remove('hidden');
  setTimeout(() => baseUrlInput.focus(), 100);
}

function closeModal() {
  configModal.classList.add('hidden');
}

configBtn.addEventListener('click', openModal);
modalClose.addEventListener('click', closeModal);
configModal.addEventListener('click', e => {
  if (e.target === configModal) closeModal();
});
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') closeModal();
});

// ── Save Config ───────────────────────────────────────────────────────────

saveConfigBtn.addEventListener('click', () => {
  const cfg = formToConfig();
  if (!cfg.base_url) {
    showValidationResult('error', '⚠️ Please enter the Jira Base URL.');
    return;
  }
  if (!cfg.token) {
    showValidationResult('error', '⚠️ Please enter your API token.');
    return;
  }
  if (cfg.auth_type === 'cloud' && !cfg.email) {
    showValidationResult('error', '⚠️ Email is required for Jira Cloud.');
    return;
  }
  saveConfig(cfg);
  updateConfigStatusPill();
  closeModal();
});

// ── Clear Config ──────────────────────────────────────────────────────────

clearConfigBtn.addEventListener('click', () => {
  if (!confirm('Clear saved Jira configuration?')) return;
  clearConfig();
  applyConfigToForm({});
  clearValidationResult();
  updateConfigStatusPill();
});

// ── Test Connection ───────────────────────────────────────────────────────

testConnectionBtn.addEventListener('click', async () => {
  const cfg = formToConfig();
  if (!cfg.base_url || !cfg.token) {
    showValidationResult('error', '⚠️ Enter Base URL and Token first.');
    return;
  }

  testConnectionBtn.disabled = true;
  testConnectionBtn.textContent = '🔄 Testing…';
  clearValidationResult();

  try {
    const res = await fetch('/validate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(cfg),
    });
    const data = await res.json();
    if (data.success) {
      showValidationResult('success', `✅ Connected! Logged in as: ${data.user}`);
    } else {
      showValidationResult('error', `❌ ${data.error}`);
    }
  } catch (err) {
    showValidationResult('error', `❌ Network error: ${err.message}`);
  } finally {
    testConnectionBtn.disabled = false;
    testConnectionBtn.textContent = '🔌 Test Connection';
  }
});

function showValidationResult(type, message) {
  validationResult.className = `validation-result ${type}`;
  validationResult.textContent = message;
  validationResult.classList.remove('hidden');
}

function clearValidationResult() {
  validationResult.classList.add('hidden');
  validationResult.className = 'validation-result hidden';
  validationResult.textContent = '';
}

// ── Error Banner ──────────────────────────────────────────────────────────

function showError(message) {
  errorMessage.textContent = message;
  errorBanner.classList.remove('hidden');
  errorBanner.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function hideError() {
  errorBanner.classList.add('hidden');
}

errorClose.addEventListener('click', hideError);

// ── Jira Key Extractor ───────────────────────────────────────────────────

function extractJiraKey(input) {
  if (!input) return '';
  const match = input.match(/\b([a-zA-Z][a-zA-Z0-9]+-\d+)\b/);
  return match ? match[1].toUpperCase() : input.trim();
}

// ── Generate Test Plan ────────────────────────────────────────────────────

async function generateTestPlan() {
  const rawInput = jiraIdInput.value.trim();

  if (!rawInput) {
    showError('Please enter a Jira Issue ID (e.g. PROJECT-123 or KAN-1).');
    jiraIdInput.focus();
    return;
  }

  // Extract clean key if user pasted a sentence or URL (e.g. "create test plan for JIRA KAN-1")
  const jiraId = extractJiraKey(rawInput);
  if (jiraId && jiraId !== rawInput && /^[A-Z][A-Z0-9]+-\d+$/.test(jiraId)) {
    jiraIdInput.value = jiraId;
  }

  const cfg = loadConfig();

  if (!cfg.base_url || !cfg.token) {
    showError('Jira is not configured. Click ⚙️ Configure to add your Jira Base URL and API token.');
    openModal();
    return;
  }

  // Set loading state
  hideError();
  if (saveFileAlert) saveFileAlert.classList.add('hidden');
  setLoading(true);
  resultCard.classList.add('hidden');

  const payload = {
    jira_id:   jiraId,
    base_url:  cfg.base_url,
    auth_type: cfg.auth_type || 'cloud',
    email:     cfg.email || '',
    token:     cfg.token,
  };

  try {
    const res = await fetch('/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    const data = await res.json();

    if (data.success) {
      currentMarkdown = data.test_plan_markdown;
      currentIssueId  = data.issue_id || jiraId;

      resultBadge.textContent = currentIssueId;
      resultTitle.textContent = data.summary || currentIssueId;
      testPlanOutput.innerHTML = data.test_plan_html;

      // Update save path to convention TestPlanReport/TestPlan{JIRANAME}.md
      if (saveFilePathInput) {
        saveFilePathInput.value = `TestPlanReport/TestPlan${currentIssueId}.md`;
      }
      if (data.saved_to && saveFileAlert) {
        saveFileAlert.textContent = `✅ Auto-saved to: ${data.saved_to}`;
        saveFileAlert.className = 'save-file-banner success';
        saveFileAlert.classList.remove('hidden');
      }

      resultCard.classList.remove('hidden');
      resultCard.scrollIntoView({ behavior: 'smooth', block: 'start' });
    } else {
      showError(data.error || 'An unknown error occurred.');

      // If config error, open modal
      if (data.error_code === 'MISSING_CONFIG' || data.error_code === 'AUTH_FAILED') {
        openModal();
      }
    }
  } catch (err) {
    showError(`Could not connect to the local server. Is app.py running? (${err.message})`);
  } finally {
    setLoading(false);
  }
}

function setLoading(loading) {
  generateBtn.disabled = loading;
  if (loading) {
    generateBtnText.textContent = 'Generating…';
    generateBtnSpinner.classList.remove('hidden');
  } else {
    generateBtnText.textContent = 'Generate Test Plan';
    generateBtnSpinner.classList.add('hidden');
  }
}

generateBtn.addEventListener('click', generateTestPlan);

jiraIdInput.addEventListener('keydown', e => {
  if (e.key === 'Enter') generateTestPlan();
});

// ── Download Markdown ─────────────────────────────────────────────────────

downloadBtn.addEventListener('click', () => {
  if (!currentMarkdown) return;
  const blob = new Blob([currentMarkdown], { type: 'text/markdown;charset=utf-8' });
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement('a');
  a.href     = url;
  a.download = `test-plan-${currentIssueId || 'jira'}.md`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
});

// ── Copy Markdown ─────────────────────────────────────────────────────────

copyBtn.addEventListener('click', async () => {
  if (!currentMarkdown) return;
  try {
    await navigator.clipboard.writeText(currentMarkdown);
    copyBtn.textContent = '✅ Copied!';
    setTimeout(() => { copyBtn.textContent = '📋 Copy Markdown'; }, 2000);
  } catch {
    copyBtn.textContent = '❌ Failed';
    setTimeout(() => { copyBtn.textContent = '📋 Copy Markdown'; }, 2000);
  }
});

// ── Save to File Path ─────────────────────────────────────────────────────

saveFileBtn.addEventListener('click', async () => {
  if (!currentMarkdown) return;
  const defaultPath = currentIssueId ? `TestPlanReport/TestPlan${currentIssueId}.md` : 'TestPlanReport/TestPlanReport.md';
  const filePath = (saveFilePathInput.value || defaultPath).trim();
  saveFileBtn.disabled = true;
  saveFileBtn.textContent = 'Saving…';
  saveFileAlert.classList.add('hidden');
  saveFileAlert.className = 'save-file-banner hidden';

  try {
    const res = await fetch('/save', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ markdown: currentMarkdown, file_path: filePath, jira_id: currentIssueId })
    });
    const data = await res.json();
    if (data.success) {
      saveFileAlert.textContent = `✅ Saved to: ${data.file_path}`;
      saveFileAlert.className = 'save-file-banner success';
      saveFileAlert.classList.remove('hidden');
    } else {
      saveFileAlert.textContent = `❌ ${data.error || 'Failed to save file'}`;
      saveFileAlert.className = 'save-file-banner error';
      saveFileAlert.classList.remove('hidden');
    }
  } catch (err) {
    saveFileAlert.textContent = `❌ Network error: ${err.message}`;
    saveFileAlert.className = 'save-file-banner error';
    saveFileAlert.classList.remove('hidden');
  } finally {
    saveFileBtn.disabled = false;
    saveFileBtn.textContent = '💾 Save to File';
  }
});

// ── Init ──────────────────────────────────────────────────────────────────

updateConfigStatusPill();
jiraIdInput.focus();
