/* Real backend client for the live reader app. Same-origin calls to the P0 API
   (core.py). Bearer token kept in memory (no localStorage, per security). */
window.IrbisAPI = (function () {
  let token = null;
  const auth = () => (token ? { Authorization: "Bearer " + token } : {});

  async function jget(path) {
    const r = await fetch(path, { headers: auth() });
    return { status: r.status, json: await r.json().catch(() => null) };
  }
  async function jpost(path, body) {
    const r = await fetch(path, {
      method: "POST",
      headers: Object.assign({ "Content-Type": "application/json" }, auth()),
      body: body ? JSON.stringify(body) : undefined,
    });
    return { status: r.status, json: await r.json().catch(() => null) };
  }
  const qs = (o) => Object.keys(o).map((k) => k + "=" + encodeURIComponent(o[k])).join("&");

  return {
    async initGuest() {
      const r = await fetch("/api/auth/guest", { method: "POST" });
      const j = await r.json();
      token = j.data.token;
      return j.data;
    },
    health: () => jget("/api/health"),
    search: (prefix, q, page, pageSize) =>
      jget("/api/search?" + qs({ prefix, q, page, pageSize })),
    terms: (start, count) => jget("/api/terms?" + qs({ start, count: count || 8 })),
    record: (db, mfn) => jget("/api/record/" + db + "/" + mfn),
    // <img> can't send the bearer header -> pass the token as a query param
    coverUrl: (db, mfn) => "/api/cover/" + db + "/" + mfn + (token ? "?t=" + encodeURIComponent(token) : ""),
    async loginReader(ticket) {
      const r = await jpost("/api/auth/reader", { ticket });
      if (r.status === 200 && r.json && r.json.ok) token = r.json.data.token;
      return r;
    },
    async loginStaff(login, password) {
      const r = await jpost("/api/auth/staff", { login, password });
      if (r.status === 200 && r.json && r.json.ok) token = r.json.data.token;
      return r;
    },
    order: (db, mfn) => jpost("/api/order", { db, mfn }),
    worklist: (db) => jget("/api/worklist/" + db),
    saveRecord: (db, mfn, fields) => jpost("/api/record/" + db + "/" + mfn, { fields }),
  };
})();
