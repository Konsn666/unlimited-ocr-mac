/* ── State ──────────────────────────────────────── */
const state = {
  sessionId: null,
  totalPages: 0,
  currentPage: 1,
  scanning: false,
  pageResults: {},       // page_num → { detections, html, translated }
  pageImageUrls: {},     // page_num → image URL
  targetLang: '',
};

/* ── DOM refs ───────────────────────────────────── */
const $ = id => document.getElementById(id);
const fileInput    = $('file-input');
const scanBtn      = $('scan-btn');
const prevBtn      = $('prev-page');
const nextBtn      = $('next-page');
const pageInd      = $('page-indicator');
const transLang    = $('translate-lang');
const transBtn     = $('translate-btn');
const exportBtn    = $('export-btn');
const srcImg       = $('source-image');
const srcPlaceholder = $('source-placeholder');
const ocrContent   = $('ocr-content');
const progressBar  = $('progress-bar');
const progressFill = $('progress-fill');
const progressText = $('progress-text');
const statusText   = $('status-text');
const modelInfo    = $('model-info');
const divider      = $('divider');
const toast        = $('toast');

/* ── Init ───────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  fileInput.addEventListener('change', handleUpload);
  scanBtn.addEventListener('click', startScan);
  prevBtn.addEventListener('click', () => goToPage(state.currentPage - 1));
  nextBtn.addEventListener('click', () => goToPage(state.currentPage + 1));
  transBtn.addEventListener('click', translatePage);
  exportBtn.addEventListener('click', showExportDialog);
  transLang.addEventListener('change', () => {
    state.targetLang = transLang.value;
    transBtn.disabled = !state.targetLang || !state.sessionId;
  });
  setupDivider();
  setupKeyboard();
  checkHealth();
});

/* ── Health check ───────────────────────────────── */
async function checkHealth() {
  try {
    const r = await fetch('/api/health');
    const d = await r.json();
    statusText.textContent = d.model_loaded ? '模型已就绪' : '模型加载中...';
    if (d.device) modelInfo.textContent = `${d.device}`;
  } catch { statusText.textContent = '连接服务器...'; }
}

/* ── Upload ─────────────────────────────────────── */
async function handleUpload(e) {
  const file = e.target.files[0];
  if (!file) return;

  statusText.textContent = '上传中...';
  const form = new FormData();
  form.append('file', file);

  try {
    const r = await fetch('/api/upload', { method: 'POST', body: form });
    const d = await r.json();
    if (d.error) { showToast(d.error); return; }

    state.sessionId = d.session_id;
    state.totalPages = d.total_pages;
    state.currentPage = 1;
    state.pageResults = {};

    for (let i = 1; i <= d.total_pages; i++) {
      state.pageImageUrls[i] = `/api/page-image/${d.session_id}/${i}`;
    }

    if (d.total_pages >= 1) loadPageImage(1);

    scanBtn.disabled = false;
    pageInd.textContent = `1 / ${d.total_pages}`;
    prevBtn.disabled = true;
    nextBtn.disabled = d.total_pages <= 1;
    transBtn.disabled = !state.targetLang;
    exportBtn.disabled = true;
    statusText.textContent = `已上传: ${d.source_name} (${d.total_pages} 页)`;
    ocrContent.innerHTML = '<p class="placeholder">点击「开始扫描」识别文档内容</p>';
  } catch (err) {
    showToast('上传失败: ' + err.message);
  }
}

/* ── Scan (SSE) — real-time line-by-line ────────── */
async function startScan() {
  if (state.scanning) return;
  state.scanning = true;
  scanBtn.disabled = true;
  scanBtn.textContent = '⏳ 扫描中...';
  progressBar.classList.remove('hidden');
  progressFill.style.width = '0%';
  progressText.textContent = '准备中...';

  try {
    const r = await fetch('/api/scan', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: state.sessionId }),
    });

    const reader = r.body.getReader();
    const decoder = new TextDecoder();
    let buf = '';

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true });

      while (true) {
        const boundary = buf.includes('\r\n\r\n') ? '\r\n\r\n' : (buf.includes('\n\n') ? '\n\n' : null);
        if (!boundary) break;
        const idx = buf.indexOf(boundary);
        if (idx === -1) break;
        const chunk = buf.substring(0, idx);
        buf = buf.substring(idx + boundary.length);
        if (chunk.trim()) handleSSEChunk(chunk);
      }
    }
    if (buf.trim()) handleSSEChunk(buf);
  } catch (err) {
    showToast('扫描出错: ' + err.message);
  }

  state.scanning = false;
  scanBtn.disabled = false;
  scanBtn.textContent = '🚀 开始扫描';
  progressBar.classList.add('hidden');
  exportBtn.disabled = false;
  statusText.textContent = `扫描完成 (${state.totalPages} 页)`;
}

function handleSSEChunk(chunk) {
  const lines = chunk.split(/\r?\n/);
  let eventType = '';
  let dataStr = '';

  for (const line of lines) {
    if (line.startsWith('event:')) eventType = line.slice(6).trim();
    else if (line.startsWith('data:')) dataStr = line.slice(5).trim();
    else if (line.startsWith(':')) continue;
  }

  if (!eventType || !dataStr) return;
  let data;
  try { data = JSON.parse(dataStr); } catch { return; }

  switch (eventType) {
    case 'page_start':
      progressText.textContent = `扫描第 ${data.page_num} / ${data.total_pages} 页...`;
      progressFill.style.width = `${(data.page_num - 1) / data.total_pages * 100}%`;
      state.currentPage = data.page_num;
      pageInd.textContent = `${data.page_num} / ${data.total_pages}`;
      loadPageImage(data.page_num);
      // Clear right panel for this page, create container
      ocrContent.innerHTML = `<div class="ocr-page" data-page="${data.page_num}"></div>`;
      break;

    case 'page_progress':
      const statusMap = { scanning: 'OCR识别中', parsing: '解析结果中', converting: '转换中' };
      progressText.textContent = `第 ${data.page_num} 页 - ${statusMap[data.status] || data.status}`;
      break;

    case 'det_result':
      // Append this single detection line to the current page container
      appendDetection(data);
      break;

    case 'page_done':
      // Store full results
      state.pageResults[data.page_num] = {
        detections: state.pageResults[data.page_num]?.detections || [],
        html: data.html,
      };
      // Re-render with full HTML (includes proper structure) and re-attach edit listeners
      ocrContent.innerHTML = data.html;
      attachEditListeners();
      break;

    case 'page_image':
      state.pageImageUrls[data.page_num] = data.image_url;
      if (data.page_num === state.currentPage) loadPageImage(data.page_num);
      break;

    case 'scan_complete':
      progressFill.style.width = '100%';
      progressText.textContent = '扫描完成!';
      exportBtn.disabled = false;
      break;

    case 'error':
      showToast(`第 ${data.page_num} 页出错: ${data.message}`);
      break;
  }
}

/* ── Append a single detection to the right panel ── */
function appendDetection(data) {
  const page = data.page_num;
  const det = data.detection;
  const detHtml = data.html;

  // Track detections for this page
  if (!state.pageResults[page]) state.pageResults[page] = { detections: [] };
  state.pageResults[page].detections.push(det);

  // Find or create the page container
  let container = ocrContent.querySelector(`.ocr-page[data-page="${page}"]`);
  if (!container) {
    ocrContent.innerHTML = `<div class="ocr-page" data-page="${page}"></div>`;
    container = ocrContent.querySelector(`.ocr-page[data-page="${page}"]`);
  }

  // Append the detection HTML
  container.insertAdjacentHTML('beforeend', detHtml);

  // Auto-scroll right panel to bottom
  ocrContent.scrollTop = ocrContent.scrollHeight;
}

/* ── Render ─────────────────────────────────────── */
function renderOCRContent(html) {
  ocrContent.innerHTML = html;
  attachEditListeners();
}

function loadPageImage(pageNum) {
  const url = state.pageImageUrls[pageNum];
  if (url) {
    srcImg.onload = () => {
      srcImg.classList.add('loaded');
      srcPlaceholder.style.display = 'none';
    };
    srcImg.onerror = () => {
      srcImg.classList.remove('loaded');
      srcPlaceholder.style.display = '';
    };
    srcImg.src = url;
  }
}

function goToPage(num) {
  if (num < 1 || num > state.totalPages) return;
  state.currentPage = num;
  pageInd.textContent = `${num} / ${state.totalPages}`;
  prevBtn.disabled = num <= 1;
  nextBtn.disabled = num >= state.totalPages;

  loadPageImage(num);

  const result = state.pageResults[num];
  if (result?.html) {
    renderOCRContent(result.html);
    if (result.translated) applyTranslations(result.translated);
  } else if (result?.detections?.length) {
    // Page was being scanned (partial), show what we have
    ocrContent.innerHTML = `<div class="ocr-page" data-page="${num}"></div>`;
    const container = ocrContent.querySelector(`.ocr-page[data-page="${num}"]`);
    result.detections.forEach((det, i) => {
      const detHtml = buildDetHtml(det, i);
      container.insertAdjacentHTML('beforeend', detHtml);
    });
  } else {
    ocrContent.innerHTML = '<p class="placeholder">此页尚未扫描</p>';
  }
}

function buildDetHtml(det, index) {
  const t = det.type;
  const text = det.text || '';
  const esc = s => s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  if (t === 'title') {
    const bbox = det.bbox || [];
    const h = (bbox[3] - bbox[1]) || 0;
    const tag = h > 60 ? 'h1' : 'h2';
    return `<${tag} class="ocr-heading" contenteditable="true" data-detection-index="${index}">${esc(text)}</${tag}>`;
  }
  if (t === 'image') return `<div class="ocr-image" data-detection-index="${index}"><span class="image-placeholder">🖼 图片区域</span></div>`;
  if (t === 'table') return `<div class="ocr-table" contenteditable="true" data-detection-index="${index}">${esc(text)}</div>`;
  if (t === 'page_number') return `<span class="ocr-page-number" data-detection-index="${index}">${esc(text)}</span>`;
  return `<p class="ocr-text" contenteditable="true" data-detection-index="${index}">${esc(text)}</p>`;
}

/* ── Inline Edit ────────────────────────────────── */
function attachEditListeners() {
  ocrContent.querySelectorAll('[contenteditable="true"]').forEach(el => {
    el.addEventListener('blur', () => {
      const idx = parseInt(el.dataset.detectionIndex);
      const page = state.currentPage;
      const result = state.pageResults[page];
      if (!result?.detections?.[idx]) return;
      const original = result.detections[idx].text || '';
      const newText = el.innerText.trim();
      if (newText !== original && newText !== '') saveEdit(page, idx, newText);
    });
    el.addEventListener('keydown', e => {
      if (e.key === 'Enter' && el.tagName === 'P') { e.preventDefault(); el.blur(); }
    });
  });
}

async function saveEdit(pageNum, detectionIndex, newText) {
  try {
    await fetch('/api/edit', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: state.sessionId, page_num: pageNum, detection_index: detectionIndex, new_text: newText }),
    });
    const result = state.pageResults[pageNum];
    if (result?.detections?.[detectionIndex]) result.detections[detectionIndex].text = newText;
    showToast('已保存');
  } catch { showToast('保存失败'); }
}

/* ── Translate (bilingual) ──────────────────────── */
async function translatePage() {
  const lang = state.targetLang;
  if (!lang || !state.sessionId) return;
  const page = state.currentPage;
  const result = state.pageResults[page];
  if (!result?.detections?.length) { showToast('此页未扫描'); return; }

  // Toggle off if already translated
  if (result.translated) {
    delete result.translated;
    if (result.html) renderOCRContent(result.html);
    else ocrContent.innerHTML = '<p class="placeholder">无结果</p>';
    transBtn.textContent = '🌐 翻译';
    return;
  }

  transBtn.disabled = true;
  transBtn.textContent = '⏳ 翻译中...';
  statusText.textContent = `翻译第 ${page} 页...`;

  try {
    const r = await fetch('/api/translate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: state.sessionId,
        page_num: page,
        source_lang: 'auto',
        target_lang: lang,
        detections: result.detections,
      }),
    });
    const d = await r.json();
    if (d.error) { showToast(d.error); return; }

    state.pageResults[page].translated = d.translated_detections;
    applyTranslations(d.translated_detections);
    transBtn.textContent = '🌐 取消翻译';
    showToast('翻译完成');
  } catch (err) {
    showToast('翻译失败: ' + err.message);
  } finally {
    transBtn.disabled = false;
    statusText.textContent = '就绪';
  }
}

function applyTranslations(translations) {
  if (!translations) return;
  ocrContent.querySelectorAll('.translated-text').forEach(el => el.remove());

  for (const t of translations) {
    const el = ocrContent.querySelector(`[data-detection-index="${t.index}"]`);
    if (el && t.translated && t.translated !== t.original) {
      // Wrap original + translation in a pair container for tight layout
      const pair = document.createElement('div');
      pair.className = 'ocr-pair';
      el.parentNode.insertBefore(pair, el);
      pair.appendChild(el);
      const div = document.createElement('div');
      div.className = 'translated-text';
      div.textContent = t.translated;
      pair.appendChild(div);
    }
  }
}

/* ── Export with mode selection ──────────────────── */
function showExportDialog() {
  const hasTranslation = Object.values(state.pageResults).some(r => r.translated);

  if (!hasTranslation) {
    doExport('original');
    return;
  }

  const existing = document.getElementById('export-dialog');
  if (existing) existing.remove();

  const dialog = document.createElement('div');
  dialog.id = 'export-dialog';
  dialog.innerHTML = `
    <div class="export-dialog-content">
      <h3>选择导出模式</h3>
      <label><input type="radio" name="export-mode" value="original" checked> 仅原文</label>
      <label><input type="radio" name="export-mode" value="translated"> 仅译文</label>
      <label><input type="radio" name="export-mode" value="bilingual"> 双语对照（一行原文一行译文）</label>
      <div class="export-dialog-actions">
        <button id="export-confirm" class="btn primary">确认导出</button>
        <button id="export-cancel" class="btn">取消</button>
      </div>
    </div>
  `;
  document.body.appendChild(dialog);

  document.getElementById('export-confirm').onclick = () => {
    const mode = document.querySelector('input[name="export-mode"]:checked').value;
    dialog.remove();
    doExport(mode);
  };
  document.getElementById('export-cancel').onclick = () => dialog.remove();
}

async function doExport(mode) {
  if (!state.sessionId) return;
  exportBtn.disabled = true;
  exportBtn.textContent = '⏳ 导出中...';
  statusText.textContent = '生成 Word 文档...';

  try {
    const r = await fetch('/api/export', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: state.sessionId, export_mode: mode }),
    });
    if (!r.ok) throw new Error('导出失败');
    const blob = await r.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `ocr_result_${mode}.docx`;
    a.click();
    URL.revokeObjectURL(url);
    showToast('导出成功!');
  } catch (err) {
    showToast('导出失败: ' + err.message);
  }

  exportBtn.disabled = false;
  exportBtn.textContent = '📥 导出 Word';
  statusText.textContent = '就绪';
}

/* ── Divider drag ───────────────────────────────── */
function setupDivider() {
  let isDragging = false;
  const container = $('split-container');
  const left = $('left-panel');
  const right = $('right-panel');

  divider.addEventListener('mousedown', e => {
    isDragging = true;
    divider.classList.add('active');
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
    e.preventDefault();
  });

  document.addEventListener('mousemove', e => {
    if (!isDragging) return;
    const rect = container.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const pct = (x / rect.width) * 100;
    left.style.flex = `0 0 ${Math.max(20, Math.min(80, pct))}%`;
    right.style.flex = '1';
  });

  document.addEventListener('mouseup', () => {
    if (!isDragging) return;
    isDragging = false;
    divider.classList.remove('active');
    document.body.style.cursor = '';
    document.body.style.userSelect = '';
  });
}

/* ── Keyboard shortcuts ─────────────────────────── */
function setupKeyboard() {
  document.addEventListener('keydown', e => {
    if (e.target.isContentEditable) return;
    if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') { e.preventDefault(); goToPage(state.currentPage - 1); }
    if (e.key === 'ArrowRight' || e.key === 'ArrowDown') { e.preventDefault(); goToPage(state.currentPage + 1); }
  });
}

/* ── Toast ──────────────────────────────────────── */
let toastTimer;
function showToast(msg) {
  toast.textContent = msg;
  toast.classList.remove('hidden');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.add('hidden'), 2500);
}
