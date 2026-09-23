/**
 * Complete a hand-written fetch mock so it behaves like a real Response.
 *
 * The API layer is split: `http.js` reads `response.text()` (so it can report
 * non-JSON error bodies), while the AI clients read `response.json()`. A mock
 * that implements only one of them passes in one module and throws in the
 * other, which is exactly how these specs drifted out of sync.
 */
export function asResponse(mock = {}) {
  const base = { ok: true, status: 200, ...mock };
  return {
    ...base,
    json: base.json ?? (async () => JSON.parse(await base.text())),
    text: base.text ?? (async () => JSON.stringify(await base.json())),
  };
}
