// The browser keeps the profile's secret key (not a guessable id).
const KEY = "saybetter.profileKey";

export const profile = {
  get id() {
    try { return localStorage.getItem(KEY); } catch { return null; }
  },
  set(id) {
    try { localStorage.setItem(KEY, String(id)); } catch { /* private mode: profile lasts this tab only */ }
    memoryId = String(id);
  },
  clear() {
    try { localStorage.removeItem(KEY); } catch { /* ignore */ }
    memoryId = null;
  },
};
let memoryId = null;

function currentId() {
  return profile.id ?? memoryId;
}

export class ApiError extends Error {
  constructor(status, message) { super(message); this.status = status; }
}

export async function api(path, { method = "GET", body, form } = {}) {
  const headers = {};
  const id = currentId();
  if (id) headers["X-Profile-Key"] = id;
  let payload;
  if (form) payload = form;
  else if (body !== undefined) { headers["Content-Type"] = "application/json"; payload = JSON.stringify(body); }
  let res;
  try {
    res = await fetch(path, { method, headers, body: payload });
  } catch {
    throw new ApiError(0, "Can't reach the SayBetter server. Is it running?");
  }
  if (res.status === 204) return null;
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = typeof data.detail === "string" ? data.detail : Array.isArray(data.detail) ? data.detail.map((d) => d.msg).join("; ") : `Error ${res.status}`;
    throw new ApiError(res.status, detail);
  }
  return data;
}
