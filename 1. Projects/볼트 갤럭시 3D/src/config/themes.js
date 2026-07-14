import { hashColor } from '../util.js';

// Data-driven themes: colors, fog, lighting, node coloring, glow.
// Adding a new theme is just adding a new entry here.

export const THEMES = {
  deepspace: {
    id: 'deepspace',
    label: '딥 스페이스',
    background: 0x02030a,
    fog: { color: 0x02030a, near: 80, far: 950 },
    ambient: { color: 0x6f86ff, intensity: 0.28 },
    keyLight: { color: 0xaecbff, intensity: 1.15 },
    rimLight: { color: 0x3d5aff, intensity: 0.4 },
    starColor: 0xffffff,
    starDensity: 6000,
    bloom: { strength: 1.05, radius: 0.5, threshold: 0.18 },
    edgeColor: 0x3a5a8f,
    edgeOpacity: 0.35,
    hubColor: 0xffcf6b,
    attachmentColor: 0x9aa3b5,
    folderColors: {
      '0. Docs': 0x5fd0ff,
      '1. Projects': 0xff6b6b,
      '2. Areas': 0x6bffb0,
      '3. Resources': 0xc48bff,
      '4. Archive': 0x8890a0,
      '5. Zettelkasten': 0xffe36b,
      '6. Templates': 0x6bc9ff,
      '7. Attachments': 0x9a9aa5,
      'hub': 0xffcf6b,
      'attachment': 0x9aa3b5
    },
    fallbackFolderColor: (folder) => hashColor(folder)
  },

  nebula: {
    id: 'nebula',
    label: '네뷸라',
    background: 0x0c0417,
    fog: { color: 0x1a0a2e, near: 50, far: 700 },
    ambient: { color: 0xff7ad9, intensity: 0.35 },
    keyLight: { color: 0xb98bff, intensity: 1.3 },
    rimLight: { color: 0xff5fae, intensity: 0.55 },
    starColor: 0xffe0fa,
    starDensity: 5000,
    bloom: { strength: 1.5, radius: 0.7, threshold: 0.1 },
    edgeColor: 0x9a5fff,
    edgeOpacity: 0.4,
    hubColor: 0xffb84d,
    attachmentColor: 0xd6b8ff,
    folderColors: {
      '0. Docs': 0x5fe0ff,
      '1. Projects': 0xff5f8f,
      '2. Areas': 0x5fffc4,
      '3. Resources': 0xd68bff,
      '4. Archive': 0x9a86c9,
      '5. Zettelkasten': 0xffe45f,
      '6. Templates': 0x5fb4ff,
      '7. Attachments': 0xd6b8ff,
      'hub': 0xffb84d,
      'attachment': 0xd6b8ff
    },
    fallbackFolderColor: (folder) => hashColor(folder)
  }
};

export function colorForNode(theme, node) {
  if (node.type === 'hub') return theme.hubColor;
  if (node.type === 'attachment') return theme.attachmentColor;
  const named = theme.folderColors[node.folder];
  if (named !== undefined) return named;
  return theme.fallbackFolderColor(node.folder);
}

export function getTheme(id) {
  return THEMES[id] || THEMES.deepspace;
}
