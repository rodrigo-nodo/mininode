// Decisión: util pequeño, sin dependencias, reusable en cualquier agente.
export function extractUrls(text, max = 3) {
  if (!text) return [];
  const re = /\bhttps?:\/\/[^\s)]+/gi;
  const found = text.match(re) || [];
  // normaliza: trim y quita puntuación de cierre común
  const norm = found.map(u => u.trim().replace(/[),.;]+$/,''));
  const uniq = Array.from(new Set(norm));
  return uniq.slice(0, max);
}

export function hasUrls(text) {
  return extractUrls(text, 1).length > 0;
}
