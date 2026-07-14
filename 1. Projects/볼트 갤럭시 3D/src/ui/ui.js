import { state, setState, bus } from '../state.js';

const TYPE_LABEL = { note: '노트', hub: '허브(가상 노드)', attachment: '첨부파일' };

export class UIController {
  constructor() {
    this.el = {
      hud: document.getElementById('hud'),
      themeSelect: document.getElementById('theme-select'),
      speedSlider: document.getElementById('speed-slider'),
      speedValue: document.getElementById('speed-value'),
      spacingSlider: document.getElementById('spacing-slider'),
      spacingValue: document.getElementById('spacing-value'),
      toggleHubs: document.getElementById('toggle-hubs'),
      toggleAttachments: document.getElementById('toggle-attachments'),
      nodeLabel: document.getElementById('node-label'),
      notePanel: document.getElementById('note-panel'),
      notePanelClose: document.getElementById('note-panel-close'),
      notePanelTitle: document.getElementById('note-panel-title'),
      notePanelMeta: document.getElementById('note-panel-meta'),
      notePanelBody: document.getElementById('note-panel-body'),
      loading: document.getElementById('loading'),
      crosshair: document.getElementById('crosshair')
    };
    this._bind();
  }

  _bind() {
    this.el.themeSelect.addEventListener('change', (e) => {
      setState({ themeId: e.target.value });
    });
    this.el.speedSlider.addEventListener('input', (e) => {
      const v = parseFloat(e.target.value);
      setState({ speedFactor: v });
      this.el.speedValue.textContent = Math.round(v * 100) + '%';
    });
    this.el.spacingSlider.addEventListener('input', (e) => {
      const v = parseFloat(e.target.value);
      setState({ linkSpacing: v });
      this.el.spacingValue.textContent = Math.round(v);
    });
    this.el.toggleHubs.addEventListener('change', (e) => {
      setState({ showHubs: e.target.checked });
    });
    this.el.toggleAttachments.addEventListener('change', (e) => {
      setState({ showAttachments: e.target.checked });
    });
    this.el.notePanelClose.addEventListener('click', () => this.closeNotePanel());

    window.addEventListener('keydown', (e) => {
      if (e.code === 'KeyZ') {
        setState({ zen: !state.zen });
      } else if (e.code === 'Escape') {
        if (state.openNoteId !== null) {
          this.closeNotePanel();
        } else {
          bus.emit('escape', {});
        }
      } else if (e.code === 'KeyV') {
        bus.emit('diveRequested', {});
      }
    });

    bus.on('state', (s) => {
      this.el.hud.classList.toggle('zen', s.zen);
    });

    this.el.speedValue.textContent = Math.round(state.speedFactor * 100) + '%';
    this.el.spacingValue.textContent = Math.round(state.linkSpacing);
    this.el.spacingSlider.value = state.linkSpacing;
  }

  hideLoading() {
    this.el.loading.classList.add('hidden');
  }

  updateNodeLabel(screenX, screenY, text, visible) {
    const el = this.el.nodeLabel;
    if (!visible || state.openNoteId !== null) {
      el.classList.add('hidden');
      return;
    }
    el.textContent = text;
    el.style.left = screenX + 'px';
    el.style.top = screenY + 'px';
    el.classList.remove('hidden');
  }

  async openNotePanel(node) {
    setState({ openNoteId: node.n });
    this.el.notePanel.classList.remove('hidden');
    this.el.notePanelTitle.textContent = node.t;
    this.el.notePanelMeta.textContent = `${TYPE_LABEL[node.type] || node.type} · ${node.folder}`;

    if (node.type !== 'note') {
      this.el.notePanelBody.textContent = node.type === 'hub'
        ? '이 노드는 실제 파일이 없는 허브(다른 노트들이 자주 참조하는 이름)입니다.'
        : '첨부파일 노드입니다. 원문 텍스트가 없습니다.';
      return;
    }

    this.el.notePanelBody.textContent = '불러오는 중…';
    try {
      const res = await fetch(`/data/notes/${node.n}.json`);
      const data = await res.json();
      this.el.notePanelBody.textContent = data.body?.trim() || '(내용 없음)';
    } catch (err) {
      this.el.notePanelBody.textContent = '노트를 불러오지 못했습니다.';
    }
  }

  closeNotePanel() {
    setState({ openNoteId: null });
    this.el.notePanel.classList.add('hidden');
  }
}
