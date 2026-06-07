import { T, saude as saudeCor } from "../theme";

// ── Linha de conformidade por ano (SVG) ──────────────────────────
export function Trend({ anos, media }) {
  const W = 560, H = 168, mL = 6, mR = 30, mT = 18, mB = 24;
  const pw = W - mL - mR, ph = H - mT - mB;
  if (!anos.length) return <Vazio h={H} />;
  const xs = anos.map((_, i) => mL + (anos.length === 1 ? pw / 2 : (i / (anos.length - 1)) * pw));
  const yOf = (v) => mT + (1 - v / 100) * ph;
  const pts = anos.map((a, i) => [xs[i], yOf(a.conf)]);
  const line = pts.map((p, i) => (i ? "L" : "M") + p[0].toFixed(1) + " " + p[1].toFixed(1)).join(" ");
  const area = line + ` L${xs[xs.length - 1].toFixed(1)} ${(mT + ph).toFixed(1)} L${xs[0].toFixed(1)} ${(mT + ph).toFixed(1)} Z`;

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto block">
      {[0, 50, 100].map((g) => (
        <g key={g}>
          <line x1={mL} x2={W - mR} y1={yOf(g)} y2={yOf(g)} stroke={T.hair2} />
          <text x={W - mR + 5} y={yOf(g) + 3} fontFamily={T.mono} fontSize="9" fill={T.ink3}>{g}</text>
        </g>
      ))}
      <line x1={mL} x2={W - mR} y1={yOf(media)} y2={yOf(media)} stroke={T.blue} strokeDasharray="4 4" opacity="0.5" />
      <path d={area} fill={T.blueLt} opacity="0.7" />
      <path d={line} fill="none" stroke={T.blue} strokeWidth="2.5" strokeLinejoin="round" strokeLinecap="round" />
      {pts.map((p, i) => (
        <g key={i}>
          <circle cx={p[0]} cy={p[1]} r="3.5" fill={T.paper} stroke={T.blue} strokeWidth="2" />
          <text x={p[0]} y={H - 7} textAnchor="middle" fontFamily={T.mono} fontSize="9" fill={T.ink3}>{anos[i].ano.slice(2)}</text>
        </g>
      ))}
    </svg>
  );
}

// ── Mapa esquemático (bolhas por ponto) ──────────────────────────
export function MiniMap({ geo }) {
  const W = 520, H = 250, pad = 40;
  if (!geo.length) return <Vazio h={H} />;
  const px = (x) => pad + x * (W - 2 * pad);
  const py = (y) => pad + y * (H - 2 * pad);
  const maxN = Math.max(...geo.map((g) => g.n));
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto block rounded-[10px]" style={{ background: T.paper2 }}>
      <defs>
        <pattern id="grid-op" width="34" height="34" patternUnits="userSpaceOnUse">
          <path d="M34 0H0V34" fill="none" stroke={T.hair} strokeWidth="1" />
        </pattern>
      </defs>
      <rect width={W} height={H} fill="url(#grid-op)" />
      {geo.map((g) => {
        const c = saudeCor(g.saude);
        const r = 11 + (g.n / maxN) * 7;
        return (
          <g key={g.nome}>
            <circle cx={px(g.x)} cy={py(g.y)} r={r} fill={c} opacity="0.9" stroke={T.paper} strokeWidth="2.5" />
            <text x={px(g.x)} y={py(g.y) + 4} textAnchor="middle" fontSize="11" fontWeight="700" fill="#fff">{g.n}</text>
            <text x={px(g.x)} y={py(g.y) + r + 13} textAnchor="middle" fontSize="10.5" fontWeight="600" fill={T.ink2}>{g.nome}</text>
          </g>
        );
      })}
    </svg>
  );
}

function Vazio({ h }) {
  return (
    <div className="flex items-center justify-center text-ink3 text-sm" style={{ height: h }}>
      Sem dados para os filtros atuais.
    </div>
  );
}
