export function scoreCandidate({
  base,
  count,
  fingerprint,
}: {
  base: number;
  count: number;
  fingerprint: Record<string, unknown>;
  signals: Record<string, unknown>;
}): number {
  let score = base;
  if (count === 1) score += 5;
  else if (count > 3) score -= Math.min(30, count * 3);
  if (fingerprint.role) score += 2;
  if (fingerprint.accessibleName) score += 2;
  return Math.max(0, Math.min(100, score));
}
