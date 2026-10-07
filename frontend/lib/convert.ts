/** The backend sends money and rates as decimal strings ("5000.00"). This turns the named fields
 * of a response into numbers, leaving null/undefined as they are. */
export function numbers<T>(raw: unknown, keys: readonly string[]): T {
  const out = { ...(raw as Record<string, unknown>) }
  for (const key of keys) {
    if (out[key] !== null && out[key] !== undefined) out[key] = Number(out[key])
  }
  return out as T
}
