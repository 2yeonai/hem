// build-graph.mjs
// Scans an Obsidian vault ahead of time and writes:
//   public/data/graph.json          - all nodes + edges (small, loaded up front)
//   public/data/notes/<numId>.json  - each note's body text (fetched on demand)
//
// Run: VAULT_PATH="/path/to/vault" node scripts/build-graph.mjs
// If VAULT_PATH is not set, defaults to three levels above this script,
// which matches this project living at <vault>/1. Projects/<this folder>/scripts/.

import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PROJECT_ROOT = path.resolve(__dirname, '..');
const VAULT_DIR = process.env.VAULT_PATH
  ? path.resolve(process.env.VAULT_PATH)
  : path.resolve(PROJECT_ROOT, '..', '..');

const OUT_DIR = path.join(PROJECT_ROOT, 'public', 'data');
const NOTES_OUT_DIR = path.join(OUT_DIR, 'notes');

const SKIP_DIR_NAMES = new Set([
  '.obsidian', '.git', '.claude', 'node_modules', 'dist', '.trash', '.DS_Store'
]);

const IMAGE_EXT = new Set(['.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg', '.bmp']);
const OTHER_ATTACH_EXT = new Set(['.pdf', '.mp3', '.mp4', '.mov', '.wav', '.m4a', '.zip', '.docx', '.pptx', '.xlsx', '.csv']);

function isStaleBackup(name) {
  return name.includes('.stale-') || name.includes('.truncated-');
}

function toPosix(p) {
  return p.split(path.sep).join('/');
}

// ---- 1. Walk the vault ----
async function walk(dir, projectRootAbs, out = []) {
  let entries;
  try {
    entries = await fs.readdir(dir, { withFileTypes: true });
  } catch {
    return out;
  }
  for (const entry of entries) {
    if (entry.name.startsWith('.') && entry.name !== '.') {
      if (!SKIP_DIR_NAMES.has(entry.name) && entry.isDirectory()) {
        // allow other dotfolders to be skipped too (safety)
        continue;
      }
      if (!entry.isDirectory()) continue; // skip dotfiles
    }
    const abs = path.join(dir, entry.name);
    if (abs === projectRootAbs) continue; // never scan our own project folder
    if (entry.isDirectory()) {
      if (SKIP_DIR_NAMES.has(entry.name)) continue;
      await walk(abs, projectRootAbs, out);
    } else if (entry.isFile()) {
      if (isStaleBackup(entry.name)) continue;
      out.push(abs);
    }
  }
  return out;
}

console.log(`[vault-galaxy] vault: ${VAULT_DIR}`);
const allFiles = await walk(VAULT_DIR, PROJECT_ROOT, []);

const mdFiles = [];
const attachmentFiles = [];
for (const abs of allFiles) {
  const rel = toPosix(path.relative(VAULT_DIR, abs));
  const ext = path.extname(abs).toLowerCase();
  if (ext === '.md') {
    mdFiles.push({ abs, rel, base: path.basename(rel, ext) });
  } else {
    attachmentFiles.push({ abs, rel, base: path.basename(rel, ext), ext });
  }
}
console.log(`[vault-galaxy] found ${mdFiles.length} markdown files, ${attachmentFiles.length} other files`);

// ---- 2. Resolution maps ----
const noteByRelPath = new Map(); // lowercase rel path (no ext) -> mdFile
const noteByBasename = new Map(); // lowercase basename -> [mdFile]
for (const f of mdFiles) {
  noteByRelPath.set(f.rel.toLowerCase().replace(/\.md$/, ''), f);
  const key = f.base.toLowerCase();
  if (!noteByBasename.has(key)) noteByBasename.set(key, []);
  noteByBasename.get(key).push(f);
}

const attachByRelPath = new Map();
const attachByBasename = new Map();
for (const f of attachmentFiles) {
  attachByRelPath.set(f.rel.toLowerCase(), f);
  const key = (f.base + f.ext).toLowerCase();
  if (!attachByBasename.has(key)) attachByBasename.set(key, []);
  attachByBasename.get(key).push(f);
}

function resolveNote(target) {
  const clean = target.trim().replace(/\\/g, '/').replace(/\.md$/i, '');
  const byPath = noteByRelPath.get(clean.toLowerCase());
  if (byPath) return byPath;
  const base = clean.split('/').pop();
  const candidates = noteByBasename.get(base.toLowerCase());
  if (candidates && candidates.length) {
    return candidates.slice().sort((a, b) => a.rel.localeCompare(b.rel))[0];
  }
  return null;
}

function resolveAttachment(target) {
  const clean = target.trim().replace(/\\/g, '/');
  const byPath = attachByRelPath.get(clean.toLowerCase());
  if (byPath) return byPath;
  const base = clean.split('/').pop();
  const candidates = attachByBasename.get(base.toLowerCase());
  if (candidates && candidates.length) {
    return candidates.slice().sort((a, b) => a.rel.localeCompare(b.rel))[0];
  }
  return null;
}

// ---- 3. Parse links out of each note ----
const WIKILINK_RE = /(!)?\[\[([^\]|#]+)(#[^\]|]*)?(\|[^\]]*)?\]\]/g;

function stripFrontmatter(raw) {
  if (raw.startsWith('---')) {
    const end = raw.indexOf('\n---', 3);
    if (end !== -1) {
      const fm = raw.slice(3, end).trim();
      const body = raw.slice(end + 4).replace(/^\s*\n/, '');
      return { frontmatter: fm, body };
    }
  }
  return { frontmatter: '', body: raw };
}

function extractTitle(frontmatter, fallback) {
  const m = frontmatter.match(/^title:\s*"?([^"\n]+)"?\s*$/m);
  if (m) return m[1].trim();
  return fallback;
}

// node registry ------------------------------------------------------------
const nodes = new Map(); // id -> node
const edgeSet = new Map(); // "a|b" -> {a,b}

function noteNodeId(mdFile) { return 'note::' + mdFile.rel; }

function ensureNoteNode(mdFile, titleFallback) {
  const id = noteNodeId(mdFile);
  if (!nodes.has(id)) {
    nodes.set(id, {
      id, type: 'note', title: titleFallback || mdFile.base,
      folder: mdFile.rel.includes('/') ? mdFile.rel.split('/')[0] : '(root)',
      path: mdFile.rel, degree: 0
    });
  }
  return nodes.get(id);
}

function ensureHubNode(rawTarget) {
  const norm = rawTarget.trim().toLowerCase();
  const id = 'hub::' + norm;
  if (!nodes.has(id)) {
    const label = rawTarget.trim().split('/').pop();
    nodes.set(id, { id, type: 'hub', title: label, folder: 'hub', path: null, degree: 0 });
  }
  return nodes.get(id);
}

function ensureAttachmentNode(rawTarget, resolvedFile) {
  const norm = (resolvedFile ? resolvedFile.rel : rawTarget.trim()).toLowerCase();
  const id = 'attach::' + norm;
  if (!nodes.has(id)) {
    const ext = (resolvedFile ? resolvedFile.ext : path.extname(rawTarget)).toLowerCase();
    const subtype = IMAGE_EXT.has(ext) ? 'image' : (OTHER_ATTACH_EXT.has(ext) ? 'file' : 'file');
    const label = (resolvedFile ? resolvedFile.base + resolvedFile.ext : rawTarget.trim().split('/').pop());
    nodes.set(id, {
      id, type: 'attachment', title: label, folder: 'attachment',
      path: resolvedFile ? resolvedFile.rel : null, degree: 0, subtype
    });
  }
  return nodes.get(id);
}

function addEdge(nodeA, nodeB) {
  if (nodeA.id === nodeB.id) return;
  const key = [nodeA.id, nodeB.id].sort().join('|');
  if (!edgeSet.has(key)) edgeSet.set(key, { a: nodeA.id, b: nodeB.id });
}

const noteTexts = new Map(); // note id -> {title, folder, path, frontmatter, body}

for (const f of mdFiles) {
  let raw;
  try {
    raw = await fs.readFile(f.abs, 'utf8');
  } catch {
    continue;
  }
  const { frontmatter, body } = stripFrontmatter(raw);
  const title = extractTitle(frontmatter, f.base);
  const thisNode = ensureNoteNode(f, title);
  thisNode.title = title;

  let match;
  WIKILINK_RE.lastIndex = 0;
  while ((match = WIKILINK_RE.exec(raw)) !== null) {
    const isEmbed = !!match[1];
    const target = match[2];
    if (!target || !target.trim()) continue;
    const ext = path.extname(target).toLowerCase();
    const looksLikeAttachment = isEmbed && ext && ext !== '.md';

    if (looksLikeAttachment) {
      const resolved = resolveAttachment(target);
      const node = ensureAttachmentNode(target, resolved);
      addEdge(thisNode, node);
    } else {
      const resolvedNote = resolveNote(target);
      if (resolvedNote) {
        const node = ensureNoteNode(resolvedNote);
        addEdge(thisNode, node);
      } else {
        const node = ensureHubNode(target);
        addEdge(thisNode, node);
      }
    }
  }

  noteTexts.set(thisNode.id, {
    title, folder: thisNode.folder, path: f.rel, frontmatter, body
  });
}

// ---- 4. Degree ----
for (const e of edgeSet.values()) {
  nodes.get(e.a).degree++;
  nodes.get(e.b).degree++;
}

// ---- 5. Assign compact numeric ids ----
const nodeList = Array.from(nodes.values());
nodeList.sort((a, b) => b.degree - a.degree);
const idToNum = new Map();
nodeList.forEach((n, i) => idToNum.set(n.id, i));

const outNodes = nodeList.map((n, i) => ({
  n: i,
  id: n.id,
  t: n.title,
  type: n.type,
  folder: n.folder,
  deg: n.degree,
  path: n.path || null,
  subtype: n.subtype || null
}));

const outEdges = Array.from(edgeSet.values()).map(e => [idToNum.get(e.a), idToNum.get(e.b)]);

const stats = {
  notes: nodeList.filter(n => n.type === 'note').length,
  hubs: nodeList.filter(n => n.type === 'hub').length,
  attachments: nodeList.filter(n => n.type === 'attachment').length,
  edges: outEdges.length
};
console.log('[vault-galaxy] stats:', stats);

// ---- 6. Write output ----
await fs.rm(OUT_DIR, { recursive: true, force: true });
await fs.mkdir(NOTES_OUT_DIR, { recursive: true });

const graphJson = {
  generatedAt: new Date().toISOString(),
  vaultName: path.basename(VAULT_DIR),
  stats,
  nodes: outNodes,
  edges: outEdges
};
await fs.writeFile(path.join(OUT_DIR, 'graph.json'), JSON.stringify(graphJson), 'utf8');

for (const n of nodeList) {
  if (n.type !== 'note') continue;
  const num = idToNum.get(n.id);
  const data = noteTexts.get(n.id);
  await fs.writeFile(
    path.join(NOTES_OUT_DIR, `${num}.json`),
    JSON.stringify(data),
    'utf8'
  );
}

console.log(`[vault-galaxy] wrote ${path.join(OUT_DIR, 'graph.json')}`);
console.log(`[vault-galaxy] wrote ${stats.notes} note text files to ${NOTES_OUT_DIR}`);
