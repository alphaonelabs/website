/**
 * Version Manager
 * Fetches and displays the latest version from GitHub releases
 */

class VersionManager {
    constructor() {
        this.owner = 'alphaonelabs';
        this.repo = 'alphaonelabs-mockups';
        this.versionElement = document.getElementById('version');
    }

    async fetchLatestVersion() {
        try {
            const response = await fetch(`https://api.github.com/repos/${this.owner}/${this.repo}/releases/latest`);
            if (response.ok) {
                const data = await response.json();
                return data.tag_name;
            } else {
                console.warn('Failed to fetch version from GitHub');
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
