# Wireframe Studio

A web-based low-fidelity wireframing application with a hand-drawn sketch style and grayscale UI. Built for fast prototyping and design collaboration.

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

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

## 🌐 Deployment

This app is configured for GitHub Pages deployment. When pushed to the `main` branch, GitHub Actions automatically builds and deploys the app.

## 📦 Technology Stack

- React 19 with hooks
- Vite for fast development
- html2canvas for PNG export
- jsPDF for PDF export
- Local storage for persistence

## 📝 License

See LICENSE file for details.

