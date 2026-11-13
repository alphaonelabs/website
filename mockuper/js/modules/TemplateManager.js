/**
 * TemplateManager Module
 * Pure data/logic module — no DOM access.
 * Provides built-in wireframe templates and applies them to a page via StateManager.
 */

const BUILT_IN_TEMPLATES = [
  // ----------------------------------------------------------------
  // Template 1 — Landing Page
  // ----------------------------------------------------------------
  {
    id: 'landing-page',
    name: 'Landing Page',
    description: 'A simple landing page with navbar, hero image, headline, CTA, and footer.',
    thumbnail: '🏠',
    elements: [
      { id: '1', type: 'navbar', x: 20,  y: 20,  width: 760, height: 60,  text: 'Nav Bar',                zIndex: 0 },
      { id: '2', type: 'image',  x: 20,  y: 100, width: 760, height: 300, text: 'Hero Image',             zIndex: 1 },
      { id: '3', type: 'text',   x: 200, y: 420, width: 400, height: 50,  text: 'Welcome to our product', zIndex: 2 },
      { id: '4', type: 'button', x: 330, y: 490, width: 140, height: 44,  text: 'Get Started',            zIndex: 3 },
      { id: '5', type: 'text',   x: 20,  y: 570, width: 760, height: 30,  text: '© 2024 Company Name',   zIndex: 4 },
    ],
  },

  // ----------------------------------------------------------------
  // Template 2 — Login Form
  // ----------------------------------------------------------------
  {
    id: 'login-form',
    name: 'Login Form',
    description: 'A centred sign-in card with email, password, submit button, and forgot-password link.',
    thumbnail: '🔐',
    elements: [
      { id: '1', type: 'frame',  x: 230, y: 80,  width: 340, height: 380, text: '',               zIndex: 0 },
      { id: '2', type: 'text',   x: 270, y: 110, width: 260, height: 40,  text: 'Sign In',        zIndex: 1 },
      { id: '3', type: 'text',   x: 270, y: 170, width: 260, height: 24,  text: 'Email',          zIndex: 2 },
      { id: '4', type: 'input',  x: 270, y: 196, width: 260, height: 40,  text: 'Email',          zIndex: 3 },
      { id: '5', type: 'text',   x: 270, y: 250, width: 260, height: 24,  text: 'Password',       zIndex: 4 },
      { id: '6', type: 'input',  x: 270, y: 276, width: 260, height: 40,  text: 'Password',       zIndex: 5 },
      { id: '7', type: 'button', x: 260, y: 338, width: 260, height: 44,  text: 'Sign In',        zIndex: 6 },
      { id: '8', type: 'text',   x: 270, y: 400, width: 260, height: 24,  text: 'Forgot password?', zIndex: 7 },
    ],
  },

  // ----------------------------------------------------------------
  // Template 3 — Dashboard
  // ----------------------------------------------------------------
  {
    id: 'dashboard',
    name: 'Dashboard',
    description: 'Admin dashboard with navbar, sidebar, stat cards, data table, and footer.',
    thumbnail: '📊',
    elements: [
      { id: '1',  type: 'navbar', x: 0,   y: 0,   width: 800, height: 56,  text: 'Dashboard',     zIndex: 0 },
      { id: '2',  type: 'frame',  x: 0,   y: 56,  width: 200, height: 544, text: '',              zIndex: 1 },
      { id: '3',  type: 'text',   x: 20,  y: 80,  width: 160, height: 30,  text: 'Overview',      zIndex: 2 },
      { id: '4',  type: 'text',   x: 20,  y: 120, width: 160, height: 30,  text: 'Analytics',     zIndex: 3 },
      { id: '5',  type: 'text',   x: 20,  y: 160, width: 160, height: 30,  text: 'Reports',       zIndex: 4 },
      { id: '6',  type: 'frame',  x: 220, y: 72,  width: 160, height: 100, text: 'Total Users',   zIndex: 5 },
      { id: '7',  type: 'frame',  x: 400, y: 72,  width: 160, height: 100, text: 'Revenue',       zIndex: 6 },
      { id: '8',  type: 'frame',  x: 580, y: 72,  width: 160, height: 100, text: 'Sessions',      zIndex: 7 },
      { id: '9',  type: 'table',  x: 220, y: 192, width: 540, height: 300, text: 'Data Table',    zIndex: 8 },
      { id: '10', type: 'text',   x: 220, y: 504, width: 540, height: 30,  text: '© 2024 Dashboard', zIndex: 9 },
    ],
  },

  // ----------------------------------------------------------------
  // Template 4 — Blog Post
  // ----------------------------------------------------------------
  {
    id: 'blog-post',
    name: 'Blog Post',
    description: 'Article layout with navbar, title, author line, hero image, body text, and sidebar.',
    thumbnail: '📝',
    elements: [
      { id: '1', type: 'navbar', x: 0,   y: 0,   width: 800, height: 56,  text: 'Blog',                       zIndex: 0 },
      { id: '2', type: 'text',   x: 20,  y: 72,  width: 560, height: 48,  text: 'Article Title Goes Here',    zIndex: 1 },
      { id: '3', type: 'text',   x: 20,  y: 128, width: 300, height: 24,  text: 'By Author · Jan 1, 2024',    zIndex: 2 },
      { id: '4', type: 'image',  x: 20,  y: 160, width: 560, height: 200, text: 'Hero Image',                 zIndex: 3 },
      { id: '5', type: 'text',   x: 20,  y: 376, width: 560, height: 80,  text: 'Lorem ipsum paragraph one.', zIndex: 4 },
      { id: '6', type: 'frame',  x: 600, y: 72,  width: 180, height: 300, text: 'Sidebar',                    zIndex: 5 },
      { id: '7', type: 'text',   x: 20,  y: 470, width: 560, height: 80,  text: 'Lorem ipsum paragraph two.', zIndex: 6 },
    ],
  },

  // ----------------------------------------------------------------
  // Template 5 — Mobile App Screen
  // ----------------------------------------------------------------
  {
    id: 'mobile-app',
    name: 'Mobile App Screen',
    description: 'Mobile-frame mockup with app title, feature image, description, and action buttons.',
    thumbnail: '📱',
    elements: [
      { id: '1', type: 'mobile', x: 213, y: 20,  width: 375, height: 667, text: 'Mobile App',         zIndex: 0 },
      { id: '2', type: 'text',   x: 233, y: 80,  width: 335, height: 30,  text: 'App Title',           zIndex: 1 },
      { id: '3', type: 'image',  x: 233, y: 124, width: 335, height: 200, text: 'Feature Image',       zIndex: 2 },
      { id: '4', type: 'text',   x: 233, y: 340, width: 335, height: 60,  text: 'App description text here.', zIndex: 3 },
      { id: '5', type: 'button', x: 293, y: 420, width: 215, height: 44,  text: 'Get Started',         zIndex: 4 },
      { id: '6', type: 'button', x: 293, y: 476, width: 215, height: 40,  text: 'Learn More',          zIndex: 5 },
    ],
  },

  // ----------------------------------------------------------------
  // Template 6 — Settings Page
  // ----------------------------------------------------------------
  {
    id: 'settings-page',
    name: 'Settings Page',
    description: 'User settings with profile section, display name, email, preferences toggles, and save button.',
    thumbnail: '⚙️',
    elements: [
      { id: '1',  type: 'navbar', x: 0,   y: 0,   width: 800, height: 56,  text: 'Settings',          zIndex: 0  },
      { id: '2',  type: 'text',   x: 20,  y: 72,  width: 200, height: 32,  text: 'Profile',           zIndex: 1  },
      { id: '3',  type: 'image',  x: 20,  y: 112, width: 80,  height: 80,  text: 'Avatar',            zIndex: 2  },
      { id: '4',  type: 'text',   x: 20,  y: 204, width: 300, height: 24,  text: 'Display Name',      zIndex: 3  },
      { id: '5',  type: 'input',  x: 20,  y: 230, width: 300, height: 40,  text: 'Display Name',      zIndex: 4  },
      { id: '6',  type: 'text',   x: 20,  y: 282, width: 300, height: 24,  text: 'Email',             zIndex: 5  },
      { id: '7',  type: 'input',  x: 20,  y: 308, width: 300, height: 40,  text: 'Email',             zIndex: 6  },
      { id: '8',  type: 'text',   x: 20,  y: 364, width: 200, height: 32,  text: 'Preferences',       zIndex: 7  },
      { id: '9',  type: 'text',   x: 20,  y: 406, width: 160, height: 24,  text: 'Dark Mode',         zIndex: 8  },
      { id: '10', type: 'button', x: 200, y: 402, width: 80,  height: 32,  text: 'Toggle',            zIndex: 9  },
      { id: '11', type: 'text',   x: 20,  y: 446, width: 160, height: 24,  text: 'Notifications',     zIndex: 10 },
      { id: '12', type: 'button', x: 200, y: 442, width: 80,  height: 32,  text: 'Enable',            zIndex: 11 },
      { id: '13', type: 'button', x: 20,  y: 490, width: 120, height: 44,  text: 'Save Changes',      zIndex: 12 },
    ],
  },
];

export default class TemplateManager {
  constructor() {
    this._templates = [...BUILT_IN_TEMPLATES];
  }

  /** Returns all available templates. */
  getAll() {
    return this._templates;
  }

  /** Returns the template with the given id, or null if not found. */
  getById(id) {
    return this._templates.find(t => t.id === id) || null;
  }

  /**
   * Applies a template to the current page in state.
   *
   * - Deep-copies all template elements (no shared references).
   * - Re-keys element ids so they never collide with existing state ids.
   * - Advances state.nextElementId past every id used.
   * - Clears selection, saves undo history, then notifies listeners.
   *
   * @param {string} templateId
   * @param {StateManager} state
   * @returns {boolean} true on success, false if template or current page not found.
   */
  applyToPage(templateId, state) {
    const tpl = this.getById(templateId);
    if (!tpl) return false;

    const page = state.getCurrentPage();
    if (!page) return false;

    // Deep copy the template elements
    const copied = JSON.parse(JSON.stringify(tpl.elements));

    // Find the highest numeric id already in the copied elements
    const maxIdInCopied = copied.reduce((max, el) => {
      const n = parseInt(el.id, 10);
      return isNaN(n) ? max : Math.max(max, n);
    }, 0);

    // base must be strictly above both the state counter and the max template id
    const base = Math.max(state.nextElementId, maxIdInCopied + 1);

    // Re-key ids
    copied.forEach((el, i) => {
      el.id = String(base + i);
    });

    // Advance the counter past all ids we just assigned
    state.nextElementId = base + copied.length;

    // Replace page elements and clear selection
    page.elements = copied;
    state.selectedElementId = null;

    // Save undo snapshot then notify listeners
    state.saveHistory();
    state.notify();

    return true;
  }
}
