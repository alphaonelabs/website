// web/static/js/subjects-filter.js
document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('filterForm');
    const searchInput = document.getElementById('search');
    const resultsContainer = document.getElementById('results'); // <-- add a div for results
    let searchTimeout;

    if (!form || !resultsContainer){
        // Nothing to wire; exit safely on pages without the filter UI.
        return;
    }

    // Fetch results via AJAX with optional pagination reset
    function fetchResults(urlOverride, resetPagination = false) {
        const formData = new FormData(form);
        const params = new URLSearchParams();

        for (let [key, value] of formData.entries()) {
            if (value && value.trim() !== '') {
                // Skip page parameter if we're resetting pagination
                if (resetPagination && key === 'page') {
                    continue;
                }
                params.append(key, value);
            }
        }

        const url = urlOverride || (window.location.pathname + (params.toString() ? '?' + params.toString() : ''));

        // Update URL without reload
        window.history.replaceState({}, '', url);

        // Show loading state
        if (resultsContainer) {
            resultsContainer.innerHTML = '<p>Loading...</p>';
        }

        // Fetch filtered results
        fetch(url, {
            headers: { "X-Requested-With": "XMLHttpRequest" } // so backend can detect AJAX
        })
        .then(response => response.text())
        .then(html => {
            // Replace results section
            if (resultsContainer) {
                resultsContainer.innerHTML = html;
                // No need to re-attach pagination handlers - using event delegation instead
            }
        })
        .catch(error => {
            console.error("Error fetching results:", error);
        });
    }

    // Handle pagination clicks with AJAX using event delegation
    resultsContainer.addEventListener('click', function(e) {
        const paginationLink = e.target.closest('nav a[href*="page="]');
        if (paginationLink) {
            e.preventDefault();
            const url = paginationLink.getAttribute('href');
            fetchResults(url); // Don't reset pagination when navigating pages
        }
    });

    // Debounced search
    if (searchInput){
        searchInput.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => fetchResults(null, true), 500); // Reset pagination on search
        });
    }

    // Auto-submit on filter changes
    const filterControls = form.querySelectorAll('select, input[type="checkbox"], input[type="number"]');
    filterControls.forEach(function(element) {
        if (element.id !== 'search') {
            element.addEventListener('change', () => fetchResults(null, true)); // Reset pagination on filter change
        }
    });

    // Clear individual filter
    window.clearFilter = function(filterName) {
        const element = document.querySelector(`[name="${filterName}"]`);
        if (element) {
            if (element.type === 'checkbox') {
                element.checked = false;
            } else {
                element.value = '';
            }
            fetchResults(null, true); // Reset pagination when clearing filters
        }
    };

    // Reset all filters
    window.resetAllFilters = function() {
        window.history.replaceState({}, '', window.location.pathname);
        form.reset();
        fetchResults(null, true); // Reset pagination when resetting all filters
    };
});
