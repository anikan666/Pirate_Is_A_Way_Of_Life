/**
 * Pirate Lab - Launcher JavaScript
 * Handles modal/lightbox functionality for loading experiments in iframes
 */

(function () {
    'use strict';

    // ==========================================
    // DOM ELEMENTS
    // ==========================================

    const modal = document.getElementById('experiment-modal');
    const modalBackdrop = document.getElementById('modal-backdrop');
    const modalContainer = document.getElementById('modal-container');
    const modalTitle = document.getElementById('modal-title');
    const modalIframe = document.getElementById('modal-iframe');
    const modalLoading = document.getElementById('modal-loading');

    // ==========================================
    // STATE
    // ==========================================

    let isModalOpen = false;
    let currentExperimentId = null;

    // ==========================================
    // MODAL FUNCTIONS
    // ==========================================

    /**
     * Open the experiment modal with an iframe
     * @param {string} experimentId - The experiment ID
     * @param {string} url - The URL to load in the iframe
     * @param {string} name - The experiment name for the title
     */
    window.openExperimentModal = function (experimentId, url, name) {
        if (isModalOpen || !url || url === '#') return;

        isModalOpen = true;
        currentExperimentId = experimentId;

        // Update modal content
        modalTitle.textContent = name || 'Loading...';
        modalIframe.src = '';
        modalLoading.classList.remove('loaded');

        // Show modal with animation
        modal.classList.remove('hidden');

        // Trigger reflow for animation
        void modal.offsetWidth;

        modal.classList.add('modal-open');

        // Lock body scroll
        document.body.style.overflow = 'hidden';

        // Load iframe after modal animation starts
        setTimeout(() => {
            modalIframe.src = url;
        }, 100);

        // Handle iframe load
        modalIframe.onload = function () {
            modalLoading.classList.add('loaded');
        };

        // Track in URL (optional - for deep linking)
        history.pushState({ experimentId }, '', `#${experimentId}`);
    };

    /**
     * Close the experiment modal
     */
    window.closeExperimentModal = function () {
        if (!isModalOpen) return;

        isModalOpen = false;
        currentExperimentId = null;

        // Hide modal with animation
        modal.classList.remove('modal-open');

        // Cleanup after animation
        setTimeout(() => {
            modal.classList.add('hidden');
            modalIframe.src = '';
            modalTitle.textContent = '';
        }, 300);

        // Unlock body scroll
        document.body.style.overflow = '';

        // Clear URL hash
        if (window.location.hash) {
            history.pushState(null, '', window.location.pathname);
        }
    };

    /**
     * Handle card click - reads data from data attributes to avoid apostrophe issues
     * @param {HTMLElement} cardElement - The clicked card element
     */
    window.handleCardClick = function (cardElement) {
        const experimentId = cardElement.dataset.experimentId;
        const url = cardElement.dataset.experimentUrl;
        const name = cardElement.dataset.experimentName;

        if (experimentId && url && url !== '#') {
            openExperimentModal(experimentId, url, name);
        }
    };

    // ==========================================
    // EVENT LISTENERS
    // ==========================================

    // Keyboard shortcuts
    document.addEventListener('keydown', function (e) {
        // ESC to close modal
        if (e.key === 'Escape' && isModalOpen) {
            e.preventDefault();
            closeExperimentModal();
        }
    });

    // Handle browser back/forward navigation
    window.addEventListener('popstate', function (e) {
        if (isModalOpen && !e.state?.experimentId) {
            closeExperimentModal();
        } else if (!isModalOpen && e.state?.experimentId) {
            // Re-open modal if navigating forward to an experiment
            const card = document.querySelector(`[data-experiment-id="${e.state.experimentId}"]`);
            if (card) {
                const url = card.dataset.experimentUrl;
                const name = card.querySelector('h3')?.textContent;
                openExperimentModal(e.state.experimentId, url, name);
            }
        }
    });

    // Handle deep linking on page load
    document.addEventListener('DOMContentLoaded', function () {
        const hash = window.location.hash.slice(1);
        if (hash) {
            const card = document.querySelector(`[data-experiment-id="${hash}"]`);
            if (card && card.dataset.experimentStatus === 'live') {
                const url = card.dataset.experimentUrl;
                const name = card.querySelector('h3')?.textContent;
                // Delay slightly for smoother initial load
                setTimeout(() => {
                    openExperimentModal(hash, url, name);
                }, 300);
            }
        }

        // Add subtle entrance animation to cards
        const cards = document.querySelectorAll('.experiment-card');
        cards.forEach((card, index) => {
            card.style.opacity = '0';
            card.style.transform = 'translateY(20px)';
            card.style.transition = 'opacity 0.5s ease, transform 0.5s ease';

            setTimeout(() => {
                card.style.opacity = '1';
                card.style.transform = 'translateY(0)';
            }, 100 + (index * 100));
        });
    });

    // ==========================================
    // UTILITY FUNCTIONS
    // ==========================================

    /**
     * Handle message events from iframe (for cross-origin communication)
     */
    window.addEventListener('message', function (e) {
        // Only handle messages from our own iframes
        if (e.data?.type === 'pirate-lab-close') {
            closeExperimentModal();
        }
    });

    // Log initialization
    console.log('🏴‍☠️ Pirate Lab Launcher initialized');

})();
