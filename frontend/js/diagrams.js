// Side-view (mid-sagittal) mouth diagrams, facing left.
// Every tongue shape uses the same path commands (M C C C L C Z) so the
// browser can morph between them with SMIL <animate>.

const REST = "M72,140 C80,130 100,124 120,123 C150,118 185,112 210,130 C225,145 228,180 226,226 L196,226 C160,214 110,196 72,140 Z";

const SHAPES = {
  alveolar_contact: "M84,102 C86,112 100,122 120,124 C150,120 185,114 210,130 C225,145 228,180 226,226 L196,226 C160,214 100,190 84,102 Z",
  alveolar_near: "M82,109 C86,116 100,122 120,124 C150,120 185,114 210,130 C225,145 228,180 226,226 L196,226 C160,214 100,190 82,109 Z",
  retroflex_contact: "M108,95 C97,99 97,116 120,124 C150,120 185,114 210,130 C225,145 228,180 226,226 L196,226 C160,214 90,190 108,95 Z",
  retroflex_near: "M110,103 C99,106 98,118 120,125 C150,120 185,114 210,130 C225,145 228,180 226,226 L196,226 C160,214 90,190 110,103 Z",
  palatal_near: "M72,140 C80,128 100,108 130,99 C150,93 180,100 210,128 C225,145 228,180 226,226 L196,226 C160,214 110,196 72,140 Z",
  postalveolar_near: "M80,120 C86,108 96,103 110,104 C140,110 180,112 210,130 C225,145 228,180 226,226 L196,226 C160,214 104,194 80,120 Z",
  velar_contact: "M72,142 C82,132 100,126 122,124 C150,120 182,94 206,94 C226,102 228,180 226,226 L196,226 C160,214 110,196 72,142 Z",
};

// kind -> how to draw and animate it
const KINDS = {
  retroflex_approximant: {
    shape: "retroflex_near", label: "Tip curled back, close to the roof — not touching",
    marker: { x: 110, y: 99, contact: false }, air: "M226,160 C205,112 150,104 114,101 C92,104 70,118 34,126",
  },
  retroflex_lateral: {
    shape: "retroflex_contact", label: "Tip curled back, pressed on the roof; air flows round the sides",
    marker: { x: 108, y: 94, contact: true }, sides: true,
  },
  alveolar_lateral: {
    shape: "alveolar_contact", label: "Tip flat on the ridge behind the top teeth; air flows round the sides",
    marker: { x: 84, y: 101, contact: true }, sides: true,
  },
  alveolar_tap: {
    shape: "alveolar_contact", label: "Tip flicks up and taps the ridge once, quickly",
    marker: { x: 84, y: 101, contact: true }, tap: true,
  },
  palatal_approximant: {
    shape: "palatal_near", label: "Middle of the tongue raised toward the roof; tip stays down",
    marker: { x: 138, y: 94, contact: false }, air: "M226,160 C205,118 160,96 138,96 C110,100 76,118 34,126",
  },
  postalveolar_fricative: {
    shape: "postalveolar_near", label: "Front of the tongue just behind the ridge, lips pushed forward; steady 'shh' air",
    marker: { x: 100, y: 99, contact: false }, air: "M226,160 C205,118 150,110 104,101 C84,102 66,120 26,124", lipsForward: true,
  },
  alveolar_fricative: {
    shape: "alveolar_near", label: "Tip close to the ridge, not touching; narrow 'sss' air",
    marker: { x: 83, y: 104, contact: false }, air: "M226,160 C205,118 150,116 84,106 C70,110 58,120 30,124",
  },
  aspirated_velar: {
    shape: "velar_contact", label: "Back of the tongue touches the soft palate, then lets go with a puff of air",
    marker: { x: 206, y: 93, contact: true }, puff: true,
  },
  velar_stop: {
    shape: "velar_contact", label: "Back of the tongue touches the soft palate, then lets go — no extra puff",
    marker: { x: 206, y: 93, contact: true },
  },
};

let uid = 0;

export function diagramLabel(kind) {
  return KINDS[kind]?.label ?? "";
}

/**
 * Returns SVG markup. opts: { animate=true, title, compact=false }
 */
export function diagram(kind, opts = {}) {
  const k = KINDS[kind];
  if (!k) return "";
  const { animate = true, title = "", compact = false } = opts;
  const id = `dg${++uid}`;
  const target = SHAPES[k.shape];
  const anim = !animate ? "" : k.tap
    ? `<animate attributeName="d" dur="1.8s" repeatCount="indefinite" values="${REST};${target};${REST};${REST}" keyTimes="0;0.12;0.26;1" calcMode="spline" keySplines="0.4 0 0.2 1;0.4 0 0.2 1;0 0 1 1"/>`
    : `<animate attributeName="d" dur="3s" repeatCount="indefinite" values="${REST};${target};${target};${REST}" keyTimes="0;0.3;0.78;1" calcMode="spline" keySplines="0.4 0 0.2 1;0 0 1 1;0.4 0 0.2 1"/>`;
  const holdOpacity = animate
    ? `<animate attributeName="opacity" dur="${k.tap ? "1.8s" : "3s"}" repeatCount="indefinite" values="0;0;1;1;0" keyTimes="${k.tap ? "0;0.08;0.12;0.2;1" : "0;0.25;0.32;0.76;0.8"}"/>`
    : "";
  const lipShift = k.lipsForward ? "translate(-5,0)" : "";

  const marker = k.marker.contact
    ? `<circle cx="${k.marker.x}" cy="${k.marker.y}" r="6" class="dg-contact">${holdOpacity}</circle>`
    : `<circle cx="${k.marker.x}" cy="${k.marker.y}" r="7" class="dg-near">${holdOpacity}</circle>`;

  const air = k.air ? `<path d="${k.air}" class="dg-air">${holdOpacity}</path>` : "";
  const sides = "";
  const puff = k.puff ? `<g class="dg-puff">${["0", "8", "16"].map((dx, i) => `<circle cx="${26 - +dx}" cy="${124 + (i - 1) * 6}" r="${4 + i}" opacity="0">${animate ? `<animate attributeName="opacity" dur="3s" repeatCount="indefinite" values="0;0;0.8;0" keyTimes="0;0.78;0.84;1" begin="${i * 0.04}s"/>` : ""}</circle>`).join("")}</g>` : "";

  return `
<svg viewBox="0 0 300 240" class="diagram${compact ? " compact" : ""}" role="img" aria-labelledby="${id}t ${id}d">
  <title id="${id}t">${title || "Mouth diagram"}</title>
  <desc id="${id}d">${k.label}</desc>
  <path class="dg-face" d="M120,6 C82,10 56,30 48,54 L30,80 L44,87 C38,94 39,102 47,106"/>
  <g transform="${lipShift}">
    <path class="dg-lip" d="M47,106 C38,109 37,117 46,120 L60,119 L60,108 Z"/>
    <path class="dg-lip" d="M46,132 C37,135 37,145 48,148 L62,146 L62,131 Z"/>
  </g>
  <path class="dg-face" d="M48,148 C50,162 46,176 54,190 C64,206 92,212 124,214"/>
  <path class="dg-teeth" d="M56,109 L64,109 L66,125 L58,126 Z"/>
  <path class="dg-teeth" d="M58,131 L65,130 L65,147 L59,147 Z"/>
  <path class="dg-palate" d="M62,111 C70,103 78,99 88,98 C110,89 140,81 168,82 C190,84 210,92 222,106 C226,112 226,118 222,122"/>
  <path class="dg-wall" d="M238,96 C243,140 243,190 238,232"/>
  <path class="dg-floor" d="M65,147 C90,180 150,205 200,216"/>
  ${air}
  <path class="dg-tongue" d="${animate ? REST : target}">${anim}</path>
  ${marker}
  ${sides}
  ${puff}
  ${compact ? "" : `<g class="dg-labels">
    <text x="4" y="114">lips</text>
    <text x="74" y="86">ridge</text>
    <text x="118" y="74">roof</text>
    <text x="188" y="78">soft palate</text>
    <text x="140" y="190">tongue</text>
  </g>`}
</svg>`;
}
