/**
 * Version Manager
 * Fetches and displays the latest version from GitHub releases
 */

class VersionManager {
    constructor() {
        this.owner = 'alphaonelabs';
        this.repo = 'alphaonelabs-mockups';
        this.versionElement = document.getElementById('version');
        this.cacheKey = 'wireframe_studio_version';
        this.cacheTimeKey = 'wireframe_studio_version_time';
        this.cacheDuration = 3600000; // 1 hour in milliseconds
    }

    async fetchLatestVersion() {
        // Check cache first
        const cachedVersion = localStorage.getItem(this.cacheKey);
        const cacheTime = localStorage.getItem(this.cacheTimeKey);
        
        if (cachedVersion && cacheTime) {
            const timeSinceCache = Date.now() - parseInt(cacheTime);
            if (timeSinceCache < this.cacheDuration) {
                return cachedVersion;
            }
        }

        // Fetch from API if cache is expired or doesn't exist
        try {
            const response = await fetch(`https://api.github.com/repos/${this.owner}/${this.repo}/releases/latest`);
            if (response.ok) {
                const data = await response.json();
                const version = data.tag_name;
                // Cache the version
                localStorage.setItem(this.cacheKey, version);
                localStorage.setItem(this.cacheTimeKey, Date.now().toString());
                return version;
            } else {
                console.warn('Failed to fetch version from GitHub. Status:', response.status);
                return null;
            }
        } catch (error) {
            console.error('Error fetching version:', error);
            return null;
        }
    }

    async displayVersion() {
        const version = await this.fetchLatestVersion();
        if (version && this.versionElement) {
            this.versionElement.textContent = version;
        } else if (this.versionElement) {
            this.versionElement.textContent = 'v1.0';
        }
    }
}

export default VersionManager;
