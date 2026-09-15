/* ShortLink Demo 前端逻辑 */

const api = {
  async create(longUrl) {
    const res = await fetch('/api/links', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ long_url: longUrl }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || '创建失败');
    return data;
  },

  async list() {
    const res = await fetch('/api/links');
    if (!res.ok) throw new Error('获取列表失败');
    return res.json();
  },

  async disable(code) {
    const res = await fetch(`/api/links/${code}`, { method: 'DELETE' });
    if (!res.ok) throw new Error('操作失败');
  },
};

/* ---------- 首页：生成短链 ---------- */
function initCreatePage() {
  const form = document.getElementById('createForm');
  if (!form) return;

  const errorMsg = document.getElementById('errorMsg');
  const resultCard = document.getElementById('resultCard');
  const shortUrl = document.getElementById('shortUrl');
  const longUrlPreview = document.getElementById('longUrlPreview');

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    errorMsg.classList.add('d-none');
    resultCard.classList.add('d-none');

    const longUrl = document.getElementById('longUrl').value.trim();
    if (!longUrl) {
      errorMsg.textContent = '请输入长链接';
      errorMsg.classList.remove('d-none');
      return;
    }

    const btn = document.getElementById('generateBtn');
    btn.disabled = true;
    btn.textContent = '生成中...';
    try {
      const data = await api.create(longUrl);
      shortUrl.href = data.short_url;
      shortUrl.textContent = data.short_url;
      longUrlPreview.textContent = data.long_url;
      resultCard.classList.remove('d-none');
    } catch (err) {
      errorMsg.textContent = err.message;
      errorMsg.classList.remove('d-none');
    } finally {
      btn.disabled = false;
      btn.textContent = '生成短链';
    }
  });

  document.getElementById('copyBtn').addEventListener('click', async () => {
    try {
      await navigator.clipboard.writeText(shortUrl.textContent);
      alert('已复制');
    } catch {
      alert('复制失败，请手动复制');
    }
  });
}

/* ---------- Dashboard：列表 + 图表 ---------- */
let clickChart = null;

function initDashboardPage() {
  if (!document.getElementById('linkTable')) return;

  document.getElementById('refreshBtn').addEventListener('click', loadDashboard);
  loadDashboard();
}

async function loadDashboard() {
  const links = await api.list();
  renderTable(links);
  renderChart(links);
  renderStats(links);
}

function renderStats(links) {
  document.getElementById('statTotal').textContent = links.length;
  document.getElementById('statClicks').textContent = links.reduce((s, l) => s + l.click_count, 0);
  document.getElementById('statActive').textContent = links.filter((l) => l.status === 1).length;
}

function renderTable(links) {
  const tbody = document.getElementById('linkTable');
  const emptyTip = document.getElementById('emptyTip');
  tbody.innerHTML = '';

  if (!links.length) {
    emptyTip.classList.remove('d-none');
    return;
  }
  emptyTip.classList.add('d-none');

  for (const link of links) {
    const shortUrl = `${location.origin}/s/${link.code}`;
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td><code>${link.code}</code></td>
      <td><a class="app-link text-decoration-none" href="/s/${link.code}" target="_blank">${shortUrl}</a></td>
      <td class="text-truncate text-muted" style="max-width: 240px" title="${escapeHtml(link.long_url)}">${escapeHtml(link.long_url)}</td>
      <td class="text-end fw-semibold">${link.click_count}</td>
      <td class="text-end">${link.status === 1
        ? '<span class="badge text-bg-success">启用</span>'
        : '<span class="badge text-bg-secondary">已禁用</span>'}</td>
      <td class="text-end text-muted small">${formatTime(link.created_at)}</td>
      <td class="text-end">${link.status === 1
        ? `<button class="btn btn-sm btn-outline-danger" data-code="${link.code}">禁用</button>`
        : ''}</td>
    `;
    tbody.appendChild(tr);
  }

  tbody.querySelectorAll('button[data-code]').forEach((btn) => {
    btn.addEventListener('click', async () => {
      if (!confirm('确定禁用该短链？禁用后跳转会返回 404。')) return;
      await api.disable(btn.dataset.code);
      loadDashboard();
    });
  });
}

function renderChart(links) {
  const ctx = document.getElementById('clickChart');
  const top = [...links]
    .filter((l) => l.status === 1)
    .sort((a, b) => b.click_count - a.click_count)
    .slice(0, 10);

  const labels = top.map((l) => l.code);
  const data = top.map((l) => l.click_count);

  if (clickChart) clickChart.destroy();
  clickChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        label: '点击量',
        data,
        backgroundColor: '#4f46e5',
        borderRadius: 6,
        maxBarThickness: 42,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        y: { beginAtZero: true, ticks: { precision: 0 } },
        x: { grid: { display: false } },
      },
    },
  });
}

function formatTime(value) {
  if (!value) return '-';
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  const pad = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function escapeHtml(str) {
  return String(str ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;');
}

/* 页面分发 */
initCreatePage();
initDashboardPage();
