/* M&K Nexus Cloud - static/script.js
 * Shared client script for ALL templates (index, signup, verify_otp, reset_password, 500...).
 * Safe to load next to the inline scripts already inside the templates:
 * if a page already started a feature, this file skips it (no double events).
 * Load it AFTER the page scripts (base.html does this).
 * Talks to: Socket.IO (new_log, terminal_command/response, subscribe_live_logs/new_live_log),
 * POST /add_log (form), POST /api/v3/reports/export-csv, POST /api/v3/hub/ingest, POST /api/v2/ingest-logs.
 */
(function () {
  const g = id => document.getElementById(id);
  const esc = s => String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const COL = {INFO:'text-cyan-300', WARNING:'text-amber-300', ERROR:'text-red-400', CRITICAL:'text-red-300 font-bold', SECURITY:'text-fuchsia-300'};
  const csrf = () => (document.querySelector('meta[name=csrf-token]') || {}).content || '';

  /* ----- all pages: flash toasts fade after 6s ----- */
  document.querySelectorAll('.fixed.top-4 > div').forEach(t => setTimeout(() => t.remove(), 6000));

  /* ----- signup / reset_password: strength bar + match check ----- */
  if (typeof p1 === 'undefined' && g('p1') && g('p2') && g('f')) {
    const a1 = g('p1'), a2 = g('p2'), bar = g('bar');
    if (bar) a1.addEventListener('input', () => {
      let s = 0, v = a1.value;
      if (v.length >= 8) s++; if (/[A-Z]/.test(v)) s++; if (/\d/.test(v)) s++; if (/\W/.test(v)) s++;
      bar.style.width = s * 25 + '%';
      bar.className = 'h-1 rounded transition-all ' + ['bg-red-500','bg-red-500','bg-amber-400','bg-cyan-400','bg-emerald-400'][s];
    });
    g('f').addEventListener('submit', e => { if (a1.value !== a2.value) { e.preventDefault(); g('err').classList.remove('hidden'); } });
  }

  /* ----- verify_otp: 6 boxes ----- */
  if (typeof bx === 'undefined' && g('boxes')) {
    const boxes = [...g('boxes').querySelectorAll('input')];
    boxes.forEach((b, i) => {
      b.addEventListener('input', () => { b.value = b.value.replace(/\D/g, ''); if (b.value && boxes[i + 1]) boxes[i + 1].focus(); });
      b.addEventListener('keydown', e => { if (e.key === 'Backspace' && !b.value && boxes[i - 1]) boxes[i - 1].focus(); });
      b.addEventListener('paste', e => {
        const t = (e.clipboardData.getData('text') || '').replace(/\D/g, '').slice(0, 6);
        if (!t) return; e.preventDefault(); t.split('').forEach((c, j) => boxes[j].value = c);
      });
    });
    g('f').addEventListener('submit', () => { g('otp').value = boxes.map(b => b.value).join(''); });
  }

  /* ----- 500: trace reference ----- */
  if (g('trc') && !g('trc').textContent) g('trc').textContent = '#MK-TRC-' + Date.now().toString().slice(-8);

  /* ----- index: dashboard (skipped when the template's inline script already ran) ----- */
  if (!g('logs') || typeof window.hubUpload === 'function') return;

  const badge = s => { s = parseFloat(s); const c = s >= .8 ? 'bg-red-500/20 text-red-300' : s >= .4 ? 'bg-amber-500/20 text-amber-300' : 'bg-emerald-500/20 text-emerald-300'; return `<span class="px-2 py-0.5 rounded-full text-xs ${c}">${s}</span>`; };
  const stats = () => { const r = [...document.querySelectorAll('.log-row')];
    g('sTotal').textContent = r.length;
    g('sErr').textContent = r.filter(x => ['ERROR','CRITICAL'].includes(x.dataset.level)).length;
    g('sWarn').textContent = r.filter(x => x.dataset.level === 'WARNING').length; };
  const paint = () => { document.querySelectorAll('.log-row').forEach(r => {
    r.querySelector('.lvl').className = 'lvl ' + (COL[r.dataset.level] || '');
    const t = r.querySelector('.thr'); if (t) t.outerHTML = badge(r.dataset.score); }); stats(); };
  paint();

  window.openModal = () => g('modal').classList.remove('hidden');
  window.closeModal = () => g('modal').classList.add('hidden');
  g('flt').onchange = e => document.querySelectorAll('.log-row').forEach(r =>
    r.style.display = (!e.target.value || r.dataset.level === e.target.value) ? '' : 'none');

  const sock = io();
  const ws = (t, c) => { g('ws').textContent = t; g('ws').className = 'text-xs px-2 py-0.5 rounded-full ' + c; };
  sock.on('connect', () => ws('live', 'bg-emerald-500/10 text-emerald-300'));
  sock.on('disconnect', () => ws('offline', 'bg-red-500/10 text-red-300'));

  sock.on('new_log', d => {                       // backend rule: ERROR = 0.98 else 0.01
    const e = g('empty'); if (e) e.remove();
    const tr = document.createElement('tr');
    tr.className = 'border-t border-white/5 log-row bg-cyan-400/10';
    Object.assign(tr.dataset, {level: d.level, ts: d.timestamp, tag: d.tag, score: d.level === 'ERROR' ? 0.98 : 0.01});
    tr.innerHTML = `<td class="py-2 pr-3 whitespace-nowrap text-slate-400">${esc(d.timestamp)}</td><td><span class="lvl">${esc(d.level)}</span></td><td>${esc(d.tag)}</td><td class="msg max-w-md break-words">${esc(d.message)}</td><td class="font-mono text-xs text-cyan-300">${esc(d.trace_id)}</td><td><span class="thr"></span></td>`;
    g('logs').prepend(tr); paint(); setTimeout(() => tr.classList.remove('bg-cyan-400/10'), 2000);
  });

  g('tf').onsubmit = e => { e.preventDefault(); const c = g('tc').value.trim(); if (!c) return; sock.emit('terminal_command', {command: c}); g('tc').value = ''; };
  sock.on('terminal_response', d => { const t = g('term'); if (d.output.includes('CLEAR')) { t.textContent = ''; return; } t.textContent += d.output; t.scrollTop = t.scrollHeight; });

  window.subscribe = () => { g('tele').innerHTML = ''; sock.emit('subscribe_live_logs', {company: g('clu').value || 'Default-Cluster'}); };
  sock.on('live_response', d => g('tele').insertAdjacentHTML('afterbegin', `<li class="text-emerald-300">${esc(d.status)}</li>`));
  sock.on('new_live_log', d => g('tele').insertAdjacentHTML('afterbegin', `<li><span class="text-slate-500">${esc(d.timestamp)}</span> [${esc(d.cluster)}] ${esc(d.log)}</li>`));

  window.exportCsv = async () => {
    const logs = [...document.querySelectorAll('.log-row')].map(r => ({timestamp: r.dataset.ts, severity: r.dataset.level, tag: r.dataset.tag, message: r.querySelector('.msg').textContent, threat_score: r.dataset.score}));
    if (!logs.length) return alert('No logs to export.');
    const r = await fetch('/api/v3/reports/export-csv', {method: 'POST', headers: {'Content-Type': 'application/json', 'X-CSRFToken': csrf()}, body: JSON.stringify({logs})});
    if (!r.ok) return alert('Export failed (' + r.status + ')');
    const a = document.createElement('a'); a.href = URL.createObjectURL(await r.blob()); a.download = 'enterprise_compliance_report.csv'; a.click();
  };

  window.hubUpload = async () => {
    const ep = g('hep').value, pull = ep.endsWith('/pull'), f = g('hf').files[0], k = g('hk').value.trim();
    if (!k || (!pull && !f)) return alert(pull ? 'API key is required.' : 'API key and a .log/.txt file are required.');
    const fd = new FormData(); if (!pull) fd.append('file', f);
    try {
      const r = await fetch(ep, {method: 'POST', headers: {'X-API-Key': k}, body: pull ? undefined : fd}), d = await r.json();
      if (!r.ok) return alert(d.error || 'Upload failed');
      const sum = d.category_summary || d.summary, data = d.categorized_data || d.detailed_logs;
      g('hubOut').classList.remove('hidden');
      g('hCl').textContent = d.cluster_hub || d.company; g('hTi').textContent = d.cluster_threat_index;
      g('hTot').textContent = d.total_logs_analyzed || d.total_logs_processed;
      g('hSum').innerHTML = Object.entries(sum).map(([n, v]) => `<div class="glass p-2"><div class="text-slate-400">${n}</div><div class="text-lg text-white">${v}</div></div>`).join('');
      g('hRows').innerHTML = Object.entries(data).flatMap(([c, a]) => a.map(x => `<tr class="border-t border-white/5"><td class="py-1 ${COL[c] || ''}">${c}</td><td class="break-all">${esc(x.message)}</td><td>${badge(x.threat_score)}</td><td class="text-slate-400">${x.timestamp}</td></tr>`)).join('');
    } catch (e) { alert('Network error: ' + e.message); }
  };
})();