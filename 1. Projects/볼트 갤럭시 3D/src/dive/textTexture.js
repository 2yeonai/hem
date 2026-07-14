import * as THREE from 'three';

// Renders a chunk of note text into a repeating canvas texture:
// glowing white glyphs on a transparent background. Purely decorative —
// not meant to be legible at a distance, just texture.
export function makeTextTileTexture(text, { fontSize = 40, cols = 18, rows = 18 } = {}) {
  const clean = (text || '').replace(/\s+/g, ' ').trim() || '빈 노트 · empty note';
  const chars = Array.from(clean);
  const cell = 48;
  const canvas = document.createElement('canvas');
  canvas.width = cols * cell;
  canvas.height = rows * cell;
  const ctx = canvas.getContext('2d');
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.font = `${fontSize}px "Malgun Gothic", "Apple SD Gothic Neo", sans-serif`;
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.shadowColor = 'rgba(255,255,255,0.9)';
  ctx.shadowBlur = 10;
  ctx.fillStyle = 'rgba(255,255,255,0.95)';

  let ci = 0;
  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      let ch = chars[ci % chars.length];
      ci++;
      if (ch === ' ') continue;
      ctx.fillText(ch, c * cell + cell / 2, r * cell + cell / 2);
    }
  }
  const tex = new THREE.CanvasTexture(canvas);
  tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
  return tex;
}

// Tall scrolling texture for aurora ribbons — same text, different framing.
export function makeAuroraTexture(text, seed = 0) {
  const clean = (text || '').replace(/\s+/g, ' ').trim() || '빈 노트 empty note ';
  const canvas = document.createElement('canvas');
  canvas.width = 256;
  canvas.height = 1024;
  const ctx = canvas.getContext('2d');
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.font = '34px "Malgun Gothic", "Apple SD Gothic Neo", sans-serif';
  ctx.textAlign = 'center';
  ctx.fillStyle = 'rgba(255,255,255,0.9)';
  ctx.shadowColor = 'rgba(255,255,255,0.8)';
  ctx.shadowBlur = 12;
  const chars = Array.from(clean);
  let y = 40;
  let ci = seed % chars.length;
  while (y < canvas.height - 20) {
    ctx.fillText(chars[ci % chars.length], canvas.width / 2, y);
    y += 40;
    ci++;
  }
  const tex = new THREE.CanvasTexture(canvas);
  tex.wrapS = THREE.RepeatWrapping;
  tex.wrapT = THREE.RepeatWrapping;
  return tex;
}
