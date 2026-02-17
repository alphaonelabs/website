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
        this.exportJsonBtn = document.getElementById('export-json-btn');
        this.importJsonBtn = document.getElementById('import-json-btn');
        this.jsonFileInput = document.getElementById('json-file-input');
        
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
        
        // Collapse buttons
        this.leftSidebar = document.getElementById('left-sidebar');
        this.leftCollapseBtn = document.getElementById('left-collapse-btn');
        this.rightCollapseBtn = document.getElementById('right-collapse-btn');
        
        // Collapse state
        this.leftSidebarCollapsed = false;
        this.rightPanelCollapsed = false;
        
        // Drag ghost element
        this.dragGhost = null;
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
        this.exportJsonBtn.addEventListener('click', () => this.exportToJSON());
        this.importJsonBtn.addEventListener('click', () => this.importFromJSON());
        
        // Handle file input change
        this.jsonFileInput.addEventListener('change', (e) => this.handleFileSelect(e));
        
        // Pages
        this.addPageBtn.addEventListener('click', () => this.state.addPage());
        
        // Components - Enable dragging
        this.componentsGrid.querySelectorAll('.component-btn').forEach(btn => {
            // Desktop drag events
            btn.addEventListener('dragstart', (e) => {
                const target = e.target.closest('.component-btn');
                if (!target) return;
                
                const type = target.dataset.type;
                e.dataTransfer.effectAllowed = 'copy';
                e.dataTransfer.setData('componentType', type);
                target.style.opacity = '0.5';
                
                // Create a transparent drag image to hide default ghost
                const img = new Image();
                img.src = 'data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7';
                e.dataTransfer.setDragImage(img, 0, 0);
                
                // Create custom drag ghost
                this.createDragGhost(type);
            });
            
            btn.addEventListener('drag', (e) => {
                // Update ghost position during drag
                if (e.clientX !== 0 && e.clientY !== 0) {
                    this.updateDragGhost(e.clientX, e.clientY);
                }
            });
            
            btn.addEventListener('dragend', (e) => {
                const target = e.target.closest('.component-btn');
                if (target) target.style.opacity = '1';
                this.removeDragGhost();
            });

            // Touch events for mobile
            let touchStartData = null;
            let touchMoveDistance = 0;
            
            btn.addEventListener('touchstart', (e) => {
                const target = e.target.closest('.component-btn');
                if (!target) return;
                
                const type = target.dataset.type;
                const touch = e.touches[0];
                touchStartData = {
                    type,
                    startX: touch.clientX,
                    startY: touch.clientY,
                    button: target
                };
                touchMoveDistance = 0;
                touchStartData.button.style.opacity = '0.5';
            });
            
            btn.addEventListener('touchmove', (e) => {
                if (touchStartData) {
                    const touch = e.touches[0];
                    touchMoveDistance = Math.sqrt(
                        Math.pow(touch.clientX - touchStartData.startX, 2) + 
                        Math.pow(touch.clientY - touchStartData.startY, 2)
                    );
                    
                    // Only prevent default if we've moved enough to be dragging
                    if (touchMoveDistance > 5) {
                        e.preventDefault(); // Prevent scrolling while dragging
                        
                        // Create drag ghost if not already created
                        if (!this.dragGhost) {
                            this.createDragGhost(touchStartData.type);
                        }
                        
                        // Update ghost position
                        this.updateDragGhost(touch.clientX, touch.clientY);
                    }
                }
            });
            
            btn.addEventListener('touchend', (e) => {
                if (touchStartData) {
                    touchStartData.button.style.opacity = '1';
                    this.removeDragGhost();
                    
                    const touch = e.changedTouches[0];
                    const canvas = document.getElementById('canvas');
                    const rect = canvas.getBoundingClientRect();
                    
                    // Check if touch ended on canvas
                    if (touch.clientX >= rect.left && touch.clientX <= rect.right &&
                        touch.clientY >= rect.top && touch.clientY <= rect.bottom) {
                        const scrollLeft = canvas.scrollLeft;
                        const scrollTop = canvas.scrollTop;
                        const x = (touch.clientX - rect.left + scrollLeft) / this.state.zoom;
                        const y = (touch.clientY - rect.top + scrollTop) / this.state.zoom;
                        
                        this.state.addElementAtPosition(touchStartData.type, x, y);
                    }
                    
                    touchStartData = null;
                    touchMoveDistance = 0;
                }
            });
            
            btn.addEventListener('touchcancel', (e) => {
                if (touchStartData) {
                    touchStartData.button.style.opacity = '1';
                    this.removeDragGhost();
                    touchStartData = null;
                    touchMoveDistance = 0;
                }
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
        
        // Collapse buttons
        this.leftCollapseBtn.addEventListener('click', () => this.toggleLeftSidebar());
        this.rightCollapseBtn.addEventListener('click', () => this.toggleRightPanel());
        
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

    toggleLeftSidebar() {
        this.leftSidebarCollapsed = !this.leftSidebarCollapsed;
        if (this.leftSidebarCollapsed) {
            this.leftSidebar.classList.add('collapsed');
            this.leftCollapseBtn.textContent = '›';
            this.leftCollapseBtn.title = 'Expand sidebar';
        } else {
            this.leftSidebar.classList.remove('collapsed');
            this.leftCollapseBtn.textContent = '‹';
            this.leftCollapseBtn.title = 'Collapse sidebar';
        }
    }

    toggleRightPanel() {
        this.rightPanelCollapsed = !this.rightPanelCollapsed;
        if (this.rightPanelCollapsed) {
            this.propertyPanel.classList.add('collapsed');
            this.rightCollapseBtn.textContent = '‹';
            this.rightCollapseBtn.title = 'Expand panel';
        } else {
            this.propertyPanel.classList.remove('collapsed');
            this.rightCollapseBtn.textContent = '›';
            this.rightCollapseBtn.title = 'Collapse panel';
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

    createDragGhost(componentType) {
        // Remove any existing ghost
        this.removeDragGhost();
        
        // Create ghost element
        const ghost = document.createElement('div');
        ghost.className = 'drag-ghost element';
        
        // Get default dimensions for this component type
        const dimensions = this.getComponentDimensions(componentType);
        ghost.style.width = dimensions.width + 'px';
        ghost.style.height = dimensions.height + 'px';
        
        // Create content based on component type
        const content = document.createElement('div');
        content.className = `element-content ${componentType}`;
        
        // Add component-specific content
        if (componentType === 'table') {
            for (let i = 1; i <= 9; i++) {
                const cell = document.createElement('div');
                cell.className = 'table-cell';
                cell.textContent = `Cell ${i}`;
                content.appendChild(cell);
            }
        } else if (componentType === 'browser') {
            const browserBar = document.createElement('div');
            browserBar.className = 'browser-bar';
            browserBar.innerHTML = '<div class="browser-controls"><span>○</span><span>○</span><span>○</span></div><div class="browser-address">https://example.com</div>';
            content.appendChild(browserBar);
            
            const browserContent = document.createElement('div');
            browserContent.className = 'browser-content';
            browserContent.textContent = this.getComponentDefaultText(componentType);
            content.appendChild(browserContent);
        } else if (componentType === 'mobile') {
            const mobileHeader = document.createElement('div');
            mobileHeader.className = 'mobile-header';
            content.appendChild(mobileHeader);
            
            const mobileContent = document.createElement('div');
            mobileContent.className = 'mobile-content';
            mobileContent.textContent = this.getComponentDefaultText(componentType);
            content.appendChild(mobileContent);
            
            const mobileFooter = document.createElement('div');
            mobileFooter.className = 'mobile-footer';
            content.appendChild(mobileFooter);
        } else {
            content.textContent = this.getComponentDefaultText(componentType);
        }
        
        ghost.appendChild(content);
        document.body.appendChild(ghost);
        
        this.dragGhost = ghost;
        return ghost;
    }

    updateDragGhost(x, y) {
        if (this.dragGhost) {
            this.dragGhost.style.left = x + 'px';
            this.dragGhost.style.top = y + 'px';
        }
    }

    removeDragGhost() {
        if (this.dragGhost) {
            this.dragGhost.remove();
            this.dragGhost = null;
        }
    }

    getComponentDimensions(type) {
        const dimensions = {
            button: { width: 120, height: 40 },
            input: { width: 200, height: 40 },
            text: { width: 150, height: 30 },
            image: { width: 200, height: 150 },
            navbar: { width: 400, height: 60 },
            table: { width: 300, height: 200 },
            modal: { width: 400, height: 300 },
            frame: { width: 300, height: 250 },
            browser: { width: 600, height: 400 },
            mobile: { width: 280, height: 520 }
        };
        return dimensions[type] || { width: 150, height: 100 };
    }

    getComponentDefaultText(type) {
        const texts = {
            button: 'Button',
            input: 'Input field',
            text: 'Text content',
            image: '',
            navbar: 'Navigation',
            table: '',
            modal: 'Modal Content',
            frame: 'Frame',
            browser: 'Browser Content',
            mobile: 'Mobile App'
        };
        return texts[type] || type;
    }

    exportToJSON() {
        try {
            const jsonData = this.state.exportToJSON();
            const blob = new Blob([jsonData], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = `wireframe-project-${new Date().toISOString().split('T')[0]}.json`;
            link.click();
            URL.revokeObjectURL(url);
        } catch (error) {
            console.error('Export to JSON failed:', error);
            alert('Export failed. Please try again.');
        }
    }

    importFromJSON() {
        // Trigger the file input
        this.jsonFileInput.click();
    }

    handleFileSelect(e) {
        const file = e.target.files[0];
        if (!file) return;

        const reader = new FileReader();
        reader.onload = (event) => {
            const jsonString = event.target.result;
            const success = this.state.importFromJSON(jsonString);
            
            if (success) {
                alert('Project imported successfully!');
            } else {
                alert('Failed to import project. Please check the file format.');
            }
            
            // Clear the file input so the same file can be selected again
            this.jsonFileInput.value = '';
        };
        
        reader.onerror = () => {
            alert('Failed to read file. Please try again.');
            this.jsonFileInput.value = '';
        };
        
        reader.readAsText(file);
    }
}

export default UIController;
