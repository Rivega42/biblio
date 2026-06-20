/* global React */
/* ============================================================
   SeasonalFX — декоративный оверлей для сезонных тем.
   «Новый год»  → стеатральная золотая гирлянда (мерцает) + снег + лёгкая дымка софита.
   «8 марта»    → тёплый сценический софит + падающие лепестки роз и мимозы.
   Оверлей всегда pointer-events:none, лежит НИЖЕ модалок/тостов (z=150),
   уважает prefers-reduced-motion (падение отключается, статичная сцена остаётся).
   Чистая декорация — на смысл/доступность контента не влияет (aria-hidden).
   ============================================================ */
(function () {
  // детерминированный «рандом», чтобы частицы не прыгали при ре-рендере
  function rng(seed) {
    let s = seed % 2147483647;
    if (s <= 0) s += 2147483646;
    return () => (s = (s * 16807) % 2147483647) / 2147483647;
  }

  const FX_CSS = `
  @keyframes irbisFall {
    0%   { transform: translate3d(0,-12vh,0) rotate(0deg); }
    100% { transform: translate3d(var(--drift,0px),112vh,0) rotate(var(--spin,360deg)); }
  }
  @keyframes irbisSway {
    0%,100% { margin-left: -14px; }
    50%     { margin-left: 14px; }
  }
  @keyframes irbisTwinkle {
    0%,100% { opacity: .35; filter: brightness(.8); }
    50%     { opacity: 1;   filter: brightness(1.35); }
  }
  @keyframes irbisGlow {
    0%,100% { opacity: .55; transform: scale(1); }
    50%     { opacity: .85; transform: scale(1.06); }
  }
  .irbis-fx-fall { position:absolute; top:0; will-change: transform; animation: irbisFall linear infinite; }
  .irbis-fx-fall > i { display:block; animation: irbisSway ease-in-out infinite; }
  .irbis-fx-bulb { animation: irbisTwinkle ease-in-out infinite; transform-origin:center; }
  .irbis-fx-glow { animation: irbisGlow ease-in-out infinite; }
  @media (prefers-reduced-motion: reduce) {
    .irbis-fx-fall { display:none !important; }
    .irbis-fx-bulb, .irbis-fx-glow { animation: none !important; opacity:.8 !important; }
  }`;

  // ---- Снег (Новый год) ----
  function makeSnow() {
    const r = rng(7);
    return Array.from({ length: 44 }, (_, i) => {
      const size = 3 + r() * 9;
      const depth = r();
      return {
        id: i,
        left: r() * 100,
        size,
        dur: 9 + r() * 12,
        delay: -r() * 16,
        drift: (r() * 2 - 1) * 90,
        spin: (r() * 2 - 1) * 200,
        sway: 5 + r() * 6,
        opacity: 0.45 + depth * 0.5,
        blur: depth < 0.3 ? 1.2 : 0,
        star: r() > 0.78,
      };
    });
  }

  // ---- Лепестки (8 марта) ----
  function makePetals() {
    const r = rng(23);
    const palette = ["#E27FA0", "#D85F86", "#EEAEC4", "#C44C70"];
    return Array.from({ length: 30 }, (_, i) => {
      const mimosa = r() > 0.74;
      const size = mimosa ? 7 + r() * 5 : 11 + r() * 12;
      const depth = r();
      return {
        id: i,
        left: r() * 100,
        size,
        dur: 8 + r() * 9,
        delay: -r() * 14,
        drift: (r() * 2 - 1) * 130,
        spin: (r() * 2 - 1) * 420,
        sway: 7 + r() * 8,
        opacity: 0.6 + depth * 0.4,
        mimosa,
        color: mimosa ? "#E3B100" : palette[i % palette.length],
        blur: depth < 0.28 ? 1 : 0,
      };
    });
  }

  // Гирлянда: провисающая SVG-нить с мерцающими лампочками (театральная маркиза)
  function Garland() {
    const segs = 16;
    const W = 1200;
    const sag = 30;
    const step = W / segs;
    const pts = [];
    let d = "M 0 6";
    for (let i = 0; i < segs; i++) {
      const x0 = i * step;
      const x1 = (i + 1) * step;
      const cx = (x0 + x1) / 2;
      d += ` Q ${cx} ${6 + sag} ${x1} 6`;
      pts.push({ x: cx, y: 6 + sag * 0.92 });
    }
    const warm = ["#E6CB86", "#C8A24A", "#FBEFC9", "#D8A93F"];
    return (
      <svg viewBox={`0 0 ${W} 44`} preserveAspectRatio="none" width="100%" height="44"
        style={{ position: "absolute", top: 0, left: 0, display: "block" }} aria-hidden="true">
        <path d={d} fill="none" stroke="#6E5A2E" strokeWidth="1.4" opacity="0.55" />
        {pts.map((p, i) => (
          <g key={i} className="irbis-fx-bulb" style={{ animationDuration: `${1.6 + (i % 5) * 0.35}s`, animationDelay: `${(i % 7) * 0.22}s` }}>
            <line x1={p.x} y1={p.y - 7} x2={p.x} y2={p.y - 1} stroke="#6E5A2E" strokeWidth="1.2" opacity="0.6" />
            <circle cx={p.x} cy={p.y + 3} r="5.4" fill={warm[i % warm.length]} />
            <circle cx={p.x} cy={p.y + 3} r="9.5" fill={warm[i % warm.length]} opacity="0.28" />
          </g>
        ))}
      </svg>
    );
  }

  function SeasonalFX({ theme }) {
    const isNY = theme === "newyear";
    const isM8 = theme === "march8";
    const snow = React.useMemo(makeSnow, []);
    const petals = React.useMemo(makePetals, []);
    if (!isNY && !isM8) return null;

    return (
      <div aria-hidden="true" style={{
        position: "fixed", inset: 0, overflow: "hidden", pointerEvents: "none", zIndex: 150,
      }}>
        <style>{FX_CSS}</style>

        {isNY && (
          <React.Fragment>
            {/* мягкая дымка софита сверху */}
            <div className="irbis-fx-glow" style={{
              position: "absolute", top: "-30vh", left: "50%", width: "120vw", height: "70vh",
              transform: "translateX(-50%)", animationDuration: "7s",
              background: "radial-gradient(ellipse at center top, rgba(200,162,74,.20), rgba(200,162,74,0) 62%)",
            }} />
            <Garland />
            {snow.map((p) => (
              <div key={p.id} className="irbis-fx-fall" style={{
                left: p.left + "vw", width: p.size, height: p.size,
                animationDuration: p.dur + "s", animationDelay: p.delay + "s",
                "--drift": p.drift + "px", "--spin": p.spin + "deg",
              }}>
                <i style={{
                  width: p.size, height: p.size, animationDuration: p.sway + "s",
                  display: "flex", alignItems: "center", justifyContent: "center",
                  color: "#FFFFFF", fontSize: p.size + 4, lineHeight: 1,
                  opacity: p.opacity, filter: p.blur ? `blur(${p.blur}px)` : "none",
                  textShadow: "0 0 4px rgba(120,150,190,.5)",
                }}>
                  {p.star ? "❄" : (
                    <span style={{ width: p.size, height: p.size, borderRadius: "50%", background: "#FFFFFF", display: "block", boxShadow: "0 0 5px rgba(150,180,220,.6)" }} />
                  )}
                </i>
              </div>
            ))}
          </React.Fragment>
        )}

        {isM8 && (
          <React.Fragment>
            {/* тёплый сценический софит сверху + мягкое свечение «рампы» снизу */}
            <div className="irbis-fx-glow" style={{
              position: "absolute", top: "-28vh", left: "50%", width: "110vw", height: "66vh",
              transform: "translateX(-50%)", animationDuration: "8s",
              background: "radial-gradient(ellipse at center top, rgba(227,177,0,.16), rgba(168,50,79,.05) 50%, rgba(0,0,0,0) 68%)",
            }} />
            {petals.map((p) => (
              <div key={p.id} className="irbis-fx-fall" style={{
                left: p.left + "vw", width: p.size, height: p.size,
                animationDuration: p.dur + "s", animationDelay: p.delay + "s",
                "--drift": p.drift + "px", "--spin": p.spin + "deg",
              }}>
                <i style={{
                  width: p.size, height: p.size, animationDuration: p.sway + "s",
                  opacity: p.opacity, filter: p.blur ? `blur(${p.blur}px)` : "none",
                  background: p.mimosa
                    ? `radial-gradient(circle at 38% 35%, #F6D656, ${p.color})`
                    : `radial-gradient(circle at 32% 28%, rgba(255,255,255,.7), ${p.color} 70%)`,
                  borderRadius: p.mimosa ? "50%" : "100% 0 100% 0",
                  boxShadow: p.mimosa ? "0 0 4px rgba(227,177,0,.4)" : "0 1px 3px rgba(120,30,60,.18)",
                }} />
              </div>
            ))}
          </React.Fragment>
        )}
      </div>
    );
  }

  Object.assign(window, { SeasonalFX });
})();
