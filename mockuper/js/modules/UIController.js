/**
 * UI Controller Module
 * Handles UI updates and event bindings
 */

class UIController {
    constructor(state) {
        this.state = state;
        this.initElements();
        this.bindEvents();
    }

    initElements() {
        // Toolbar buttons
        this.undoBtn = document.getElementById('undo-btn');
        this.redoBtn = document.getElementById('redo-btn');
        this.gridToggleBtn = document.getElementById('grid-toggle-btn');
        this.bringFrontBtn = document.getElementById('bring-front-btn');
        this.sendBackBtn = document.getElementById('send-back-btn');
        this.deleteBtn = document.getElementById('delete-btn');
        this.exportPngBtn = document.getElementById('export-png-btn');
        this.exportPdfBtn = document.getElementById('export-pdf-btn');
        
        // Page controls
        this.pagesList = document.getElementById('pages-list');
        this.addPageBtn = document.getElementById('add-page-btn');
        
        // Component buttons
        this.componentsGrid = document.getElementById('components-grid');
        
        // Zoom controls
        this.zoomInBtn = document.getElementById('zoom-in-btn');
        this.zoomOutBtn = document.getElementById('zoom-out-btn');
        this.zoomResetBtn = document.getElementById('zoom-reset-btn');
        this.zoomLevel = document.getElementById('zoom-level');
        
        // Grid
        this.grid = document.getElementById('grid');
        
        // Property panel
        this.propertyPanel = document.getElementById('property-panel');
        this.propText = document.getElementById('prop-text');
        this.propX = document.getElementById('prop-x');
        this.propY = document.getElementById('prop-y');
        this.propWidth = document.getElementById('prop-width');
        this.propHeight = document.getElementById('prop-height');
    }

    bindEvents() {
        // Toolbar
        this.undoBtn.addEventListener('click', () => this.state.undo());
        this.redoBtn.addEventListener('click', () => this.state.redo());
        this.gridToggleBtn.addEventListener('click', () => this.state.toggleGrid());
        this.bringFrontBtn.addEventListener('click', () => {
            if (this.state.selectedElementId) {
                this.state.bringToFront(this.state.selectedElementId);
            }
        });
        this.sendBackBtn.addEventListener('click', () => {
            if (this.state.selectedElementId) {
                this.state.sendToBack(this.state.selectedElementId);
            }
        });
        this.deleteBtn.addEventListener('click', () => {
            if (this.state.selectedElementId) {
                this.state.deleteElement(this.state.selectedElementId);
            }
        });
        
        // Export buttons
        this.exportPngBtn.addEventListener('click', () => this.exportToPNG());
        this.exportPdfBtn.addEventListener('click', () => this.exportToPDF());
        
        // Pages
        this.addPageBtn.addEventListener('click', () => this.state.addPage());
        
        // Components - Enable dragging
        this.componentsGrid.querySelectorAll('.component-btn').forEach(btn => {
            btn.addEventListener('dragstart', (e) => {
                const type = e.target.dataset.type;
                e.dataTransfer.effectAllowed = 'copy';
                e.dataTransfer.setData('componentType', type);
                e.target.style.opacity = '0.5';
            });
            
            btn.addEventListener('dragend', (e) => {
                e.target.style.opacity = '1';
            });
        });
        
        // Components - Click to add (fallback)
        this.componentsGrid.addEventListener('click', (e) => {
            if (e.target.classList.contains('component-btn')) {
                const type = e.target.dataset.type;
                this.state.addElement(type);
            }
        });
        
        // Zoom
        this.zoomInBtn.addEventListener('click', () => this.state.zoomIn());
        this.zoomOutBtn.addEventListener('click', () => this.state.zoomOut());
        this.zoomResetBtn.addEventListener('click', () => this.state.resetZoom());
        
        // Properties
        this.propText.addEventListener('input', (e) => {
            if (this.state.selectedElementId) {
                this.state.updateElement(this.state.selectedElementId, { text: e.target.value });
            }
        });
        this.propText.addEventListener('blur', () => this.state.saveHistory());
        
        this.propX.addEventListener('change', (e) => {
            if (this.state.selectedElementId) {
                this.state.updateElement(this.state.selectedElementId, { x: parseFloat(e.target.value) || 0 });
                this.state.saveHistory();
            }
        });
        
        this.propY.addEventListener('change', (e) => {
            if (this.state.selectedElementId) {
                this.state.updateElement(this.state.selectedElementId, { y: parseFloat(e.target.value) || 0 });
                this.state.saveHistory();
            }
        });
        
        this.propWidth.addEventListener('change', (e) => {
            if (this.state.selectedElementId) {
                this.state.updateElement(this.state.selectedElementId, { width: parseFloat(e.target.value) || 20 });
                this.state.saveHistory();
            }
        });
        
        this.propHeight.addEventListener('change', (e) => {
            if (this.state.selectedElementId) {
                this.state.updateElement(this.state.selectedElementId, { height: parseFloat(e.target.value) || 20 });
                this.state.saveHistory();
            }
        });
        
        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            // Delete/Backspace
            if ((e.key === 'Delete' || e.key === 'Backspace') && 
                e.target.tagName !== 'INPUT' && e.target.tagName !== 'TEXTAREA') {
                if (this.state.selectedElementId) {
                    this.state.deleteElement(this.state.selectedElementId);
                }
            }
            
            // Undo/Redo
            if ((e.ctrlKey || e.metaKey) && e.key === 'z' && !e.shiftKey) {
                e.preventDefault();
                this.state.undo();
            }
            if ((e.ctrlKey || e.metaKey) && (e.key === 'y' || (e.shiftKey && e.key === 'z'))) {
                e.preventDefault();
                this.state.redo();
            }
        });
    }

    update() {
        this.updateToolbar();
        this.updatePages();
        this.updateZoom();
        this.updateGrid();
        this.updateProperties();
    }

    updateToolbar() {
        this.undoBtn.disabled = !this.state.canUndo();
        this.redoBtn.disabled = !this.state.canRedo();
        
        const hasSelection = !!this.state.selectedElementId;
        this.bringFrontBtn.disabled = !hasSelection;
        this.sendBackBtn.disabled = !hasSelection;
        this.deleteBtn.disabled = !hasSelection;
    }

    updatePages() {
        this.pagesList.innerHTML = '';
        
        this.state.pages.forEach(page => {
            const pageItem = document.createElement('div');
            pageItem.className = 'page-item';
            if (page.id === this.state.currentPageId) {
                pageItem.classList.add('active');
            }
            
            const pageName = document.createElement('span');
            pageName.className = 'page-name';
            pageName.textContent = page.name;
            pageItem.appendChild(pageName);
            
            if (this.state.pages.length > 1) {
                const deleteBtn = document.createElement('button');
                deleteBtn.className = 'page-delete';
                deleteBtn.textContent = '✕';
                deleteBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    this.state.deletePage(page.id);
                });
                pageItem.appendChild(deleteBtn);
            }
            
            pageItem.addEventListener('click', () => this.state.switchPage(page.id));
            this.pagesList.appendChild(pageItem);
        });
    }

    updateZoom() {
        this.zoomLevel.textContent = Math.round(this.state.zoom * 100) + '%';
    }

    updateGrid() {
        if (this.state.showGrid) {
            this.grid.classList.remove('hidden');
            this.gridToggleBtn.textContent = '◫ Hide Grid';
        } else {
            this.grid.classList.add('hidden');
            this.gridToggleBtn.textContent = '◫ Show Grid';
        }
    }

    updateProperties() {
        const element = this.state.getSelectedElement();
        
        if (element) {
            this.propertyPanel.style.display = 'block';
            this.propText.value = element.text;
            this.propX.value = Math.round(element.x);
            this.propY.value = Math.round(element.y);
            this.propWidth.value = Math.round(element.width);
            this.propHeight.value = Math.round(element.height);
        } else {
            this.propertyPanel.style.display = 'none';
        }
    }

    async exportToPNG() {
        const html2canvas = (await import('https://cdn.jsdelivr.net/npm/html2canvas@1.4.1/+esm')).default;
        const content = document.getElementById('canvas-content');
        
        try {
            const canvas = await html2canvas(content, {
                backgroundColor: '#ffffff',
                scale: 2
            });
            
            const link = document.createElement('a');
            link.download = `${this.state.getCurrentPage().name}.png`;
            link.href = canvas.toDataURL();
            link.click();
        } catch (error) {
            console.error('Export to PNG failed:', error);
            alert('Export failed. Please try again.');
        }
    }

    async exportToPDF() {
        const html2canvas = (await import('https://cdn.jsdelivr.net/npm/html2canvas@1.4.1/+esm')).default;
        const { jsPDF } = await import('https://cdn.jsdelivr.net/npm/jspdf@2.5.2/+esm');
        const content = document.getElementById('canvas-content');
        
        try {
            const canvas = await html2canvas(content, {
                backgroundColor: '#ffffff',
                scale: 2
            });
            
            const imgData = canvas.toDataURL('image/png');
            const pdf = new jsPDF({
                orientation: canvas.width > canvas.height ? 'landscape' : 'portrait',
                unit: 'px',
                format: [canvas.width, canvas.height]
            });
            
            pdf.addImage(imgData, 'PNG', 0, 0, canvas.width, canvas.height);
            pdf.save(`${this.state.getCurrentPage().name}.pdf`);
        } catch (error) {
            console.error('Export to PDF failed:', error);
            alert('Export failed. Please try again.');
        }
    }
}

export default UIController;
