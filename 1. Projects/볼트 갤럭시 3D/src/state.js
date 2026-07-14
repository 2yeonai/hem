import { Emitter } from './util.js';

// Central app state + event bus. UI, graph, flight and dive modules all
// read/write here instead of reaching into each other directly.
export const bus = new Emitter();

export const state = {
  themeId: 'deepspace',
  showHubs: true,
  showAttachments: false,
  linkSpacing: 90,       // target link length for the force sim
  speedFactor: 0.25,     // 0..1, mapped to max avatar speed
  zen: false,
  hyperdrive: false,
  avatarKind: 'dart',    // 'dart' | 'blob'
  openNoteId: null,
  diving: false
};

export function setState(patch) {
  Object.assign(state, patch);
  bus.emit('state', state);
}
