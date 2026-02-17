/**
 * Canvas Module
 * Handles canvas rendering and interactions
 */

class Canvas {
    constructor(state, canvasElement, canvasContent) {
        this.state = state;
        this.canvas = canvasElement;
        this.content = canvasContent;
        
        this.isDragging = false;
        this.isResizing = false;
        this.dragStart = null;
        this.resizeStart = null;
        this.resizeHandle = null;
        
        this.init();
    }

    init() {
        // Canvas click to deselect
        this.canvas.addEventListener('click', (e) => {
            if (e.target === this.canvas || e.target === this.content) {
                this.state.deselectElement();
            }
        });

        // Drag and drop handlers for components
        const dropHandler = (e) => {
            e.preventDefault();
            const componentType = e.dataTransfer.getData('componentType');
            if (componentType) {
                // Calculate position relative to canvas and zoom
                const rect = this.canvas.getBoundingClientRect();
                const scrollLeft = this.canvas.scrollLeft;
                const scrollTop = this.canvas.scrollTop;
                const x = (e.clientX - rect.left + scrollLeft) / this.state.zoom;
                const y = (e.clientY - rect.top + scrollTop) / this.state.zoom;
                
                this.state.addElementAtPosition(componentType, x, y);
            }
        };
        
        const dragOverHandler = (e) => {
            e.preventDefault();
            e.dataTransfer.dropEffect = 'copy';
        };
        
        this.canvas.addEventListener('dragover', dragOverHandler);
        this.canvas.addEventListener('drop', dropHandler);
        this.content.addEventListener('dragover', dragOverHandler);
        this.content.addEventListener('drop', dropHandler);

        // Context menu for z-index management
        this.content.addEventListener('contextmenu', (e) => {
            const element = e.target.closest('.element');
            if (element) {
                e.preventDefault();
                const elementId = element.dataset.id;
                this.showContextMenu(e.clientX, e.clientY, elementId);
            }
        });

        // Global mouse handlers
        document.addEventListener('mousemove', this.handleMouseMove.bind(this));
        document.addEventListener('mouseup', this.handleMouseUp.bind(this));
    }

    render() {
        const page = this.state.getCurrentPage();
        if (!page) return;

        // Clear existing elements
        const elements = this.content.querySelectorAll('.element');
        elements.forEach(el => el.remove());

        // Apply zoom
        this.content.style.transform = `scale(${this.state.zoom})`;

        // Render elements sorted by z-index
        const sortedElements = [...page.elements].sort((a, b) => a.zIndex - b.zIndex);
        sortedElements.forEach(element => {
            this.renderElement(element);
        });
    }

    renderElement(element) {
        const el = document.createElement('div');
        el.className = 'element';
        el.dataset.id = element.id;
        
        if (element.id === this.state.selectedElementId) {
            el.classList.add('selected');
        }

        el.style.left = element.x + 'px';
        el.style.top = element.y + 'px';
        el.style.width = element.width + 'px';
        el.style.height = element.height + 'px';
        el.style.zIndex = element.zIndex;

        const content = document.createElement('div');
        content.className = `element-content ${element.type}`;

        if (element.type === 'table') {
            for (let i = 1; i <= 9; i++) {
                const cell = document.createElement('div');
                cell.className = 'table-cell';
                cell.textContent = `Cell ${i}`;
                content.appendChild(cell);
            }
        } else {
            content.textContent = element.text;
        }

        el.appendChild(content);

        // Add resize handles if selected
        if (element.id === this.state.selectedElementId) {
            this.addResizeHandles(el);
        }

        // Drag handler
        el.addEventListener('mousedown', (e) => this.handleElementMouseDown(e, element.id));

        this.content.appendChild(el);
    }

    addResizeHandles(el) {
        const handles = ['nw', 'ne', 'sw', 'se', 'n', 's', 'w', 'e'];
        handles.forEach(handle => {
            const div = document.createElement('div');
            div.className = `resize-handle ${handle}`;
            div.addEventListener('mousedown', (e) => this.handleResizeMouseDown(e, handle));
            el.appendChild(div);
        });
    }

    handleElementMouseDown(e, elementId) {
        if (e.button !== 0) return;
        e.stopPropagation();
        
        this.state.selectElement(elementId);
        this.isDragging = true;
        
        const element = this.state.getCurrentPage().elements.find(el => el.id === elementId);
        this.dragStart = {
            x: e.clientX - element.x * this.state.zoom,
            y: e.clientY - element.y * this.state.zoom
        };
    }

    handleResizeMouseDown(e, handle) {
        e.stopPropagation();
        
        this.isResizing = true;
        this.resizeHandle = handle;
        
        const element = this.state.getSelectedElement();
        this.resizeStart = {
            x: e.clientX,
            y: e.clientY,
            elementX: element.x,
            elementY: element.y,
            elementWidth: element.width,
            elementHeight: element.height
        };
    }

    handleMouseMove(e) {
        if (this.isDragging && this.state.selectedElementId && this.dragStart) {
            const newX = (e.clientX - this.dragStart.x) / this.state.zoom;
            const newY = (e.clientY - this.dragStart.y) / this.state.zoom;
            this.state.updateElement(this.state.selectedElementId, { x: newX, y: newY });
            
        } else if (this.isResizing && this.state.selectedElementId && this.resizeStart) {
            const dx = e.clientX - this.resizeStart.x;
            const dy = e.clientY - this.resizeStart.y;
            
            const updates = {};
            
            if (this.resizeHandle.includes('e')) {
                updates.width = Math.max(20, this.resizeStart.elementWidth + dx / this.state.zoom);
            }
            if (this.resizeHandle.includes('w')) {
                const newWidth = Math.max(20, this.resizeStart.elementWidth - dx / this.state.zoom);
                updates.width = newWidth;
                updates.x = this.resizeStart.elementX + (this.resizeStart.elementWidth - newWidth);
            }
            if (this.resizeHandle.includes('s')) {
                updates.height = Math.max(20, this.resizeStart.elementHeight + dy / this.state.zoom);
            }
            if (this.resizeHandle.includes('n')) {
                const newHeight = Math.max(20, this.resizeStart.elementHeight - dy / this.state.zoom);
                updates.height = newHeight;
                updates.y = this.resizeStart.elementY + (this.resizeStart.elementHeight - newHeight);
            }
            
            this.state.updateElement(this.state.selectedElementId, updates);
        }

        // Update cursor
        if (this.isDragging) {
            this.canvas.classList.add('grabbing');
        }
    }

    handleMouseUp() {
        if (this.isDragging || this.isResizing) {
            this.state.saveHistory();
            this.isDragging = false;
            this.isResizing = false;
            this.dragStart = null;
            this.resizeStart = null;
            this.resizeHandle = null;
            this.canvas.classList.remove('grabbing');
        }
    }

    showContextMenu(x, y, elementId) {
        // Remove existing context menu
        const existingMenu = document.querySelector('.context-menu');
        if (existingMenu) {
            existingMenu.remove();
        }

        // Create context menu
        const menu = document.createElement('div');
        menu.className = 'context-menu';
        menu.style.left = x + 'px';
        menu.style.top = y + 'px';

        const menuItems = [
            { label: 'Bring Forward', action: () => this.state.bringForward(elementId) },
            { label: 'Send Backward', action: () => this.state.sendBackward(elementId) },
            { label: 'Bring to Front', action: () => this.state.bringToFront(elementId) },
            { label: 'Send to Back', action: () => this.state.sendToBack(elementId) },
        ];

        menuItems.forEach(item => {
            const menuItem = document.createElement('div');
            menuItem.className = 'context-menu-item';
            menuItem.textContent = item.label;
            menuItem.addEventListener('click', () => {
                item.action();
                menu.remove();
            });
            menu.appendChild(menuItem);
        });

        document.body.appendChild(menu);

        // Close menu on click outside
        const closeMenu = (e) => {
            if (!menu.contains(e.target)) {
                menu.remove();
                document.removeEventListener('click', closeMenu);
            }
        };
        
        // Also remove listener when menu is removed by other means
        const observer = new MutationObserver((mutations) => {
            if (!document.body.contains(menu)) {
                document.removeEventListener('click', closeMenu);
                observer.disconnect();
            }
        });
        observer.observe(document.body, { childList: true });
        
        setTimeout(() => document.addEventListener('click', closeMenu), 0);
    }
}

export default Canvas;
