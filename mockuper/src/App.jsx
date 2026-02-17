import { useState, useRef, useCallback, useEffect } from 'react';
import html2canvas from 'html2canvas';
import jsPDF from 'jspdf';
import './App.css';

const COMPONENT_TYPES = [
  { type: 'button', label: 'Button', defaultWidth: 120, defaultHeight: 40 },
  { type: 'input', label: 'Input', defaultWidth: 200, defaultHeight: 40 },
  { type: 'text', label: 'Text', defaultWidth: 150, defaultHeight: 30 },
  { type: 'image', label: 'Image', defaultWidth: 200, defaultHeight: 150 },
  { type: 'navbar', label: 'Nav Bar', defaultWidth: 800, defaultHeight: 60 },
  { type: 'table', label: 'Table', defaultWidth: 400, defaultHeight: 200 },
  { type: 'modal', label: 'Modal', defaultWidth: 400, defaultHeight: 300 },
  { type: 'frame', label: 'Frame', defaultWidth: 300, defaultHeight: 400 },
];

function App() {
  const [pages, setPages] = useState([{ id: '1', name: 'Page 1', elements: [] }]);
  const [currentPageId, setCurrentPageId] = useState('1');
  const [selectedId, setSelectedId] = useState(null);
  const [zoom, setZoom] = useState(1);
  const [showGrid, setShowGrid] = useState(true);
  const [history, setHistory] = useState([]);
  const [historyIndex, setHistoryIndex] = useState(-1);
  const [isDragging, setIsDragging] = useState(false);
  const [isResizing, setIsResizing] = useState(false);
  const [dragStart, setDragStart] = useState(null);
  const [resizeStart, setResizeStart] = useState(null);
  const [resizeHandle, setResizeHandle] = useState(null);
  
  const canvasRef = useRef(null);
  const nextIdRef = useRef(1);

  const currentPage = pages.find(p => p.id === currentPageId);
  const selectedElement = currentPage?.elements.find(el => el.id === selectedId);

  // Save state to localStorage
  useEffect(() => {
    localStorage.setItem('wireframe-project', JSON.stringify({ pages, currentPageId }));
  }, [pages, currentPageId]);

  // Load state from localStorage (only on mount)
  useEffect(() => {
    const saved = localStorage.getItem('wireframe-project');
    if (saved) {
      try {
        const { pages: savedPages, currentPageId: savedPageId } = JSON.parse(saved);
        if (savedPages && savedPages.length > 0) {
          setPages(savedPages);
          setCurrentPageId(savedPageId || savedPages[0].id);
          // Update nextIdRef to avoid ID conflicts
          const maxId = savedPages.reduce((max, page) => {
            const pageMax = page.elements.reduce((m, el) => Math.max(m, parseInt(el.id) || 0), 0);
            return Math.max(max, pageMax);
          }, 0);
          nextIdRef.current = maxId + 1;
        }
      } catch (e) {
        console.error('Failed to load saved project:', e);
      }
    }
  }, []); // Only run on mount

  // Save to history for undo/redo
  const saveHistory = useCallback(() => {
    const newHistory = history.slice(0, historyIndex + 1);
    newHistory.push({ pages: JSON.parse(JSON.stringify(pages)), currentPageId });
    setHistory(newHistory);
    setHistoryIndex(newHistory.length - 1);
  }, [history, historyIndex, pages, currentPageId]);

  // Add element
  const addElement = useCallback((type) => {
    const componentType = COMPONENT_TYPES.find(c => c.type === type);
    setPages(prevPages => {
      const currentPg = prevPages.find(p => p.id === currentPageId);
      const newElement = {
        id: String(nextIdRef.current++),
        type,
        x: 100,
        y: 100,
        width: componentType.defaultWidth,
        height: componentType.defaultHeight,
        text: componentType.label,
        zIndex: currentPg.elements.length,
      };
      
      const updatedPages = prevPages.map(p => 
        p.id === currentPageId 
          ? { ...p, elements: [...p.elements, newElement] }
          : p
      );
      
      setSelectedId(newElement.id);
      return updatedPages;
    });
    saveHistory();
  }, [currentPageId, saveHistory]);

  // Update element
  const updateElement = useCallback((id, updates) => {
    setPages(prevPages => prevPages.map(p => 
      p.id === currentPageId 
        ? { ...p, elements: p.elements.map(el => el.id === id ? { ...el, ...updates } : el) }
        : p
    ));
  }, [currentPageId]);

  // Delete element
  const deleteElement = useCallback(() => {
    if (!selectedId) return;
    setPages(prevPages => prevPages.map(p => 
      p.id === currentPageId 
        ? { ...p, elements: p.elements.filter(el => el.id !== selectedId) }
        : p
    ));
    setSelectedId(null);
    saveHistory();
  }, [currentPageId, selectedId, saveHistory]);

  // Layer ordering
  const bringToFront = useCallback(() => {
    if (!selectedId) return;
    const maxZ = Math.max(...currentPage.elements.map(el => el.zIndex), 0);
    updateElement(selectedId, { zIndex: maxZ + 1 });
    saveHistory();
  }, [currentPage, selectedId, updateElement, saveHistory]);

  const sendToBack = useCallback(() => {
    if (!selectedId) return;
    const minZ = Math.min(...currentPage.elements.map(el => el.zIndex), 0);
    updateElement(selectedId, { zIndex: minZ - 1 });
    saveHistory();
  }, [currentPage, selectedId, updateElement, saveHistory]);

  // Undo/Redo
  const undo = useCallback(() => {
    if (historyIndex > 0) {
      const prevState = history[historyIndex - 1];
      setPages(prevState.pages);
      setCurrentPageId(prevState.currentPageId);
      setHistoryIndex(historyIndex - 1);
    }
  }, [history, historyIndex]);

  const redo = useCallback(() => {
    if (historyIndex < history.length - 1) {
      const nextState = history[historyIndex + 1];
      setPages(nextState.pages);
      setCurrentPageId(nextState.currentPageId);
      setHistoryIndex(historyIndex + 1);
    }
  }, [history, historyIndex]);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Delete' || e.key === 'Backspace') {
        if (e.target.tagName !== 'INPUT' && e.target.tagName !== 'TEXTAREA') {
          deleteElement();
        }
      }
      if ((e.ctrlKey || e.metaKey) && e.key === 'z' && !e.shiftKey) {
        e.preventDefault();
        undo();
      }
      if ((e.ctrlKey || e.metaKey) && (e.key === 'y' || (e.shiftKey && e.key === 'z'))) {
        e.preventDefault();
        redo();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [deleteElement, undo, redo]);

  // Mouse handlers for dragging
  const handleMouseDown = useCallback((e, elementId) => {
    if (e.button !== 0) return;
    e.stopPropagation();
    setSelectedId(elementId);
    setIsDragging(true);
    const element = currentPage.elements.find(el => el.id === elementId);
    setDragStart({
      x: e.clientX - element.x * zoom,
      y: e.clientY - element.y * zoom,
    });
  }, [currentPage, zoom]);

  const handleResizeMouseDown = useCallback((e, elementId, handle) => {
    e.stopPropagation();
    setIsResizing(true);
    setResizeHandle(handle);
    setSelectedId(elementId);
    const element = currentPage.elements.find(el => el.id === elementId);
    setResizeStart({
      x: e.clientX,
      y: e.clientY,
      elementX: element.x,
      elementY: element.y,
      elementWidth: element.width,
      elementHeight: element.height,
    });
  }, [currentPage]);

  const handleMouseMove = useCallback((e) => {
    if (isDragging && selectedId && dragStart) {
      const newX = (e.clientX - dragStart.x) / zoom;
      const newY = (e.clientY - dragStart.y) / zoom;
      updateElement(selectedId, { x: newX, y: newY });
    } else if (isResizing && selectedId && resizeStart) {
      const dx = e.clientX - resizeStart.x;
      const dy = e.clientY - resizeStart.y;
      
      let updates = {};
      
      if (resizeHandle.includes('e')) {
        updates.width = Math.max(20, resizeStart.elementWidth + dx / zoom);
      }
      if (resizeHandle.includes('w')) {
        const newWidth = Math.max(20, resizeStart.elementWidth - dx / zoom);
        updates.width = newWidth;
        updates.x = resizeStart.elementX + (resizeStart.elementWidth - newWidth);
      }
      if (resizeHandle.includes('s')) {
        updates.height = Math.max(20, resizeStart.elementHeight + dy / zoom);
      }
      if (resizeHandle.includes('n')) {
        const newHeight = Math.max(20, resizeStart.elementHeight - dy / zoom);
        updates.height = newHeight;
        updates.y = resizeStart.elementY + (resizeStart.elementHeight - newHeight);
      }
      
      updateElement(selectedId, updates);
    }
  }, [isDragging, isResizing, selectedId, dragStart, resizeStart, resizeHandle, zoom, updateElement, currentPage]);

  const handleMouseUp = useCallback(() => {
    if (isDragging || isResizing) {
      saveHistory();
    }
    setIsDragging(false);
    setIsResizing(false);
    setDragStart(null);
    setResizeStart(null);
    setResizeHandle(null);
  }, [isDragging, isResizing, saveHistory]);

  useEffect(() => {
    if (isDragging || isResizing) {
      window.addEventListener('mousemove', handleMouseMove);
      window.addEventListener('mouseup', handleMouseUp);
      return () => {
        window.removeEventListener('mousemove', handleMouseMove);
        window.removeEventListener('mouseup', handleMouseUp);
      };
    }
  }, [isDragging, isResizing, handleMouseMove, handleMouseUp]);

  // Canvas click to deselect
  const handleCanvasClick = useCallback((e) => {
    if (e.target === e.currentTarget || e.target.classList.contains('canvas-content')) {
      setSelectedId(null);
    }
  }, []);

  // Page management
  const addPage = useCallback(() => {
    setPages(prevPages => {
      const newPage = {
        id: String(Date.now()),
        name: `Page ${prevPages.length + 1}`,
        elements: [],
      };
      setCurrentPageId(newPage.id);
      return [...prevPages, newPage];
    });
    saveHistory();
  }, [saveHistory]);

  const deletePage = useCallback((pageId) => {
    setPages(prevPages => {
      if (prevPages.length === 1) return prevPages;
      const newPages = prevPages.filter(p => p.id !== pageId);
      if (currentPageId === pageId) {
        setCurrentPageId(newPages[0].id);
      }
      return newPages;
    });
    saveHistory();
  }, [currentPageId, saveHistory]);

  // Export functions
  const exportToPNG = useCallback(async () => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    
    const contentDiv = canvas.querySelector('.canvas-content');
    if (!contentDiv) return;

    try {
      const canvasEl = await html2canvas(contentDiv, {
        backgroundColor: '#ffffff',
        scale: 2,
      });
      
      const link = document.createElement('a');
      link.download = `${currentPage.name}.png`;
      link.href = canvasEl.toDataURL();
      link.click();
    } catch (error) {
      console.error('Export to PNG failed:', error);
      alert('Export failed. Please try again.');
    }
  }, [currentPage]);

  const exportToPDF = useCallback(async () => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    
    const contentDiv = canvas.querySelector('.canvas-content');
    if (!contentDiv) return;

    try {
      const canvasEl = await html2canvas(contentDiv, {
        backgroundColor: '#ffffff',
        scale: 2,
      });
      
      const imgData = canvasEl.toDataURL('image/png');
      const pdf = new jsPDF({
        orientation: canvasEl.width > canvasEl.height ? 'landscape' : 'portrait',
        unit: 'px',
        format: [canvasEl.width, canvasEl.height],
      });
      
      pdf.addImage(imgData, 'PNG', 0, 0, canvasEl.width, canvasEl.height);
      pdf.save(`${currentPage.name}.pdf`);
    } catch (error) {
      console.error('Export to PDF failed:', error);
      alert('Export failed. Please try again.');
    }
  }, [currentPage]);

  // Zoom controls
  const zoomIn = () => setZoom(Math.min(zoom + 0.1, 2));
  const zoomOut = () => setZoom(Math.max(zoom - 0.1, 0.5));
  const resetZoom = () => setZoom(1);

  // Render element with sketch style
  const renderElement = (element) => {
    const getElementStyle = () => {
      switch (element.type) {
        case 'button':
          return { border: '3px solid #333', borderRadius: '6px', fontWeight: 'bold' };
        case 'input':
          return { border: '2px solid #666', borderRadius: '4px', background: '#fff' };
        case 'text':
          return { border: 'none', background: 'transparent', justifyContent: 'flex-start' };
        case 'image':
          return { border: '3px solid #333', background: '#e8e8e8' };
        case 'navbar':
          return { border: '3px solid #333', background: '#d0d0d0', justifyContent: 'space-around' };
        case 'table':
          return { 
            border: '3px solid #333', 
            display: 'grid', 
            gridTemplateColumns: 'repeat(3, 1fr)',
            gap: '2px',
            background: '#333'
          };
        case 'modal':
          return { 
            border: '4px solid #333', 
            borderRadius: '8px',
            background: '#f5f5f5',
            boxShadow: '0 4px 12px rgba(0,0,0,0.3)'
          };
        case 'frame':
          return { border: '3px dashed #666', background: 'transparent' };
        default:
          return {};
      }
    };

    return (
      <div
        key={element.id}
        className={`element ${selectedId === element.id ? 'selected' : ''}`}
        style={{
          left: element.x,
          top: element.y,
          width: element.width,
          height: element.height,
          zIndex: element.zIndex,
        }}
        onMouseDown={(e) => handleMouseDown(e, element.id)}
      >
        <div className="element-content" style={getElementStyle()}>
          {element.type === 'table' ? (
            <>
              {[...Array(9)].map((_, i) => (
                <div key={i} style={{ background: '#fff', padding: '4px' }}>
                  Cell {i + 1}
                </div>
              ))}
            </>
          ) : (
            element.text
          )}
        </div>
        
        {selectedId === element.id && (
          <>
            <div className="resize-handle nw" onMouseDown={(e) => handleResizeMouseDown(e, element.id, 'nw')} />
            <div className="resize-handle ne" onMouseDown={(e) => handleResizeMouseDown(e, element.id, 'ne')} />
            <div className="resize-handle sw" onMouseDown={(e) => handleResizeMouseDown(e, element.id, 'sw')} />
            <div className="resize-handle se" onMouseDown={(e) => handleResizeMouseDown(e, element.id, 'se')} />
            <div className="resize-handle n" onMouseDown={(e) => handleResizeMouseDown(e, element.id, 'n')} />
            <div className="resize-handle s" onMouseDown={(e) => handleResizeMouseDown(e, element.id, 's')} />
            <div className="resize-handle w" onMouseDown={(e) => handleResizeMouseDown(e, element.id, 'w')} />
            <div className="resize-handle e" onMouseDown={(e) => handleResizeMouseDown(e, element.id, 'e')} />
          </>
        )}
      </div>
    );
  };

  return (
    <div className="app">
      <header className="header">
        <div className="logo">Wireframe Studio</div>
        <div className="toolbar">
          <div className="toolbar-group">
            <button className="btn" onClick={undo} disabled={historyIndex <= 0}>
              ↶ Undo
            </button>
            <button className="btn" onClick={redo} disabled={historyIndex >= history.length - 1}>
              ↷ Redo
            </button>
          </div>
          <div className="toolbar-group">
            <button className="btn" onClick={() => setShowGrid(!showGrid)}>
              {showGrid ? '◫ Hide Grid' : '◫ Show Grid'}
            </button>
          </div>
          <div className="toolbar-group">
            <button className="btn" onClick={bringToFront} disabled={!selectedId}>
              ⬆ Front
            </button>
            <button className="btn" onClick={sendToBack} disabled={!selectedId}>
              ⬇ Back
            </button>
          </div>
          <div className="toolbar-group">
            <button className="btn" onClick={deleteElement} disabled={!selectedId}>
              🗑 Delete
            </button>
          </div>
          <div className="toolbar-group">
            <button className="btn" onClick={exportToPNG}>
              📷 PNG
            </button>
            <button className="btn" onClick={exportToPDF}>
              📄 PDF
            </button>
          </div>
        </div>
      </header>

      <div className="main-content">
        <aside className="sidebar">
          <h3>Pages</h3>
          <div className="pages-list">
            {pages.map(page => (
              <div
                key={page.id}
                className={`page-item ${page.id === currentPageId ? 'active' : ''}`}
                onClick={() => setCurrentPageId(page.id)}
              >
                <span className="page-name">{page.name}</span>
                {pages.length > 1 && (
                  <button
                    className="page-delete"
                    onClick={(e) => {
                      e.stopPropagation();
                      deletePage(page.id);
                    }}
                  >
                    ✕
                  </button>
                )}
              </div>
            ))}
            <button className="btn" style={{ width: '100%' }} onClick={addPage}>
              + Add Page
            </button>
          </div>

          <h3>Components</h3>
          <div className="components-grid">
            {COMPONENT_TYPES.map(comp => (
              <button
                key={comp.type}
                className="component-btn"
                onClick={() => addElement(comp.type)}
              >
                {comp.label}
              </button>
            ))}
          </div>
        </aside>

        <div className="canvas-container">
          <div 
            ref={canvasRef}
            className={`canvas ${isDragging ? 'grabbing' : ''}`}
            onClick={handleCanvasClick}
          >
            <div 
              className="canvas-content"
              style={{ transform: `scale(${zoom})` }}
            >
              {showGrid && <div className="grid" />}
              {currentPage?.elements
                .sort((a, b) => a.zIndex - b.zIndex)
                .map(renderElement)}
            </div>
          </div>

          <div className="zoom-control">
            <button className="zoom-btn" onClick={zoomOut}>-</button>
            <div className="zoom-level">{Math.round(zoom * 100)}%</div>
            <button className="zoom-btn" onClick={zoomIn}>+</button>
            <button className="zoom-btn" onClick={resetZoom}>Reset</button>
          </div>
        </div>

        {selectedElement && (
          <aside className="property-panel">
            <h3>Properties</h3>
            <div className="property-group">
              <label>Text</label>
              <textarea
                value={selectedElement.text}
                onChange={(e) => updateElement(selectedId, { text: e.target.value })}
                onBlur={saveHistory}
              />
            </div>
            <div className="property-group">
              <label>X Position</label>
              <input
                type="number"
                value={Math.round(selectedElement.x)}
                onChange={(e) => updateElement(selectedId, { x: parseInt(e.target.value) || 0 })}
                onBlur={saveHistory}
              />
            </div>
            <div className="property-group">
              <label>Y Position</label>
              <input
                type="number"
                value={Math.round(selectedElement.y)}
                onChange={(e) => updateElement(selectedId, { y: parseInt(e.target.value) || 0 })}
                onBlur={saveHistory}
              />
            </div>
            <div className="property-group">
              <label>Width</label>
              <input
                type="number"
                value={Math.round(selectedElement.width)}
                onChange={(e) => updateElement(selectedId, { width: parseInt(e.target.value) || 20 })}
                onBlur={saveHistory}
              />
            </div>
            <div className="property-group">
              <label>Height</label>
              <input
                type="number"
                value={Math.round(selectedElement.height)}
                onChange={(e) => updateElement(selectedId, { height: parseInt(e.target.value) || 20 })}
                onBlur={saveHistory}
              />
            </div>
          </aside>
        )}
      </div>
    </div>
  );
}

export default App;
