// Arsenal Transfer Central - Main JavaScript

class ArsenalTransferHub {
    constructor() {
        this.transferData = null;
        this.filteredRumors = null;
        this.currentFilters = {
            transferType: 'all',
            rumorStrength: 'all',
            position: 'all'
        };
        
        this.init();
    }

    async init() {
        this.showLoading();
        await this.loadTransferData();
        this.renderRumors();
        this.setupEventListeners();
        this.hideLoading();
        this.addPageAnimations();
    }

    showLoading() {
        const loadingSpinner = document.getElementById('loadingSpinner');
        if (loadingSpinner) {
            loadingSpinner.style.display = 'flex';
        }
    }

    hideLoading() {
        const loadingSpinner = document.getElementById('loadingSpinner');
        if (loadingSpinner) {
            loadingSpinner.style.display = 'none';
        }
    }

    async loadTransferData() {
        try {
            // Simulate loading delay for retro feel
            await new Promise(resolve => setTimeout(resolve, 1500));
            
            // Fetch from backend API
            const response = await fetch('http://127.0.0.1:5000/api/rumors');
            if (!response.ok) {
                throw new Error('Failed to load transfer data');
            }
            const apiData = await response.json();
            this.transferData = apiData;
            // Use all Arsenal-related items (rumors and tweets)
            this.filteredRumors = Array.isArray(apiData.data) ? apiData.data : [];
        } catch (error) {
            console.error('Error loading transfer data:', error);
            this.handleDataLoadError();
        }
    }

    handleDataLoadError() {
        const gridContainer = document.querySelector('.grid-container');
        if (gridContainer) {
            gridContainer.innerHTML = `
                <div class="error-message" style="
                    grid-column: 1 / -1;
                    text-align: center;
                    padding: 2rem;
                    background: rgba(220, 20, 60, 0.1);
                    border: 2px solid var(--arsenal-red);
                    border-radius: 8px;
                    color: var(--arsenal-white);
                ">
                    <h3>🚨 Unable to load transfer rumors</h3>
                    <p>Please check your connection and try again.</p>
                    <button onclick="location.reload()" style="
                        background: var(--arsenal-red);
                        color: white;
                        border: none;
                        padding: 0.5rem 1rem;
                        border-radius: 4px;
                        margin-top: 1rem;
                        cursor: pointer;
                    ">Retry</button>
                </div>
            `;
        }
    }

    renderRumors() {
        const gridContainer = document.querySelector('.grid-container');
        if (!gridContainer || !this.filteredRumors) return;

        if (this.filteredRumors.length === 0) {
            gridContainer.innerHTML = `
                <div class="no-results" style="
                    grid-column: 1 / -1;
                    text-align: center;
                    padding: 2rem;
                    color: var(--arsenal-white);
                ">
                    <h3>No Arsenal transfer news found</h3>
                    <p>Try again later or check your connection.</p>
                </div>
            `;
            return;
        }

        // Deduplicate: group by deduplication key (headline/content)
        const deduped = {};
        this.filteredRumors.forEach(item => {
            let key = '';
            if (item.type === 'rumor') {
                key = (item.title || '').trim().toLowerCase();
            } else if (item.type === 'tweet') {
                key = (item.content || '').slice(0, 80).trim().toLowerCase();
            }
            if (!key) return;
            // Prefer the most recent item
            if (!deduped[key] || new Date(item.timestamp) > new Date(deduped[key].timestamp)) {
                deduped[key] = item;
            }
        });
        const dedupedList = Object.values(deduped);

        gridContainer.innerHTML = dedupedList.map(item => this.createRumorCard(item)).join('');
        // Add intersection observer for animations
        this.observeRumorCards();
    }

    createRumorCard(item) {
        // Unified card for both rumors and tweets, no player info section
        const isRumor = item.type === 'rumor';
        const isTweet = item.type === 'tweet';
        const timeAgo = this.formatTimeAgo(item.timestamp || item.date);
        // Headline
        let headline = '';
        if (isRumor) {
            headline = item.title || 'Arsenal Transfer News';
        } else if (isTweet) {
            // Use first sentence or first 80 chars
            const content = item.content || '';
            const firstSentence = content.split(/[.!?\n]/)[0];
            headline = (firstSentence.length > 10 ? firstSentence : content.slice(0, 80)) + (content.length > 80 ? '...' : '');
        }
        // Source only (plain text, no badge, no author)
        let source = 'Unknown';
        if (isRumor) {
            if (item.source && item.source.toLowerCase().includes('sky')) source = 'Sky Sports';
            else if (item.source && item.source.toLowerCase().includes('athletic')) source = 'The Athletic';
            else if (item.source) source = item.source;
        } else if (isTweet) {
            source = item.author || item.author_handle || 'X';
        }
        // Action button
        let actionHtml = '';
        if (isRumor && item.url) {
            actionHtml = `<a href="${item.url}" target="_blank" rel="noopener noreferrer" class="source-link">📰 Read Article</a>`;
        } else if (isTweet && item.url) {
            actionHtml = `<a href="${item.url}" target="_blank" rel="noopener noreferrer" class="x-link">
                <img src="static/images/X_logo.svg" alt="X logo" class="x-logo">View on X
            </a>`;
        }
        // Card HTML
        return `
            <div class="rumor-card" data-rumor-id="${item.id || item.url || ''}">
                <h3 class="rumor-headline" style="font-weight:bold;">${headline}</h3>
                <div class="rumor-footer" style="display:flex;justify-content:flex-start;align-items:center;gap:0.5rem;margin-top:1rem;">
                    <span class="source-text">${source}</span>
                </div>
                <div class="rumor-links" style="margin-top:0.5rem;">
                    ${actionHtml}
                </div>
                <div class="rumor-meta" style="margin-top:0.5rem;">
                    <span class="time-ago">${timeAgo}</span>
                </div>
            </div>
        `;
    }

    getRumorStrengthLabel(strength) {
        if (!strength) return 'UNKNOWN';
        const labels = {
            'confirmed': 'CONFIRMED',
            'likely': 'LIKELY',
            'speculation': 'SPECULATION'
        };
        return labels[strength.toLowerCase()] || strength.toUpperCase();
    }

    getTransferTypeLabel(type) {
        if (!type) return 'UNKNOWN';
        const labels = {
            'incoming': 'IN',
            'outgoing': 'OUT',
            'contract_extension': 'CONTRACT'
        };
        return labels[type] || type.toUpperCase();
    }

    setupEventListeners() {
        // Filter toggle button
        const filterToggle = document.getElementById('filterToggle');
        const filterModal = document.getElementById('filterModal');
        const closeModal = document.querySelector('.close-modal');
        const applyFiltersBtn = document.querySelector('.apply-filters-btn');

        if (filterToggle) {
            filterToggle.addEventListener('click', () => {
                filterModal.style.display = 'flex';
            });
        }

        if (closeModal) {
            closeModal.addEventListener('click', () => {
                filterModal.style.display = 'none';
            });
        }

        if (filterModal) {
            filterModal.addEventListener('click', (e) => {
                if (e.target === filterModal) {
                    filterModal.style.display = 'none';
                }
            });
        }

        if (applyFiltersBtn) {
            applyFiltersBtn.addEventListener('click', () => {
                this.applyFilters();
                filterModal.style.display = 'none';
            });
        }

        // Smooth scrolling for navigation
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {
            anchor.addEventListener('click', (e) => {
                e.preventDefault();
                const target = document.querySelector(anchor.getAttribute('href'));
                if (target) {
                    target.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                }
            });
        });

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && filterModal.style.display === 'flex') {
                filterModal.style.display = 'none';
            }
            if (e.ctrlKey && e.key === 'f') {
                e.preventDefault();
                filterToggle.click();
            }
        });

        // Auto-refresh simulation (every 30 seconds in a real app)
        this.setupAutoRefresh();
    }

    applyFilters() {
        const transferTypeFilter = document.getElementById('transferTypeFilter');
        const rumorStrengthFilter = document.getElementById('rumorStrengthFilter');
        const positionFilter = document.getElementById('positionFilter');

        this.currentFilters = {
            transferType: transferTypeFilter?.value || 'all',
            rumorStrength: rumorStrengthFilter?.value || 'all',
            position: positionFilter?.value || 'all'
        };

        // Filter rumors from the API data
        this.filteredRumors = Array.isArray(this.transferData.data) ? this.transferData.data.filter(rumor => {
            if (!rumor.title) return false; // Only rumors, not tweets
            const matchesType = this.currentFilters.transferType === 'all' || 
                              rumor.rumor_type === this.currentFilters.transferType;
            const matchesStrength = this.currentFilters.rumorStrength === 'all' || 
                                  rumor.rumor_strength === this.currentFilters.rumorStrength;
            const matchesPosition = this.currentFilters.position === 'all' || 
                                  rumor.position === this.currentFilters.position;
            return matchesType && matchesStrength && matchesPosition;
        }) : [];

        this.renderRumors();
        this.showFilterNotification();
    }

    showFilterNotification() {
        const notification = document.createElement('div');
        notification.className = 'filter-notification';
        notification.style.cssText = `
            position: fixed;
            top: 100px;
            right: 20px;
            background: var(--arsenal-red);
            color: white;
            padding: 1rem;
            border-radius: 8px;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
            z-index: 1001;
            transform: translateX(300px);
            transition: transform 0.3s ease;
        `;
        notification.innerHTML = `
            <strong>Filters Applied!</strong><br>
            Found ${this.filteredRumors.length} rumors
        `;

        document.body.appendChild(notification);

        // Animate in
        setTimeout(() => {
            notification.style.transform = 'translateX(0)';
        }, 100);

        // Remove after 3 seconds
        setTimeout(() => {
            notification.style.transform = 'translateX(300px)';
            setTimeout(() => {
                document.body.removeChild(notification);
            }, 300);
        }, 3000);
    }

    setupAutoRefresh() {
        // Simulate live updates in a real application
        setInterval(() => {
            this.simulateNewRumor();
        }, 45000); // Every 45 seconds for demo
    }

    simulateNewRumor() {
        if (!this.transferData) return;

        // Add a visual indicator for new content
        const hero = document.querySelector('.hero-section');
        if (hero) {
            const indicator = document.createElement('div');
            indicator.style.cssText = `
                position: absolute;
                top: 10px;
                right: 10px;
                background: var(--arsenal-gold);
                color: var(--arsenal-red);
                padding: 0.5rem;
                border-radius: 20px;
                font-size: 0.8rem;
                font-weight: bold;
                animation: pulse 2s infinite;
            `;
            indicator.textContent = 'NEW RUMORS AVAILABLE';
            hero.appendChild(indicator);

            setTimeout(() => {
                if (hero.contains(indicator)) {
                    hero.removeChild(indicator);
                }
            }, 5000);
        }
    }

    observeRumorCards() {
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.style.opacity = '1';
                    entry.target.style.transform = 'translateY(0)';
                }
            });
        }, { threshold: 0.1 });

        document.querySelectorAll('.rumor-card').forEach((card, index) => {
            card.style.opacity = '0';
            card.style.transform = 'translateY(30px)';
            card.style.transition = `opacity 0.6s ease ${index * 0.1}s, transform 0.6s ease ${index * 0.1}s`;
            observer.observe(card);
        });
    }

    addPageAnimations() {
        // Add CSS animations
        const style = document.createElement('style');
        style.textContent = `
            @keyframes pulse {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.7; }
            }
            
            @keyframes fadeInUp {
                from {
                    opacity: 0;
                    transform: translateY(30px);
                }
                to {
                    opacity: 1;
                    transform: translateY(0);
                }
            }
            
            .hero-section {
                animation: fadeInUp 0.8s ease;
            }
            
            .section-title {
                animation: fadeInUp 1s ease 0.2s both;
            }
        `;
        document.head.appendChild(style);
    }

    formatTimeAgo(dateString) {
        const date = new Date(dateString);
        const now = new Date();
        const diffInSeconds = Math.floor((now - date) / 1000);

        if (diffInSeconds < 60) return 'Just now';
        if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)}m ago`;
        if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)}h ago`;
        if (diffInSeconds < 604800) return `${Math.floor(diffInSeconds / 86400)}d ago`;
        
        return date.toLocaleDateString();
    }

    // Utility methods for enhanced functionality
    shareRumor(rumorId) {
        const rumor = this.transferData.latest_rumors.find(r => r.id === rumorId);
        if (rumor && navigator.share) {
            navigator.share({
                title: rumor.headline,
                text: rumor.summary,
                url: window.location.href
            });
        } else {
            // Fallback for browsers without Web Share API
            this.copyToClipboard(`${rumor.headline}\n\n${rumor.summary}\n\nSource: ${rumor.source}`);
        }
    }

    copyToClipboard(text) {
        navigator.clipboard.writeText(text).then(() => {
            this.showNotification('Link copied to clipboard!');
        });
    }

    showNotification(message) {
        const notification = document.createElement('div');
        notification.textContent = message;
        notification.style.cssText = `
            position: fixed;
            bottom: 100px;
            right: 20px;
            background: var(--arsenal-green);
            color: white;
            padding: 1rem;
            border-radius: 8px;
            z-index: 1002;
        `;
        document.body.appendChild(notification);
        
        setTimeout(() => {
            document.body.removeChild(notification);
        }, 3000);
    }
}

// Error handling
window.addEventListener('error', (e) => {
    console.error('JavaScript error:', e.error);
});

window.addEventListener('unhandledrejection', (e) => {
    console.error('Unhandled promise rejection:', e.reason);
});

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    const app = new ArsenalTransferHub();
    
    // Make app globally available for debugging
    window.arsenalApp = app;
});

// Service Worker registration for offline functionality (future enhancement)
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        // navigator.serviceWorker.register('/sw.js'); // Uncomment when implementing PWA features
    });
}

// Analytics and performance monitoring (placeholder)
class PerformanceMonitor {
    static trackPageLoad() {
        window.addEventListener('load', () => {
            const loadTime = performance.now();
            console.log(`Page loaded in ${loadTime.toFixed(2)}ms`);
        });
    }
    
    static trackUserInteraction(eventType, element) {
        // Track user interactions for analytics
        console.log(`User interaction: ${eventType} on ${element}`);
    }
}

PerformanceMonitor.trackPageLoad();

async function fetchAndDisplayRumors() {
    const rumorsGrid = document.querySelector('.grid-container'); // or your rumors grid container
    rumorsGrid.innerHTML = '<div>Loading...</div>';
    try {
        const response = await fetch('http://127.0.0.1:5000/api/rumors');
        if (!response.ok) throw new Error('Failed to fetch rumors');
        const result = await response.json();
        rumorsGrid.innerHTML = '';
        const hub = new ArsenalTransferHub();
        result.data.forEach(item => {
            let cardHtml = '';
            if (item.source === 'Sky Sports') {
                // Map backend fields to your frontend card fields
                cardHtml = hub.createRumorCard({
                    id: item.url, // or a unique id
                    rumor_strength: "default", // or map from item if available
                    transfer_type: item.rumor_type || "in",
                    headline: item.title,
                    player: item.player_name || "N/A",
                    position: item.position || "N/A",
                    current_club: item.current_club || "N/A",
                    contract_until: item.contract_until || "N/A",
                    estimated_fee: item.transfer_fee || "N/A",
                    reliability_score: item.reliability_score || 5,
                    summary: item.content || "",
                    source: item.source,
                    journalist: item.journalist || "",
                    source_url: item.url,
                    twitter_url: "",
                    twitter_activity: 0,
                    date: item.timestamp
                });
            } else if (item.source === 'Twitter') {
                // Render as a tweet card (use your tweet card system or a simple fallback)
                cardHtml = `
                    <div class="tweet-card">
                        <div class="tweet-header">
                            <span class="journalist-name">${item.author}</span>
                            <span class="journalist-handle">@${item.author_handle}</span>
                        </div>
                        <div class="tweet-content">${item.content}</div>
                        <div class="tweet-stats">
                            <span>❤️ ${item.likes}</span>
                            <span>🔁 ${item.retweets}</span>
                            <span>💬 ${item.replies}</span>
                        </div>
                        <div class="tweet-actions">
                            <a href="${item.url}" target="_blank" class="view-tweet-btn">View Tweet</a>
                        </div>
                        <div class="tweet-meta">
                            <span>${new Date(item.timestamp).toLocaleString()}</span>
                        </div>
                    </div>
                `;
            }
            rumorsGrid.innerHTML += cardHtml;
        });
        // Re-apply any card animations/intersection observers
        if (hub.observeRumorCards) hub.observeRumorCards();
    } catch (error) {
        rumorsGrid.innerHTML = '<div>Error loading rumors.</div>';
        console.error(error);
    }
}

window.addEventListener('DOMContentLoaded', fetchAndDisplayRumors);
