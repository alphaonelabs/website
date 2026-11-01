/**
 * Main Application Entry Point
 * Wireframe Studio - Vanilla JavaScript Implementation
 */

import StateManager from './modules/StateManager.js';
import Canvas from './modules/Canvas.js';
import UIController from './modules/UIController.js';
import VersionManager from './modules/VersionManager.js';

class WireframeApp {
    constructor() {
        this.state = new StateManager();
        this.canvas = new Canvas(
            this.state,
            document.getElementById('canvas'),
            document.getElementById('canvas-content')
        );
        this.ui = new UIController(this.state);
        this.versionManager = new VersionManager();
        
        this.init();
    }

    init() {
        // Listen to state changes and update UI
        this.state.onChange(() => {
            this.canvas.render();
            this.ui.update();
        });

        // Initial render
        this.canvas.render();
        this.ui.update();
        
        // Fetch and display version
        this.versionManager.displayVersion();
        
        console.log('Wireframe Studio initialized');
    }
}

// Initialize the app when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => new WireframeApp());
} else {
    new WireframeApp();
}
