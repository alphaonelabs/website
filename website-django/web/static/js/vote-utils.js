/**
 * Utility functions for feature voting functionality
 */
const VoteUtils = {
    /**
     * Set button loading state
     * @param {HTMLElement} btn - The button element
     * @param {boolean} isLoading - Whether to show loading state
     */
    setButtonLoading: (btn, isLoading) => {
        btn.disabled = isLoading;
        btn.classList.toggle('opacity-70', isLoading);
    },

    /**
     * Update vote count with animation
     * @param {HTMLElement} btn - The button element containing the count
     * @param {number} count - The new count value
     */
    updateVoteCount: (btn, count) => {
        const countElement = btn.querySelector('.count');
        if (countElement) {
            countElement.classList.add('scale-125', 'text-blue-600');
            countElement.textContent = count;
            setTimeout(() => countElement.classList.remove('scale-125', 'text-blue-600'), 500);
        }
    },

    /**
     * Reset all button styles
     * @param {NodeList} buttons - Collection of buttons to reset
     */
    resetButtonStyles: (buttons) => {
        buttons.forEach(btn => {
            btn.classList.remove(
                'bg-green-50', 'dark:bg-green-900', 'border-green-400', 'text-green-600',
                'bg-red-50', 'dark:bg-red-900', 'border-red-400', 'text-red-600'
            );
        });
    },

    /**
     * Apply selected state to button
     * @param {HTMLElement} btn - The button element
     * @param {boolean} isSelected - Whether the button is selected
     * @param {boolean} isUpvote - Whether it's an upvote (true) or downvote (false)
     */
    setSelectedState: (btn, isSelected, isUpvote) => {
        if (isSelected) {
            const colorClasses = isUpvote ?
                ['bg-green-50', 'dark:bg-green-900', 'border-green-400', 'text-green-600'] :
                ['bg-red-50', 'dark:bg-red-900', 'border-red-400', 'text-red-600'];

            btn.classList.add(...colorClasses);
            btn.setAttribute('aria-pressed', 'true');
        } else {
            btn.setAttribute('aria-pressed', 'false');
        }
    },

    /**
     * Disable all vote buttons
     * @param {HTMLElement} container - The container with buttons
     */
    disableAllButtons: (container) => {
        const buttons = container.querySelectorAll('button');
        buttons.forEach(btn => {
            btn.disabled = true;
            btn.classList.add('opacity-70');
        });
    },

    /**
     * Get appropriate error message based on error type
     * @param {Error} error - The caught error
     * @returns {string} User-friendly error message
     */
    getErrorMessage: (error) => {
        if (error.message.includes('Network')) {
            return "Network error. Please check your connection.";
        } else if (error.message.includes('401') || error.message.includes('403')) {
            return "Please log in to vote on features.";
        } else {
            return "Error recording your vote. Please try again.";
        }
    }
};

// Make the utility functions available globally
window.VoteUtils = VoteUtils;
