// ── Toast ─────────────────────────────────────────────────────
function showToast(msg, type = '') {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.className = `toast show ${type}`;
  clearTimeout(t._timer);
  t._timer = setTimeout(() => { t.className = 'toast'; }, 3200);
}

// ── Tabs ──────────────────────────────────────────────────────
document.querySelectorAll('.tab').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.tab').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(s => s.classList.remove('active'));
    btn.classList.add('active');
    const tab = btn.dataset.tab;
    document.getElementById(`tab-${tab}`).classList.add('active');
    if (tab === 'carousels') loadCarousels();
    if (tab === 'generate') updateGenerateInfo();
  });
});

// ── Type selector ─────────────────────────────────────────────
let selectedType = 'sans_flocage';

function selectType(type) {
  selectedType = type;
  document.querySelectorAll('.type-btn').forEach(b => b.classList.remove('active'));
  document.querySelector(`.type-btn[data-type="${type}"]`).classList.add('active');
  updateGenerateInfo();
}

// ── Stats ─────────────────────────────────────────────────────
async function loadStats() {
  try {
    const r = await fetch('/api/stats');
    const d = await r.json();
    document.getElementById('statCat1').textContent = d.category1;
    document.getElementById('statCat2').textContent = d.category2;
    document.getElementById('statCat3').textContent = d.category3;
    document.getElementById('statCat4').textContent = d.category4;
    document.getElementById('statToday').textContent = d.today_generated;
    document.getElementById('statTotal').textContent = d.total_generated;
    document.getElementById('badgeCat1').textContent = d.category1;
    document.getElementById('badgeCat2').textContent = d.category2;
    document.getElementById('badgeCat3').textContent = d.category3;
    document.getElementById('badgeCat4').textContent = d.category4;
    return d;
  } catch(e) { return null; }
}

async function updateGenerateInfo() {
  const d = await loadStats();
  if (!d) return;
  document.getElementById('infoC4').textContent = d.category4 + ' image(s)';

  if (selectedType === 'flocage') {
    document.getElementById('infoCoverRow').style.display = 'none';
    document.getElementById('infoStockLabel').textContent = '🎽 Images flocage';
    document.getElementById('infoC2').textContent = d.category3 + ' image(s)';
    document.getElementById('readyAlert').style.display = d.ready_flocage ? 'none' : 'block';
  } else {
    document.getElementById('infoCoverRow').style.display = '';
    document.getElementById('infoC1').textContent = d.category1 + ' image(s)';
    document.getElementById('infoStockLabel').textContent = '📸 Images stock';
    document.getElementById('infoC2').textContent = d.category2 + ' image(s)';
    document.getElementById('readyAlert').style.display = d.ready_sans_flocage ? 'none' : 'block';
  }
}

// ── Upload ────────────────────────────────────────────────────
async function uploadFiles(files, category) {
  if (!files || files.length === 0) return;

  const num = category === 'category1' ? '1' : category === 'category2' ? '2' : category === 'category3' ? '3' : '4';
  const progressBar = document.getElementById(`progress${num}`);
  const progressFill = document.getElementById(`progressFill${num}`);

  progressBar.style.display = 'block';
  progressFill.style.width = '10%';

  const formData = new FormData();
  formData.append('category', category);
  Array.from(files).forEach(f => formData.append('files', f));

  try {
    progressFill.style.width = '50%';
    const r = await fetch('/api/upload', { method: 'POST', body: formData });
    const d = await r.json();
    progressFill.style.width = '100%';
    setTimeout(() => { progressBar.style.display = 'none'; progressFill.style.width = '0%'; }, 600);

    if (d.count > 0) {
      showToast(`✅ ${d.count} image(s) ajoutée(s)`, 'success');
      loadImages(category);
      loadStats();
    } else {
      showToast('Aucun fichier valide (JPG, PNG, WEBP)', 'error');
    }
  } catch(e) {
    showToast('Erreur lors de l\'upload', 'error');
    progressBar.style.display = 'none';
  }
}

function setupDrop(dropId, category) {
  const zone = document.getElementById(dropId);
  if (!zone) return;
  zone.addEventListener('dragover', e => { e.preventDefault(); zone.classList.add('drag-over'); });
  zone.addEventListener('dragleave', () => zone.classList.remove('drag-over'));
  zone.addEventListener('drop', e => {
    e.preventDefault();
    zone.classList.remove('drag-over');
    uploadFiles(e.dataTransfer.files, category);
  });
}

// ── Load Images ───────────────────────────────────────────────
async function loadImages(category) {
  try {
    const r = await fetch(`/api/images/${category}`);
    const d = await r.json();
    const num = category === 'category1' ? '1' : category === 'category2' ? '2' : category === 'category3' ? '3' : '4';
    const grid = document.getElementById(`grid${num}`);
    grid.innerHTML = '';

    if (d.images.length === 0) {
      grid.innerHTML = '<p style="color:var(--text-muted);font-size:0.8rem;padding:8px 0;">Aucune image.</p>';
      return;
    }

    d.images.forEach(img => {
      const div = document.createElement('div');
      div.className = 'img-thumb';
      div.innerHTML = `
        <img src="${img.url}" loading="lazy" onclick="openModal('${img.url}')" />
        <button class="del-btn" onclick="deleteImage(event, '${category}', '${img.name}')">✕</button>
      `;
      grid.appendChild(div);
    });
  } catch(e) {}
}

async function deleteImage(e, category, filename) {
  e.stopPropagation();
  if (!confirm('Supprimer cette image ?')) return;
  try {
    const r = await fetch('/api/delete-image', {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ category, filename })
    });
    const d = await r.json();
    if (d.success) {
      showToast('Image supprimée', 'success');
      loadImages(category);
      loadStats();
    }
  } catch(e) { showToast('Erreur suppression', 'error'); }
}

// ── Generate ──────────────────────────────────────────────────
async function generateOne() {
  const btn = event.target.closest('button');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span> Génération...';
  try {
    const r = await fetch('/api/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ video_type: selectedType })
    });
    const d = await r.json();
    btn.disabled = false;
    btn.innerHTML = '<span>🎲</span> Générer 1 carrousel';
    if (d.success) {
      showToast('✅ Carrousel généré !', 'success');
      showGenerateResult([d.carousel]);
      loadStats();
    } else {
      showToast(d.error, 'error');
    }
  } catch(e) {
    btn.disabled = false;
    btn.innerHTML = '<span>🎲</span> Générer 1 carrousel';
    showToast('Erreur', 'error');
  }
}

async function generateFive() {
  const btn = event.target.closest('button');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span> Génération...';
  try {
    const r = await fetch('/api/generate-five', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ video_type: selectedType })
    });
    const d = await r.json();
    btn.disabled = false;
    btn.innerHTML = '<span>⚡</span> Générer 5 carrousels';
    if (d.success) {
      showToast(`✅ ${d.count} carrousel(s) générés !`, 'success');
      showGenerateResult(d.carousels);
      loadStats();
    } else {
      showToast(d.error, 'error');
    }
  } catch(e) {
    btn.disabled = false;
    btn.innerHTML = '<span>⚡</span> Générer 5 carrousels';
    showToast('Erreur', 'error');
  }
}

function showGenerateResult(carousels) {
  document.getElementById('generateResult').style.display = 'block';
  document.getElementById('generateResult').textContent = `✅ ${carousels.length} carrousel(s) prêt(s) ! Va dans "Carrousels" pour télécharger.`;

  const latest = document.getElementById('latestCarousels');
  const grid = document.getElementById('latestGrid');
  latest.style.display = 'block';
  grid.innerHTML = '';

  carousels.forEach(c => {
    const div = document.createElement('div');
    div.className = 'carousel-thumb';
    div.onclick = switchToCarousels;
    div.innerHTML = `
      ${c.preview_url
        ? `<img src="${c.preview_url}" style="width:100%;aspect-ratio:1;object-fit:cover;" />`
        : `<div style="aspect-ratio:1;display:flex;align-items:center;justify-content:center;font-size:2rem;background:var(--surface2)">📸</div>`
      }
      <div class="ct-info">${formatDate(c.timestamp)}<br>${c.total_images} images</div>
    `;
    grid.appendChild(div);
  });
}

function switchToCarousels() {
  document.querySelectorAll('.tab').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.tab-content').forEach(s => s.classList.remove('active'));
  document.querySelector('[data-tab="carousels"]').classList.add('active');
  document.getElementById('tab-carousels').classList.add('active');
  loadCarousels();
}

// ── Carousels List ────────────────────────────────────────────
async function loadCarousels() {
  document.getElementById('noCarousels').style.display = 'none';
  document.getElementById('carouselsList').innerHTML = '<p style="color:var(--text-muted);padding:20px 0;">Chargement...</p>';

  try {
    const r = await fetch('/api/carousels');
    const d = await r.json();
    const list = document.getElementById('carouselsList');
    list.innerHTML = '';

    if (!d.carousels || d.carousels.length === 0) {
      document.getElementById('noCarousels').style.display = 'block';
      return;
    }

    d.carousels.forEach(c => {
      const item = document.createElement('div');
      item.className = 'carousel-item';
      const fullText = `${c.description}\n\n${c.hashtags}`;

      const stripHtml = (c.image_urls || []).map((url, i) =>
        `<img class="strip-img" src="${url}" loading="lazy" onclick="openModal('${url}')" onerror="this.style.display='none'" ${i === 0 ? 'style="border-color:var(--accent)"' : ''} />`
      ).join('');

      item.innerHTML = `
        <div class="carousel-item-header">
          <div>
            <div class="carousel-item-title">📸 Carrousel — ${c.total_images} images</div>
            <div class="carousel-item-date">${formatDate(c.timestamp)}</div>
          </div>
          <div class="carousel-item-actions">
            <a href="/api/download/${encodeURIComponent(c.name)}" class="btn btn-primary btn-sm">⬇️ Télécharger</a>
            <button class="btn btn-danger btn-sm" onclick="deleteCarousel('${c.name}', this)">🗑️</button>
          </div>
        </div>
        <div class="carousel-item-body">
          <div class="desc-box">
            <button class="copy-btn" onclick="copyText(this, ${JSON.stringify(fullText)})">Copier</button>
            <div class="desc-text">${c.description}</div>
            <div class="hashtags">${c.hashtags}</div>
          </div>
          <div class="image-strip">${stripHtml}</div>
        </div>
      `;
      list.appendChild(item);
    });
  } catch(e) {
    document.getElementById('carouselsList').innerHTML = `<p style="color:var(--red);padding:20px 0;">Erreur : ${e.message}</p>`;
  }
}

async function deleteCarousel(name, btn) {
  if (!confirm('Supprimer ce carrousel ?')) return;
  btn.disabled = true;
  try {
    const r = await fetch('/api/delete-carousel', {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name })
    });
    const d = await r.json();
    if (d.success) {
      showToast('Carrousel supprimé', 'success');
      loadCarousels();
      loadStats();
    }
  } catch(e) { showToast('Erreur', 'error'); }
}

// ── Helpers ───────────────────────────────────────────────────
function copyText(btn, text) {
  navigator.clipboard.writeText(text).then(() => {
    btn.textContent = '✓ Copié !';
    btn.classList.add('copied');
    setTimeout(() => { btn.textContent = 'Copier'; btn.classList.remove('copied'); }, 2000);
  });
}

function openModal(src) {
  document.getElementById('modalImg').src = src;
  document.getElementById('modal').classList.add('open');
}

function closeModal() {
  document.getElementById('modal').classList.remove('open');
}

document.addEventListener('keydown', e => { if (e.key === 'Escape') closeModal(); });

function formatDate(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  return d.toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' });
}

// ── Init ──────────────────────────────────────────────────────
(async function init() {
  setupDrop('drop1', 'category1');
  setupDrop('drop2', 'category2');
  setupDrop('drop3', 'category3');
  setupDrop('drop4', 'category4');
  await loadStats();
  await loadImages('category1');
  await loadImages('category2');
  await loadImages('category3');
  await loadImages('category4');
})();
