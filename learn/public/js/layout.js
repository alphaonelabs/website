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
    window.location.href = '/login.html';
}

function esc(s) {
    return String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

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
    } else {
        // User is not logged in
        if (notLoggedInDiv) notLoggedInDiv.classList.remove('hidden');
        if (loggedInDiv) loggedInDiv.classList.add('hidden');
        if (mobileNotLoggedIn) mobileNotLoggedIn.classList.remove('hidden');
        if (mobileLoggedIn) mobileLoggedIn.classList.add('hidden');
    }
}

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

// ── Language dropdown ─────────────────────────────────────────────────
window.toggleLanguageDropdown = function () {
    document.getElementById('language-dropdown')?.classList.toggle('hidden');
};

window.setLanguage = function (lang) {
    localStorage.setItem('language', lang);
    console.log('Language set to:', lang);
    window.toggleLanguageDropdown();
};

// ── Click outside handlers ────────────────────────────────────────────
document.addEventListener('click', (event) => {
    const menu = document.getElementById('mobile-menu');
    const menuBtn = event.target.closest('[onclick="toggleMobileMenu()"]');
    const menuContent = event.target.closest('.mobile-menu-content');
    if (menu && !menu.classList.contains('hidden') && !menuBtn && !menuContent) {
        window.toggleMobileMenu();
    }

    const langDropdown = document.getElementById('language-dropdown');
    if (
        langDropdown &&
        !event.target.closest('[onclick="toggleLanguageDropdown()"]') &&
        !langDropdown.contains(event.target)
    ) {
        langDropdown.classList.add('hidden');
    }

    // Close profile dropdown when clicking outside
    const profileBtn = document.querySelector('[onclick="toggleProfileDropdown()"]');
    const profileDropdown = document.getElementById('profile-dropdown');
    if (profileDropdown && !profileDropdown.contains(event.target) && !profileBtn?.contains(event.target)) {
        profileDropdown.classList.add('hidden');
    }
});

// ── Initialize on DOM ready ───────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
    initializeDarkMode();
    await inject('site-navbar', '/partials/navbar.html', updateAuthSection);
    await inject('site-footer', '/partials/footer.html');
     updateDarkModeIcon();
});

// conditional rendering for the join lobby classroom btn
document.addEventListener('DOMContentLoaded', function() {
    const loggedInEl = document.getElementById('join-logged-in');
    const notLoggedInEl = document.getElementById('join-not-logged-in');
    const token = localStorage.getItem('edu_token');
    const user = JSON.parse(localStorage.getItem('edu_user') || 'null');
    if (token && user) {
        loggedInEl.style.display = 'flex';
        notLoggedInEl.style.display = 'none';
    } else {
        loggedInEl.style.display = 'none';
        notLoggedInEl.style.display = 'flex';
    }
});