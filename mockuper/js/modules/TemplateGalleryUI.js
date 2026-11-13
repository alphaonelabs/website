/**
 * TemplateGalleryUI
 * Modal UI for browsing and applying built-in wireframe templates.
 * Depends on TemplateManager (FEAT-001) and StateManager.
 */

export default class TemplateGalleryUI {
    constructor(templateManager, state) {
        this.tm = templateManager;
        this.state = state;
        this._initElements();
        this._buildCards();
        this._bindEvents();
    }

    _initElements() {
        this.openBtn  = document.getElementById('template-gallery-btn');
        this.backdrop = document.getElementById('tg-backdrop');
        this.closeBtn = document.getElementById('tg-close-btn');
        this.grid     = document.getElementById('tg-grid');
    }

    _buildCards() {
        this.grid.innerHTML = '';
        this.tm.getAll().forEach(tpl => {
            const card = document.createElement('button');
            card.className = 'tg-card';
            card.dataset.templateId = tpl.id;
            card.setAttribute('role', 'listitem');
            card.innerHTML = `
                <span class="tg-thumb" aria-hidden="true">${tpl.thumbnail}</span>
                <span class="tg-name">${tpl.name}</span>
                <span class="tg-desc">${tpl.description}</span>
            `;
            card.addEventListener('click', () => this._applyTemplate(tpl.id));
            this.grid.appendChild(card);
        });
    }

    _bindEvents() {
        this.openBtn.addEventListener('click', () => this.open());
        this.closeBtn.addEventListener('click', () => this.close());

        // Click outside the modal box to close
        this.backdrop.addEventListener('click', (e) => {
            if (e.target === this.backdrop) this.close();
        });

        // Escape key to close
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && !this.backdrop.hidden) this.close();
        });
    }

    open() {
        this.backdrop.hidden = false;
        this.closeBtn.focus();
    }

    close() {
        this.backdrop.hidden = true;
        this.openBtn.focus();
    }

    _applyTemplate(templateId) {
        const tpl = this.tm.getById(templateId);
        const confirmMsg = `Load template "${tpl.name}"? This will replace all elements on the current page.`;
        if (!confirm(confirmMsg)) return;
        this.tm.applyToPage(templateId, this.state);
        this.close();
    }
}
