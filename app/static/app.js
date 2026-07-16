const dropZone = document.getElementById('dropZone');
const fileInput = document.getElementById('fileInput');
const fileInfo = document.getElementById('fileInfo');
const fileName = document.getElementById('fileName');
const fileMeta = document.getElementById('fileMeta');
const removeFile = document.getElementById('removeFile');
const sourceLang = document.getElementById('sourceLang');
const targetLang = document.getElementById('targetLang');
const batchSize = document.getElementById('batchSize');
const numBeams = document.getElementById('numBeams');
const engineBatch = document.getElementById('engineBatch');
const deviceSelect = document.getElementById('device');
const translateBtn = document.getElementById('translateBtn');
const progressPanel = document.getElementById('progressPanel');
const progressBar = document.getElementById('progressBar');
const progressText = document.getElementById('progressText');
const statusText = document.getElementById('statusText');
const batchInfo = document.getElementById('batchInfo');
const elapsedTime = document.getElementById('elapsedTime');
const speedInfo = document.getElementById('speedInfo');
const downloadBtn = document.getElementById('downloadBtn');
const glossaryList = document.getElementById('glossaryList');
const glossarySource = document.getElementById('glossarySource');
const glossaryTarget = document.getElementById('glossaryTarget');
const addGlossaryBtn = document.getElementById('addGlossaryBtn');
const deviceBadge = document.getElementById('deviceBadge');
const settingsSummary = document.getElementById('settingsSummary');

let selectedFile = null;
let currentJobId = null;
let glossaryEntries = [];
let deviceInfo = { cuda_available: false, gpu_name: null };

const DEVICE_PRESETS = {
    cpu:  { num_beams: 2, engine_batch: 8,  context_batch: 15, label: 'Num Beams: 2 | Engine Batch: 8 | Context: 15' },
    gpu:  { num_beams: 2, engine_batch: 8,  context_batch: 15, label: 'Num Beams: 2 | Engine Batch: 8 | Context: 15' },
    auto: null,
};

async function loadLanguages() {
    try {
        const resp = await fetch('/api/languages');
        const langs = await resp.json();
        langs.forEach(l => {
            sourceLang.add(new Option(`${l.name} (${l.code})`, l.code));
            targetLang.add(new Option(`${l.name} (${l.code})`, l.code));
        });
        sourceLang.value = 'en';
        targetLang.value = 'id';
    } catch (e) {
        console.error('Failed to load languages:', e);
    }
}

async function loadDeviceInfo() {
    try {
        const resp = await fetch('/api/device-info');
        deviceInfo = await resp.json();
        updateDeviceBadge();
        applyDevicePreset();
    } catch (e) {
        console.error('Failed to load device info:', e);
        deviceBadge.textContent = 'CPU Only';
        deviceBadge.className = 'device-badge cpu';
    }
}

function updateDeviceBadge() {
    if (deviceInfo.cuda_available) {
        deviceBadge.textContent = 'GPU: ' + deviceInfo.gpu_name;
        deviceBadge.className = 'device-badge gpu';
    } else {
        deviceBadge.textContent = 'CPU Mode (' + (deviceInfo.pytorch_version || '?') + ')';
        deviceBadge.className = 'device-badge cpu';
    }
}

function applyDevicePreset() {
    const selected = deviceSelect.value;
    let preset;

    if (selected === 'auto') {
        preset = deviceInfo.cuda_available ? DEVICE_PRESETS.gpu : DEVICE_PRESETS.cpu;
    } else {
        preset = DEVICE_PRESETS[selected];
    }

    if (!preset) return;

    numBeams.value = preset.num_beams;
    engineBatch.value = preset.engine_batch;
    batchSize.value = preset.context_batch;
    settingsSummary.textContent = preset.label;
}

deviceSelect.addEventListener('change', applyDevicePreset);

dropZone.addEventListener('click', () => fileInput.click());

dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('drag-over');
});

dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('drag-over');
});

dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('drag-over');
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
});

fileInput.addEventListener('change', (e) => {
    if (e.target.files[0]) handleFile(e.target.files[0]);
});

function handleFile(file) {
    const ext = file.name.split('.').pop().toLowerCase();
    if (!['srt', 'ass', 'ssa', 'vtt'].includes(ext)) {
        alert('Unsupported format. Use SRT, ASS, SSA, or VTT.');
        return;
    }
    selectedFile = file;
    fileName.textContent = file.name;
    fileMeta.textContent = `${ext.toUpperCase()} • ${(file.size / 1024).toFixed(1)} KB`;
    fileInfo.style.display = 'flex';
    dropZone.style.display = 'none';
    translateBtn.disabled = false;
}

removeFile.addEventListener('click', () => {
    selectedFile = null;
    fileInfo.style.display = 'none';
    dropZone.style.display = 'block';
    fileInput.value = '';
    translateBtn.disabled = true;
});

addGlossaryBtn.addEventListener('click', () => {
    const src = glossarySource.value.trim();
    const tgt = glossaryTarget.value.trim();
    if (!src || !tgt) return;

    glossaryEntries.push({ source: src, target: tgt, case_sensitive: true });
    renderGlossary();
    glossarySource.value = '';
    glossaryTarget.value = '';
});

function renderGlossary() {
    glossaryList.innerHTML = '';
    glossaryEntries.forEach((entry, i) => {
        const div = document.createElement('div');
        div.className = 'glossary-item';
        div.innerHTML = `
            <span class="source">${esc(entry.source)}</span>
            <span class="arrow">→</span>
            <span class="target">${esc(entry.target)}</span>
            <button class="remove-btn" data-idx="${i}">✕</button>
        `;
        glossaryList.appendChild(div);
    });

    glossaryList.querySelectorAll('.remove-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            glossaryEntries.splice(parseInt(btn.dataset.idx), 1);
            renderGlossary();
        });
    });
}

function esc(s) {
    const d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
}

translateBtn.addEventListener('click', startTranslation);

async function startTranslation() {
    if (!selectedFile) return;

    translateBtn.disabled = true;
    translateBtn.textContent = 'Starting...';
    progressPanel.style.display = 'block';
    downloadBtn.style.display = 'none';
    progressBar.style.width = '0%';
    progressText.textContent = '0%';
    statusText.textContent = 'Uploading...';
    batchInfo.textContent = '0 / 0';
    elapsedTime.textContent = '0.0s';
    speedInfo.textContent = '- lines/s';

    const formData = new FormData();
    formData.append('file', selectedFile);
    formData.append('source_lang', sourceLang.value);
    formData.append('target_lang', targetLang.value);
    formData.append('batch_size', batchSize.value);
    formData.append('num_beams', numBeams.value);
    formData.append('engine_batch_size', engineBatch.value);
    formData.append('device', deviceSelect.value);
    formData.append('glossary', JSON.stringify(glossaryEntries));

    try {
        const resp = await fetch('/api/translate', {
            method: 'POST',
            body: formData,
        });

        if (!resp.ok) {
            const err = await resp.json();
            alert(err.detail || 'Translation failed');
            translateBtn.disabled = false;
            translateBtn.textContent = 'Translate';
            return;
        }

        const data = await resp.json();
        currentJobId = data.job_id;
        pollProgress();
    } catch (e) {
        alert('Error: ' + e.message);
        translateBtn.disabled = false;
        translateBtn.textContent = 'Translate';
    }
}

function pollProgress() {
    if (!currentJobId) return;

    const interval = setInterval(async () => {
        try {
            const resp = await fetch(`/api/progress/${currentJobId}`);
            const data = await resp.json();

            const pct = Math.round(data.percent);
            progressBar.style.width = pct + '%';
            progressText.textContent = pct + '%';
            statusText.textContent = data.status;
            batchInfo.textContent = `${data.completed_batches} / ${data.total_batches}`;
            elapsedTime.textContent = `${data.elapsed_seconds}s`;
            speedInfo.textContent = data.lines_per_second > 0 ? `${data.lines_per_second} lines/s` : '- lines/s';

            if (data.status === 'completed') {
                clearInterval(interval);
                downloadBtn.style.display = 'block';
                translateBtn.disabled = false;
                translateBtn.textContent = 'Translate';
            } else if (data.status === 'failed') {
                clearInterval(interval);
                statusText.textContent = 'Failed: ' + (data.error || 'Unknown error');
                translateBtn.disabled = false;
                translateBtn.textContent = 'Translate';
            }
        } catch (e) {
            console.error('Poll error:', e);
        }
    }, 800);
}

downloadBtn.addEventListener('click', () => {
    if (currentJobId) {
        window.location.href = `/api/download/${currentJobId}`;
    }
});

loadLanguages();
loadDeviceInfo();
