// Kili the parrot ("kili" is Tamil for parrot — parrots copy speech) and the icon set.

/**
 * Kili states: idle | listening | thinking | happy | encourage
 * The state only changes a class; CSS handles the pose so motion can be
 * switched off for people who prefer reduced motion.
 */
export function kili(state = "idle", { size = 120, label = "Kili the parrot" } = {}) {
  return `
<span class="kili kili--${state}" style="--kili-size:${size}px" role="img" aria-label="${label}">
<svg viewBox="0 0 120 130" aria-hidden="true">
  <g class="kili-tail">
    <path d="M70 96 L92 126 L80 127 L66 104 Z" fill="var(--grape)" stroke="var(--ink)" stroke-width="2.5" stroke-linejoin="round"/>
    <path d="M62 100 L74 128 L62 128 L56 104 Z" fill="var(--coral)" stroke="var(--ink)" stroke-width="2.5" stroke-linejoin="round"/>
  </g>
  <g class="kili-hop">
    <g class="kili-feet">
      <path d="M50 108 q-2 7 -8 8 M50 108 q1 7 -2 9" stroke="var(--ink)" stroke-width="2.5" fill="none" stroke-linecap="round"/>
      <path d="M68 108 q2 7 8 8 M68 108 q-1 7 2 9" stroke="var(--ink)" stroke-width="2.5" fill="none" stroke-linecap="round"/>
    </g>
    <ellipse cx="59" cy="80" rx="29" ry="31" fill="var(--sky)" stroke="var(--ink)" stroke-width="2.5"/>
    <ellipse cx="59" cy="88" rx="17" ry="19" fill="#CFE1FF"/>
    <path class="kili-wing" d="M32 72 q-10 18 4 32 q10 -6 10 -20 q-4 -10 -14 -12 Z" fill="#3B82F6" stroke="var(--ink)" stroke-width="2.5" stroke-linejoin="round"/>
    <g class="kili-head">
      <path d="M50 18 q2 -12 8 -14 q-1 8 2 12 M60 16 q6 -10 13 -9 q-4 6 -4 12" fill="var(--sun)" stroke="var(--ink)" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round"/>
      <circle cx="60" cy="40" r="25" fill="var(--sky)" stroke="var(--ink)" stroke-width="2.5"/>
      <circle cx="44" cy="49" r="5.5" fill="var(--sun)"/>
      <circle cx="76" cy="49" r="5.5" fill="var(--sun)"/>
      <g class="kili-eye-open">
        <circle cx="50" cy="37" r="7" fill="#fff" stroke="var(--ink)" stroke-width="2"/>
        <circle cx="70" cy="37" r="7" fill="#fff" stroke="var(--ink)" stroke-width="2"/>
        <circle class="kili-pupil" cx="51" cy="38" r="3.4" fill="var(--ink)"/>
        <circle class="kili-pupil" cx="71" cy="38" r="3.4" fill="var(--ink)"/>
        <g class="kili-lids">
          <rect x="42" y="29" width="16" height="16" rx="8" fill="var(--sky)"/>
          <rect x="62" y="29" width="16" height="16" rx="8" fill="var(--sky)"/>
        </g>
      </g>
      <g class="kili-eye-happy" stroke="var(--ink)" stroke-width="2.6" fill="none" stroke-linecap="round">
        <path d="M44 39 q6 -8 12 0"/><path d="M64 39 q6 -8 12 0"/>
      </g>
      <path d="M52 46 Q60 41 68 46 Q67 57 60 62 Q53 57 52 46 Z" fill="var(--coral)" stroke="var(--ink)" stroke-width="2.5" stroke-linejoin="round"/>
      <path d="M55 52 Q60 55 65 52" stroke="var(--ink)" stroke-width="1.6" fill="none" stroke-linecap="round"/>
    </g>
  </g>
  <g class="kili-waves" stroke="var(--sky-deep)" stroke-width="2.6" fill="none" stroke-linecap="round">
    <path d="M94 30 q6 8 0 16"/><path d="M101 25 q10 13 0 26"/>
  </g>
  <g class="kili-dots" fill="var(--grape)">
    <circle cx="92" cy="14" r="3.2"/><circle cx="101" cy="14" r="3.2"/><circle cx="110" cy="14" r="3.2"/>
  </g>
  <g class="kili-sparkle" fill="var(--sun)" stroke="var(--ink)" stroke-width="1.8" stroke-linejoin="round">
    <path d="M98 22 l3 7 7 3 -7 3 -3 7 -3 -7 -7 -3 7 -3 Z"/>
    <path d="M16 30 l2 4 4 2 -4 2 -2 4 -2 -4 -4 -2 4 -2 Z"/>
  </g>
</svg></span>`;
}

export function setKili(root, state) {
  root?.querySelectorAll(".kili").forEach((k) => {
    k.className = `kili kili--${state}`;
  });
}

// Lucide-style 24px stroke icons (consistent 2px stroke, round joins).
const PATHS = {
  speaker: '<path d="M11 5 6 9H2v6h4l5 4z"/><path d="M15.5 8.5a5 5 0 0 1 0 7"/><path d="M19 5a10 10 0 0 1 0 14"/>',
  play: '<path d="M7 4v16l13-8z"/>',
  check: '<path d="M20 6 9 17l-5-5"/>',
  mic: '<rect x="9" y="2" width="6" height="12" rx="3"/><path d="M5 10a7 7 0 0 0 14 0"/><path d="M12 17v4"/>',
  stop: '<rect x="6" y="6" width="12" height="12" rx="2.5"/>',
  retry: '<path d="M3 12a9 9 0 1 0 3-6.7"/><path d="M3 4v5h5"/>',
  arrow: '<path d="M5 12h14"/><path d="m13 6 6 6-6 6"/>',
  swap: '<path d="M7 7h11l-3-3"/><path d="M17 17H6l3 3"/>',
  help: '<circle cx="12" cy="12" r="9"/><path d="M9.5 9a2.5 2.5 0 1 1 3.5 2.3c-.6.3-1 .9-1 1.6V14"/><path d="M12 17.5h.01"/>',
  upload: '<path d="M12 15V4"/><path d="m7 9 5-5 5 5"/><path d="M5 20h14"/>',
  book: '<path d="M4 5a2 2 0 0 1 2-2h13v16H6a2 2 0 0 0-2 2z"/><path d="M4 21V5"/>',
  sparkle: '<path d="M12 3l2 6 6 2-6 2-2 6-2-6-6-2 6-2z"/>',
};

export function icon(name, cls = "") {
  return `<svg class="icon ${cls}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${PATHS[name] || ""}</svg>`;
}
