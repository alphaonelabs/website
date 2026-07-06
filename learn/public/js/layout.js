// ── Authentication utilities ──────────────────────────────────────────
function getAuth() {
    return {
        token: localStorage.getItem('edu_token'),
        user: JSON.parse(localStorage.getItem('edu_user') || 'null')
    };
}

function isAuthenticated() {
    const { token, user } = getAuth();
    return token && user;
}

function logout() {
    localStorage.removeItem('edu_token');
    localStorage.removeItem('edu_user');
    window.location.href = '/login';
}

window.esc = window.esc || function (s) {
    return String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
};

window.cartHumanStartedAt = window.cartHumanStartedAt || Date.now();

function getGuestCartToken() {
    try {
        let token = localStorage.getItem('guest_cart_token');
        if (!token) {
            const bytes = new Uint8Array(32);
            window.crypto.getRandomValues(bytes);
            token = 'gct_' + Array.from(bytes).map((b) => b.toString(16).padStart(2, '0')).join('');
            localStorage.setItem('guest_cart_token', token);
        }
        return token;
    } catch (_) {
        return 'gct_' + String(Date.now()) + Math.random().toString(16).slice(2);
    }
}

function cartHumanProof() {
    return {
        human_started_at: window.cartHumanStartedAt,
        human_confirmed_at: Date.now(),
        company_website: '',
    };
}

function cartRequestHeaders() {
    const { token } = getAuth();
    const headers = { 'Content-Type': 'application/json' };
    if (token) headers.Authorization = `Bearer ${token}`;
    else headers['X-Guest-Cart'] = getGuestCartToken();
    return headers;
}

window.getGuestCartToken = getGuestCartToken;
window.cartHumanProof = cartHumanProof;
window.cartRequestHeaders = cartRequestHeaders;

// ── Dark mode utilities ───────────────────────────────────────────────
window.toggleDarkMode = function () {
    const isDark = document.documentElement.classList.toggle('dark');
    localStorage.setItem('darkMode', isDark.toString());
    updateDarkModeIcon();
};

function updateDarkModeIcon() {
    const isDark = document.documentElement.classList.contains('dark');
    const icon = document.getElementById('darkModeIcon');
    const iconMobile = document.getElementById('darkModeIconMobile');
    
    if (icon) {
        icon.className = isDark ? 'fas fa-sun' : 'fas fa-moon';
        icon.title = isDark ? 'Switch to Light Mode' : 'Switch to Dark Mode';
    }
    if (iconMobile) {
        iconMobile.className = isDark ? 'fas fa-sun mr-2 text-teal-500' : 'fas fa-moon mr-2 text-teal-500';
    }
}

function initializeDarkMode() {
    const darkModeEnabled = localStorage.getItem('darkMode') === 'true';
    if (darkModeEnabled) {
        document.documentElement.classList.add('dark');
    } else if (localStorage.getItem('darkMode') === null) {
        localStorage.setItem('darkMode', 'false');
    }
    updateDarkModeIcon();
}

// ── Layout injection ──────────────────────────────────────────────────
async function inject(id, file, callback) {
    const el = document.getElementById(id);
    if (!el) return;
    if (el.dataset.inline === 'true') {
        if (callback && typeof callback === 'function') {
            callback();
        }
        return;
    }
    try {
        const res = await fetch(file);
        el.innerHTML = await res.text();
        if (callback && typeof callback === 'function') {
            callback();
        }
    } catch (err) {
        console.error(`Failed to load ${file}:`, err);
    }
}

// ── Profile dropdown toggle ──────────────────────────────────────────
window.toggleProfileDropdown = function () {
    const dropdown = document.getElementById('profile-dropdown');
    if (dropdown) {
        dropdown.classList.toggle('hidden');
    }
};

// ── Update auth section with profile ─────────────────────────────────
function updateAuthSection() {
    const { token, user } = getAuth();
    const notLoggedInDiv = document.getElementById('auth-not-logged-in');
    const loggedInDiv = document.getElementById('auth-logged-in');
    const mobileNotLoggedIn = document.getElementById('mobile-auth-not-logged-in');
    const mobileLoggedIn = document.getElementById('mobile-auth-logged-in');

    if (token && user) {
        // User is logged in
        const firstName = user.name ? user.name.split(' ')[0] : user.username;
        const firstLetter = firstName.charAt(0).toUpperCase();

        // Desktop view
        if (notLoggedInDiv) notLoggedInDiv.classList.add('hidden');
        if (loggedInDiv) loggedInDiv.classList.remove('hidden');
        
        const avatarEl = document.getElementById('profile-avatar');
        const greetingEl = document.getElementById('profile-greeting');
        const usernameEl = document.getElementById('dropdown-username');
        
        if (avatarEl) avatarEl.textContent = firstLetter;
        if (greetingEl) greetingEl.textContent = `Hi, ${firstName}`;
        if (usernameEl) usernameEl.textContent = user.username;

        // Mobile view
        if (mobileNotLoggedIn) mobileNotLoggedIn.classList.add('hidden');
        if (mobileLoggedIn) mobileLoggedIn.classList.remove('hidden');
        
        const mobileAvatarEl = document.getElementById('mobile-profile-avatar');
        const mobileGreetingEl = document.getElementById('mobile-profile-greeting');
        
        if (mobileAvatarEl) mobileAvatarEl.textContent = firstLetter;
        if (mobileGreetingEl) mobileGreetingEl.textContent = `Hi, ${firstName}`;

        startUnreadPolling();
        refreshCartBadge();
    } else {
        // User is not logged in
        if (notLoggedInDiv) notLoggedInDiv.classList.remove('hidden');
        if (loggedInDiv) loggedInDiv.classList.add('hidden');
        if (mobileNotLoggedIn) mobileNotLoggedIn.classList.remove('hidden');
        if (mobileLoggedIn) mobileLoggedIn.classList.add('hidden');

        const badge = document.getElementById('notif-unread-badge');
        if (badge) badge.classList.add('hidden');
        const notifLink = document.getElementById('notif-bell-link');
        if (notifLink) notifLink.classList.add('hidden');
        const cartBadge = document.getElementById('cart-count-badge');
        if (cartBadge) cartBadge.classList.add('hidden');
        const cartLink = document.getElementById('cart-nav-link');
        if (cartLink) cartLink.classList.add('hidden');
        stopUnreadPolling();
        refreshCartBadge();
    }
}

window.updateAuthSection = updateAuthSection;

async function refreshUnreadBadge() {
    const badge = document.getElementById('notif-unread-badge');
    const link = document.getElementById('notif-bell-link');
    const { token } = getAuth();
    if (!badge) return;
    if (!token) {
        badge.classList.add('hidden');
        if (link) link.classList.add('hidden');
        return;
    }
    if (link) link.classList.remove('hidden');
    try {
        const res = await fetch('/api/notifications/unread-count', {
            headers: { Authorization: `Bearer ${token}` },
        });
        if (!res.ok) return;
        const body = await res.json();
        const count = (body.data && body.data.unread_count) || 0;
        if (count > 0) {
            badge.textContent = count > 99 ? '99+' : String(count);
            badge.classList.remove('hidden');
            if (link) link.classList.remove('hidden');
        } else {
            badge.classList.add('hidden');
            if (link) link.classList.add('hidden');
        }
    } catch (_) {
        /* ignore */
    }
}

window.refreshUnreadBadge = refreshUnreadBadge;

var unreadPollTimer = null;

function startUnreadPolling() {
    if (unreadPollTimer) return;
    unreadPollTimer = setInterval(() => {
        refreshUnreadBadge();
    }, 5000);
    refreshUnreadBadge();
}

function stopUnreadPolling() {
    if (!unreadPollTimer) return;
    clearInterval(unreadPollTimer);
    unreadPollTimer = null;
}

window.startUnreadPolling = startUnreadPolling;
window.stopUnreadPolling = stopUnreadPolling;

async function refreshCartBadge() {
    const badge = document.getElementById('cart-count-badge');
    const link = document.getElementById('cart-nav-link');
    const { token } = getAuth();
    if (!badge) return;
    if (!token && !localStorage.getItem('guest_cart_token')) {
        badge.classList.add('hidden');
        if (link) link.classList.add('hidden');
        return;
    }
    try {
        const res = await fetch('/api/cart', {
            headers: cartRequestHeaders(),
        });
        if (!res.ok) return;
        const body = await res.json();
        const count = (body.items || []).reduce((sum, item) => sum + Number(item.quantity || 1), 0);
        if (count > 0) {
            badge.textContent = count > 99 ? '99+' : String(count);
            badge.classList.remove('hidden');
        } else {
            badge.classList.add('hidden');
        }
    } catch (_) {
        /* ignore */
    }
}

window.refreshCartBadge = refreshCartBadge;

// ── Mobile menu toggle ────────────────────────────────────────────────
window.toggleMobileMenu = function () {
    const menu = document.getElementById('mobile-menu');
    if (!menu) return;
    menu.classList.toggle('hidden');
    document.body.classList.toggle('overflow-hidden');
};

// ── Accordion toggle ──────────────────────────────────────────────────
window.toggleAccordion = function (accordionId) {
    const accordion = document.getElementById(accordionId);
    const icon = document.getElementById(`${accordionId}-icon`);
    if (!accordion || !icon) return;
    accordion.classList.toggle('hidden');
    icon.classList.toggle('rotate-180', !accordion.classList.contains('hidden'));
};

// ── Click outside handlers ────────────────────────────────────────────
document.addEventListener('click', (event) => {
    const menu = document.getElementById('mobile-menu');
    const menuBtn = event.target.closest('[onclick="toggleMobileMenu()"]');
    const menuContent = event.target.closest('.mobile-menu-content');
    if (menu && !menu.classList.contains('hidden') && !menuBtn && !menuContent) {
        window.toggleMobileMenu();
    }

    // Close profile dropdown when clicking outside
    const profileBtn = document.querySelector('[onclick="toggleProfileDropdown()"]');
    const profileDropdown = document.getElementById('profile-dropdown');
    if (profileDropdown && !profileDropdown.contains(event.target) && !profileBtn?.contains(event.target)) {
        profileDropdown.classList.add('hidden');
    }
});

function applyUnreadBadgeCount(count) {
    const badge = document.getElementById('notif-unread-badge');
    if (!badge) return;
    if (count > 0) {
        badge.textContent = count > 99 ? '99+' : String(count);
        badge.classList.remove('hidden');
        badge.setAttribute('aria-label', `${count} unread notifications`);
    } else {
        badge.classList.add('hidden');
        badge.setAttribute('aria-label', '');
    }
    const link = document.getElementById('notif-bell-link');
    if (link) {
        link.setAttribute('aria-label', count > 0 ? `Notifications, ${count} unread` : 'Notifications');
    }
}

window.applyUnreadBadgeCount = applyUnreadBadgeCount;

// ── Initialize on DOM ready ───────────────────────────────────────────
let layoutInitPromise = null;

async function initLayout() {
    if (!layoutInitPromise) {
        layoutInitPromise = (async () => {
            initializeDarkMode();
            await inject('site-navbar', '/partials/navbar.html', updateAuthSection);
            await inject('site-footer', '/partials/footer.html');
            updateDarkModeIcon();
        })();
    }
    return layoutInitPromise;
}

window.initLayout = initLayout;

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initLayout);
} else {
    initLayout();
}

// Conditional rendering for the "Join Lobby Classroom" button.
// These elements only exist on the homepage, so we guard against nulls.
document.addEventListener('DOMContentLoaded', () => {
    const loggedInEl = document.getElementById('join-logged-in');
    const notLoggedInEl = document.getElementById('join-not-logged-in');
    if (!loggedInEl || !notLoggedInEl) return;

    const authed = isAuthenticated();
    loggedInEl.style.display = authed ? 'flex' : 'none';
    notLoggedInEl.style.display = authed ? 'none' : 'flex';
});
