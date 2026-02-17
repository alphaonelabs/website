/**
 * State Manager Module
 * Manages application state with history for undo/redo
 */

class StateManager {
    constructor() {
        this.pages = [];
        this.currentPageId = null;
        this.selectedElementId = null;
        this.history = [];
        this.historyIndex = -1;
        this.zoom = 1;
        this.showGrid = true;
        this.nextElementId = 1;
        this.listeners = [];
        
        this.loadFromStorage();
    }

    // Save state to localStorage
    saveToStorage() {
        const state = {
            pages: this.pages,
            currentPageId: this.currentPageId,
            nextElementId: this.nextElementId
        };
        localStorage.setItem('wireframe-project', JSON.stringify(state));
    }

    // Load state from localStorage
    loadFromStorage() {
        const saved = localStorage.getItem('wireframe-project');
        if (saved) {
            try {
                const state = JSON.parse(saved);
                this.pages = state.pages || [];
                this.currentPageId = state.currentPageId;
                this.nextElementId = state.nextElementId || 1;
            } catch (e) {
                console.error('Failed to load project:', e);
            }
        }
        
        // Initialize with one page if empty
        if (this.pages.length === 0) {
            this.pages = [{
                id: '1',
                name: 'Page 1',
                elements: []
            }];
            this.currentPageId = '1';
        }
    }

    // Add state change listener
    onChange(callback) {
        this.listeners.push(callback);
    }

    // Notify all listeners
    notify() {
        this.saveToStorage();
        this.listeners.forEach(callback => callback());
    }

    // Get current page
    getCurrentPage() {
        return this.pages.find(p => p.id === this.currentPageId);
    }

    // Get selected element
    getSelectedElement() {
        const page = this.getCurrentPage();
        return page ? page.elements.find(el => el.id === this.selectedElementId) : null;
    }

    // Add element
    addElement(type) {
        const page = this.getCurrentPage();
        if (!page) return;

        const componentTypes = {
            button: { width: 120, height: 40, label: 'Button' },
            input: { width: 200, height: 40, label: 'Input' },
            text: { width: 150, height: 30, label: 'Text' },
            image: { width: 200, height: 150, label: 'Image' },
            navbar: { width: 800, height: 60, label: 'Nav Bar' },
            table: { width: 400, height: 200, label: 'Table' },
            modal: { width: 400, height: 300, label: 'Modal' },
            frame: { width: 300, height: 400, label: 'Frame' },
            browser: { width: 800, height: 600, label: 'Browser Window' },
            mobile: { width: 375, height: 667, label: 'Mobile App' }
        };

        const config = componentTypes[type];
        const newElement = {
            id: String(this.nextElementId++),
            type,
            x: 100,
            y: 100,
            width: config.width,
            height: config.height,
            text: config.label,
            zIndex: page.elements.length
        };

        page.elements.push(newElement);
        this.selectedElementId = newElement.id;
        this.saveHistory();
        this.notify();
    }

    // Add element at specific position (for drag-and-drop)
    addElementAtPosition(type, x, y) {
        const page = this.getCurrentPage();
        if (!page) return;

        const componentTypes = {
            button: { width: 120, height: 40, label: 'Button' },
            input: { width: 200, height: 40, label: 'Input' },
            text: { width: 150, height: 30, label: 'Text' },
            image: { width: 200, height: 150, label: 'Image' },
            navbar: { width: 800, height: 60, label: 'Nav Bar' },
            table: { width: 400, height: 200, label: 'Table' },
            modal: { width: 400, height: 300, label: 'Modal' },
            frame: { width: 300, height: 400, label: 'Frame' },
            browser: { width: 800, height: 600, label: 'Browser Window' },
            mobile: { width: 375, height: 667, label: 'Mobile App' }
        };

        const config = componentTypes[type];
        const newElement = {
            id: String(this.nextElementId++),
            type,
            x: Math.max(0, x - config.width / 2), // Center on drop position
            y: Math.max(0, y - config.height / 2),
            width: config.width,
            height: config.height,
            text: config.label,
            zIndex: page.elements.length
        };

        page.elements.push(newElement);
        this.selectedElementId = newElement.id;
        this.saveHistory();
        this.notify();
    }

    // Update element
    updateElement(id, updates) {
        const page = this.getCurrentPage();
        if (!page) return;

        const element = page.elements.find(el => el.id === id);
        if (element) {
            Object.assign(element, updates);
            this.notify();
        }
    }

    // Delete element
    deleteElement(id) {
        const page = this.getCurrentPage();
        if (!page) return;

        page.elements = page.elements.filter(el => el.id !== id);
        if (this.selectedElementId === id) {
            this.selectedElementId = null;
        }
        this.saveHistory();
        this.notify();
    }

    // Select element
    selectElement(id) {
        this.selectedElementId = id;
        this.notify();
    }

    // Deselect element
    deselectElement() {
        this.selectedElementId = null;
        this.notify();
    }

    // Layer ordering
    bringToFront(id) {
        const page = this.getCurrentPage();
        if (!page) return;

        const element = page.elements.find(el => el.id === id);
        if (element) {
            const maxZ = Math.max(...page.elements.map(el => el.zIndex), 0);
            element.zIndex = maxZ + 1;
            this.saveHistory();
            this.notify();
        }
    }

    sendToBack(id) {
        const page = this.getCurrentPage();
        if (!page) return;

        const element = page.elements.find(el => el.id === id);
        if (element) {
            // Set to 0 to ensure it doesn't go behind the grid
            element.zIndex = 0;
            // Adjust other elements that were at 0 or below
            page.elements.forEach(el => {
                if (el.id !== id && el.zIndex <= 0) {
                    el.zIndex++;
                }
            });
            this.saveHistory();
            this.notify();
        }
    }

    bringForward(id) {
        const page = this.getCurrentPage();
        if (!page) return;

        const element = page.elements.find(el => el.id === id);
        if (element) {
            // Find the next higher z-index
            const higherElements = page.elements.filter(el => el.zIndex > element.zIndex);
            if (higherElements.length > 0) {
                const nextZ = Math.min(...higherElements.map(el => el.zIndex));
                element.zIndex = nextZ + 0.5;
                this.normalizeZIndices();
            }
            this.saveHistory();
            this.notify();
        }
    }

    sendBackward(id) {
        const page = this.getCurrentPage();
        if (!page) return;

        const element = page.elements.find(el => el.id === id);
        if (element) {
            // Find the next lower z-index
            const lowerElements = page.elements.filter(el => el.zIndex < element.zIndex);
            if (lowerElements.length > 0) {
                const prevZ = Math.max(...lowerElements.map(el => el.zIndex));
                element.zIndex = prevZ - 0.5;
                this.normalizeZIndices();
            }
            this.saveHistory();
            this.notify();
        }
    }

    // Normalize z-indices to clean integer values
    normalizeZIndices() {
        const page = this.getCurrentPage();
        if (!page) return;

        // Sort elements by z-index and reassign clean integer values
        const sortedElements = [...page.elements].sort((a, b) => a.zIndex - b.zIndex);
        sortedElements.forEach((element, index) => {
            element.zIndex = index;
        });
    }

    // Page management
    addPage() {
        const newPage = {
            id: String(Date.now()),
            name: `Page ${this.pages.length + 1}`,
            elements: []
        };
        this.pages.push(newPage);
        this.currentPageId = newPage.id;
        this.selectedElementId = null;
        this.saveHistory();
        this.notify();
    }

    deletePage(id) {
        if (this.pages.length === 1) return;
        
        this.pages = this.pages.filter(p => p.id !== id);
        if (this.currentPageId === id) {
            this.currentPageId = this.pages[0].id;
        }
        this.selectedElementId = null;
        this.saveHistory();
        this.notify();
    }

    switchPage(id) {
        this.currentPageId = id;
        this.selectedElementId = null;
        this.notify();
    }

    // History management
    saveHistory() {
        const snapshot = {
            pages: JSON.parse(JSON.stringify(this.pages)),
            currentPageId: this.currentPageId
        };
        
        this.history = this.history.slice(0, this.historyIndex + 1);
        this.history.push(snapshot);
        this.historyIndex = this.history.length - 1;
    }

    undo() {
        if (this.historyIndex > 0) {
            this.historyIndex--;
            const snapshot = this.history[this.historyIndex];
            this.pages = JSON.parse(JSON.stringify(snapshot.pages));
            this.currentPageId = snapshot.currentPageId;
            this.selectedElementId = null;
            this.notify();
        }
    }

    redo() {
        if (this.historyIndex < this.history.length - 1) {
            this.historyIndex++;
            const snapshot = this.history[this.historyIndex];
            this.pages = JSON.parse(JSON.stringify(snapshot.pages));
            this.currentPageId = snapshot.currentPageId;
            this.selectedElementId = null;
            this.notify();
        }
    }

    canUndo() {
        return this.historyIndex > 0;
    }

    canRedo() {
        return this.historyIndex < this.history.length - 1;
    }

    // Zoom controls
    setZoom(zoom) {
        this.zoom = Math.max(0.5, Math.min(2, zoom));
        this.notify();
    }

    zoomIn() {
        this.setZoom(this.zoom + 0.1);
    }

    zoomOut() {
        this.setZoom(this.zoom - 0.1);
    }

    resetZoom() {
        this.setZoom(1);
    }

    // Grid toggle
    toggleGrid() {
        this.showGrid = !this.showGrid;
        this.notify();
    }
}

export default StateManager;
