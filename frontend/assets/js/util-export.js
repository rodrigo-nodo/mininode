export async function copyToClipboard(text) {
  try { await navigator.clipboard.writeText(text); }
  catch { /* fallback invisible */ const ta=document.createElement('textarea'); ta.value=text; document.body.appendChild(ta); ta.select(); document.execCommand('copy'); ta.remove(); }
}

export function downloadText(text, filename='archivo.txt') {
  const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  triggerDownload(url, filename);
}

export function downloadMarkdown(text, filename='documento.md') {
  const blob = new Blob([text], { type: 'text/markdown;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  triggerDownload(url, filename);
}

// Hooks para futuro (lado backend ideal)
export async function exportDocxServer(endpoint, payload, filename='documento.docx', headers={}) {
  const res = await fetch(endpoint, { method:'POST', headers, body: JSON.stringify(payload) });
  if (!res.ok) throw new Error(`Export DOCX falló: ${res.status}`);
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  triggerDownload(url, filename);
}

export async function exportPDFServer(endpoint, payload, filename='documento.pdf', headers={}) {
  const res = await fetch(endpoint, { method:'POST', headers, body: JSON.stringify(payload) });
  if (!res.ok) throw new Error(`Export PDF falló: ${res.status}`);
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  triggerDownload(url, filename);
}

function triggerDownload(url, filename) {
  const a = document.createElement('a');
  a.href = url; a.download = filename; document.body.appendChild(a); a.click();
  a.remove(); URL.revokeObjectURL(url);
}
