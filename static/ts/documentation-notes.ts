/**
 * Documentation Notes UI Module
 * Handles section navigation, highlighting, and smooth scrolling
 */

interface SectionData {
    slug: string;
    title: string;
    element?: HTMLElement;
}

interface DocumentationConfig {
    topicSlug: string;
    sections: SectionData[];
    currentSectionSlug: string;
}

class DocumentationNotes {
    private config: DocumentationConfig;
    private currentSection: string;
    private sections: Map<string, SectionData> = new Map();

    constructor(config: DocumentationConfig) {
        this.config = config;
        this.currentSection = config.currentSectionSlug;
        this.initializeSections();
        this.attachEventListeners();
        this.updateActiveSection();
    }

    /**
     * Initialize sections map from config
     */
    private initializeSections(): void {
        this.config.sections.forEach((section) => {
            this.sections.set(section.slug, section);
        });
    }

    /**
     * Attach event listeners to navigation elements
     */
    private attachEventListeners(): void {
        // Sidebar section links
        document.querySelectorAll('[data-section-link]').forEach((link) => {
            link.addEventListener('click', (e) => this.onSectionLinkClick(e));
        });

        // Previous/Next buttons
        const prevBtn = document.querySelector('[data-nav-prev]');
        const nextBtn = document.querySelector('[data-nav-next]');

        if (prevBtn) {
            prevBtn.addEventListener('click', () => this.goToPreviousSection());
        }

        if (nextBtn) {
            nextBtn.addEventListener('click', () => this.goToNextSection());
        }

        // Use event delegation for anchor links (works for dynamically added content)
        document.addEventListener('click', (e) => {
            const link = (e.target as HTMLElement).closest('a[href^="#"]');
            if (link) {
                this.onAnchorClick(e as MouseEvent);
            }
        });
    }

    /**
     * Handle section link click from sidebar
     */
    private onSectionLinkClick(event: Event): void {
        const link = event.currentTarget as HTMLAnchorElement;
        const sectionSlug = link.dataset.sectionLink;

        if (sectionSlug) {
            event.preventDefault();
            this.navigateToSection(sectionSlug);
        }
    }

    /**
     * Handle anchor link clicks for smooth scrolling
     */
    private onAnchorClick(event: Event): void {
        const link = event.currentTarget as HTMLAnchorElement;
        const href = link.getAttribute('href');

        if (href?.startsWith('#')) {
            event.preventDefault();
            const element = document.querySelector(href);
            if (element) {
                this.smoothScroll(element);
            }
        }
    }

    /**
     * Navigate to a specific section
     */
    public navigateToSection(sectionSlug: string): void {
        const section = this.sections.get(sectionSlug);
        if (!section) return;

        this.currentSection = sectionSlug;
        this.updateActiveSection();
        this.loadSectionContent(sectionSlug);
    }

    /**
     * Go to previous section
     */
    public goToPreviousSection(): void {
        const sectionArray = Array.from(this.sections.values());
        const currentIndex = sectionArray.findIndex((s) => s.slug === this.currentSection);

        if (currentIndex > 0) {
            this.navigateToSection(sectionArray[currentIndex - 1].slug);
        }
    }

    /**
     * Go to next section
     */
    public goToNextSection(): void {
        const sectionArray = Array.from(this.sections.values());
        const currentIndex = sectionArray.findIndex((s) => s.slug === this.currentSection);

        if (currentIndex < sectionArray.length - 1) {
            this.navigateToSection(sectionArray[currentIndex + 1].slug);
        }
    }

    /**
     * Update active section highlighting
     */
    private updateActiveSection(): void {
        // Remove active state from all sidebar items
        document.querySelectorAll('[data-section-link]').forEach((item) => {
            item.classList.remove(
                'bg-teal-50',
                'dark:bg-teal-900/20',
                'text-teal-700',
                'dark:text-teal-300',
                'font-semibold',
                'border-l-teal-500'
            );
            item.classList.add('text-gray-700', 'dark:text-gray-300', 'border-l-transparent');
        });

        // Add active state to current section
        const activeLink = document.querySelector(`[data-section-link="${this.currentSection}"]`);
        if (activeLink) {
            activeLink.classList.remove('text-gray-700', 'dark:text-gray-300', 'border-l-transparent');
            activeLink.classList.add(
                'bg-teal-50',
                'dark:bg-teal-900/20',
                'text-teal-700',
                'dark:text-teal-300',
                'font-semibold'
            );
        }

        // Update progress counter
        this.updateProgressCounter();
    }

    /**
     * Load section content via AJAX
     */
    private async loadSectionContent(sectionSlug: string): Promise<void> {
        try {
            const url = `/docs/${this.config.topicSlug}/${sectionSlug}/`;
            const response = await fetch(url);

            if (!response.ok) throw new Error('Failed to load section');

            const html = await response.text();
            const parser = new DOMParser();
            const doc = parser.parseFromString(html, 'text/html');
            const newContent = doc.querySelector('[data-doc-content]');

            if (newContent) {
                const contentArea = document.querySelector('[data-doc-content]');
                if (contentArea) {
                    contentArea.innerHTML = newContent.innerHTML;
                    contentArea.scrollIntoView({ behavior: 'smooth', block: 'start' });

                    // Re-render markdown if needed
                    this.renderMarkdown(contentArea);
                    // Mark section as viewed
                    this.markSectionViewed(sectionSlug);
                }
            }
        } catch (error) {
            console.error('Error loading section:', error);
        }
    }

    /**
     * Mark section as viewed in the backend
     */
    private async markSectionViewed(sectionSlug: string): Promise<void> {
        try {
            // Get CSRF token from meta tag (cookie-based) or form input
            let csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
            if (!csrfToken) {
                const csrfInput = document.querySelector('input[name="csrfmiddlewaretoken"]') as HTMLInputElement;
                csrfToken = csrfInput?.value;
            }
            if (!csrfToken) return;

            const url = `/docs/${this.config.topicSlug}/section/${sectionSlug}/viewed/`;
            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrfToken,
                    'Content-Type': 'application/json',
                },
            });

            if (response.ok) {
                const data = await response.json();
                this.updateProgressBar(data.completion_percentage);
            }
        } catch (error) {
            console.error('Error marking section as viewed:', error);
        }
    }

    /**
     * Update progress bar
     */
    private updateProgressBar(percentage: number): void {
        const progressBar = document.querySelector('[data-progress-bar]') as HTMLElement;
        if (progressBar) {
            const bar = progressBar.querySelector('div') as HTMLElement;
            if (bar) {
                bar.style.width = `${percentage}%`;
            }
        }
    }

    /**
     * Update progress counter (e.g., "2 / 6")
     */
    private updateProgressCounter(): void {
        const counter = document.querySelector('[data-progress-counter]');
        if (counter) {
            const sectionArray = Array.from(this.sections.values());
            const currentIndex = sectionArray.findIndex((s) => s.slug === this.currentSection);
            counter.textContent = `${currentIndex + 1} / ${sectionArray.length}`;
        }
    }

    /**
     * Render markdown content
     */
    private renderMarkdown(element: Element): void {
        if (!(window as any).marked) return;

        // Look for both doc-markdown divs (AJAX loaded content)
        const markdownContainers = element.querySelectorAll('.doc-markdown');
        markdownContainers.forEach((el) => {
            // Find corresponding markdown source (usually next to or parent sibling)
            const parent = el.parentElement;
            const markdownSource = parent?.querySelector('#doc-markdown-source');
            if (markdownSource) {
                const content = markdownSource.textContent;
                if (content && (content as any).trim()) {
                    (el as any).innerHTML = (window as any).marked.parse(content).replace(/&lt;script/gi, '&amp;lt;script').replace(/&lt;iframe/gi, '&amp;lt;iframe').replace(/&lt;object/gi, '&amp;lt;object');
                }
            }
        });

        // Render LaTeX if MathJax is available
        if ((window as any).MathJax) {
            (window as any).MathJax.typesetPromise([element]).catch((err: any) => console.log(err));
        }
    }

    /**
     * Smooth scroll to element
     */
    private smoothScroll(element: Element): void {
        element.scrollIntoView({
            behavior: 'smooth',
            block: 'start',
        });
    }

    /**
     * Get current section slug
     */
    public getCurrentSection(): string {
        return this.currentSection;
    }

    /**
     * Get all sections
     */
    public getSections(): SectionData[] {
        return Array.from(this.sections.values());
    }
}

/**
 * Initialize documentation notes when DOM is ready
 */
export function initializeDocumentationNotes(config: DocumentationConfig): DocumentationNotes {
    return new DocumentationNotes(config);
}

// Export for use in global scope
(window as any).initializeDocumentationNotes = initializeDocumentationNotes;
