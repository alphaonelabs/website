# Wireframe Studio

A web-based low-fidelity wireframing application built with vanilla HTML, CSS, and JavaScript. Features a clean grayscale UI optimized for fast prototyping and design collaboration.

## 🚀 Features

- **Drag-and-Drop Canvas** - Intuitive component placement and movement
- **8 Component Types** - Button, Input, Text, Image, Nav Bar, Table, Modal, Frame
- **Resizable Components** - 8 resize handles for precise sizing
- **Editable Properties** - Modify text, position, width, and height
- **Grayscale UI** - Clean, professional interface optimized for fast prototyping
- **Multi-Page Support** - Create and manage multiple pages in one project
- **Zoom Controls** - Zoom in/out (50%-200%) with reset button
- **Grid Toggle** - Show/hide alignment grid (20px spacing)
- **Undo/Redo** - Full history support with keyboard shortcuts
- **Layer Ordering** - Bring to front/send to back for proper layering
- **Export** - Export to PNG or PDF format
- **Local Storage** - Projects automatically save and restore on reload
- **Modular Architecture** - Clean ES6 modules for easy maintenance

## 🎯 Usage

### Adding Components
1. Click any component button in the left sidebar
2. Component appears on canvas at position (100, 100)
3. Drag to reposition, use handles to resize

### Editing Components
1. Click to select a component
2. Use the property panel on the right to edit:
   - Text content
   - X/Y position
   - Width and height

### Keyboard Shortcuts
- `Delete` or `Backspace` - Delete selected component
- `Ctrl+Z` (or `Cmd+Z`) - Undo
- `Ctrl+Y` (or `Cmd+Shift+Z`) - Redo

### Managing Pages
- Click "+ Add Page" to create a new page
- Click page names to switch between pages
- Click "✕" to delete a page (must have at least one page)

### Exporting
- Click "📷 PNG" to export current page as PNG
- Click "📄 PDF" to export current page as PDF

## 🛠️ Development

No build process required! Just open `index.html` in a modern browser or serve it with any web server:

```bash
# Using Python
python -m http.server 8000

# Using Node.js
npx serve

# Or just open index.html directly in your browser
```

## 🏗️ Architecture

The application is built with a modular architecture using ES6 modules:

- **StateManager.js** - Manages application state with history for undo/redo
- **Canvas.js** - Handles canvas rendering and drag/resize interactions
- **UIController.js** - Manages UI updates and event bindings
- **app.js** - Main entry point that ties everything together

## 🌐 Deployment

This app is configured for GitHub Pages deployment. When pushed to the `main` branch, GitHub Actions automatically deploys the app.

No build step needed - it's pure vanilla JavaScript!

## 📦 Technology Stack

- Vanilla JavaScript (ES6 modules)
- HTML5 & CSS3
- html2canvas (via CDN) for PNG export
- jsPDF (via CDN) for PDF export
- Local Storage API for persistence

## 🎨 Design Philosophy

- **No Dependencies** - Pure vanilla JavaScript, no frameworks
- **Modular** - Clean separation of concerns with ES6 modules
- **Fast** - No build process, instant reload
- **Lightweight** - Minimal footprint, fast loading
- **Standards** - Modern web standards and best practices

## 📝 License

See LICENSE file for details.

