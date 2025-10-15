// Decisión: medir tiempos con performance.now() y un wrapper genérico.
export const now = () => (typeof performance !== 'undefined' && performance.now) ? performance.now() : Date.now();

export async function measureAsync(label, fn) {
  const t0 = now();
  const result = await fn();
  const ms = Math.round(now() - t0);
  return { label, ms, result };
}

export class Stopwatch {
  constructor() { this.reset(); }
  reset() { this.t0 = now(); this.marks = []; }
  mark(label) { const ms = Math.round(now() - this.t0); this.marks.push({ label, ms }); return ms; }
  elapsed() { return Math.round(now() - this.t0); }
}
