// All For Gooners - Main JavaScript
console.log('Supabase loaded:', typeof window.supabase);

// Create Supabase client - Fixed the circular reference issue
const supabaseClient = window.supabase.createClient(
    'https://szchuafsdtigbuxezrbu.supabase.co', 
    'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InN6Y2h1YWZzZHRpZ2J1eGV6cmJ1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTA5NTY3MDYsImV4cCI6MjA2NjUzMjcwNn0.19rFV1D0wv85gWXygef8LMHHD5W0Iu3Tkfmac_pwSyw'
);

class AllForGooners {
    constructor() {
        this.transferData = null;
        this.filteredNews = null;
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
        this.renderNews();
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
    
            // Fetch from Supabase - using the fixed client
            const { data, error } = await supabaseClient
                .from('transfer_news')
                .select('*')
                .order('published_at', { ascending: false });
    
            if (error) {
                throw error;
            }
    
            this.transferData = data;
            this.filteredNews = Array.isArray(data) ? data : [];
            console.log('Fetched news:', this.transferData);
            console.log('Filtered news:', this.filteredNews);
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
                    <h3>🚨 Unable to load transfer news</h3>
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

    renderNews() {
        const gridContainer = document.querySelector('.grid-container');
        console.log('Rendering news:', this.filteredNews);
        if (!gridContainer || !this.filteredNews) return;
    
        if (this.filteredNews.length === 0) {
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
    
        // Deduplicate: group by deduplication key (headline/title)
        const deduped = {};
        this.filteredNews.forEach(item => {
            let key = (item.headline || item.title || '').trim().toLowerCase();
            if (!key) return;
            // Prefer the most recent item
            if (!deduped[key] || new Date(item.published_at) > new Date(deduped[key].published_at)) {
                deduped[key] = item;
            }
        });
        const dedupedList = Object.values(deduped);
    
        gridContainer.innerHTML = dedupedList.map(item => this.createNewsCard(item)).join('');
        // Add intersection observer for animations
        this.observeNewsCards();
    }

    createNewsCard(item) {
        // Use headline as the main headline
        console.log('Rendering card for:', item);
        const headline = item.headline || 'All For Gooners';
        const source = item.source || 'Unknown';
        const url = item.url || '#';
        const image = item.image_url ? `<img src="${item.image_url}" alt="${headline}" class="news-image" style="max-width:100%;max-height:180px;object-fit:cover;border-radius:8px;margin-bottom:1rem;">` : '';
        const summary = item.news_summary || '';
        const publishedAt = item.published_at ? this.formatTimeAgo(item.published_at) : '';
        const buttonLabel = (source.toLowerCase().includes('twitter') || source.toLowerCase().includes('x'))
            ? 'View on X'
            : 'Read Article';
        const buttonClass = buttonLabel === 'View on X' ? 'x-link' : 'source-link';
        const buttonIcon = buttonLabel === 'View on X'
            ? `<img src="static/images/X_logo.svg" alt="X logo" class="x-logo">`
            : '📰 ';
    
        return `
            <div class="news-card" data-news-id="${item.id || url}">
                ${image}
                <h3 class="rumor-headline" style="font-weight:bold;">${headline}</h3>
                <div class="news-summary" style="margin-top:1rem;">${summary}</div>
                <div class="news-footer" style="display:flex;justify-content:flex-start;align-items:center;gap:0.5rem;margin-top:1rem;">
                    <span class="source-text">${source}</span>
                </div>
                <div class="news-links" style="margin-top:0.5rem;">
                    <a href="${url}" target="_blank" rel="noopener noreferrer" class="${buttonClass}">
                        ${buttonIcon}${buttonLabel}
                    </a>
                </div>
                <div class="news-meta" style="margin-top:0.5rem;">
                    <span class="time-ago">${publishedAt}</span>
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

        // Filter news from the API data - Fixed the data structure reference
        this.filteredNews = Array.isArray(this.transferData) ? this.transferData.filter(news => {
            if (!news.title && !news.headline) return false; // Only valid news items
            const matchesType = this.currentFilters.transferType === 'all' || 
                              news.rumor_type === this.currentFilters.transferType;
            const matchesStrength = this.currentFilters.rumorStrength === 'all' || 
                                  news.rumor_strength === this.currentFilters.rumorStrength;
            const matchesPosition = this.currentFilters.position === 'all' || 
                                  news.position === this.currentFilters.position;
            return matchesType && matchesStrength && matchesPosition;
        }) : [];

        this.renderNews();
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
            Found ${this.filteredNews.length} news
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
                if (document.body.contains(notification)) {
                    document.body.removeChild(notification);
                }
            }, 300);
        }, 3000);
    }

    setupAutoRefresh() {
        // Simulate live updates in a real application
        setInterval(() => {
            this.simulateNewNews();
        }, 45000); // Every 45 seconds for demo
    }

    simulateNewNews() {
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
            indicator.textContent = 'NEW NEWS AVAILABLE';
            hero.appendChild(indicator);

            setTimeout(() => {
                if (hero.contains(indicator)) {
                    hero.removeChild(indicator);
                }
            }, 5000);
        }
    }

    observeNewsCards() {
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.style.opacity = '1';
                    entry.target.style.transform = 'translateY(0)';
                }
            });
        }, { threshold: 0.1 });

        document.querySelectorAll('.news-card').forEach((card, index) => {
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
        if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)}h ago`;
        if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)}h ago`;
        if (diffInSeconds < 604800) return `${Math.floor(diffInSeconds / 86400)}d ago`;
        return date.toLocaleDateString();
    }

    // Utility methods for enhanced functionality
    shareNews(newsId) {
        const news = this.transferData.find(r => r.id === newsId);
        if (news && navigator.share) {
            navigator.share({
                title: news.headline || news.title,
                text: news.summary || news.news_summary,
                url: window.location.href
            });
        } else if (news) {
            // Fallback for browsers without Web Share API
            this.copyToClipboard(`${news.headline || news.title}\n\n${news.summary || news.news_summary}\n\nSource: ${news.source}`);
        }
    }

    copyToClipboard(text) {
        navigator.clipboard.writeText(text).then(() => {
            this.showNotification('Link copied to clipboard!');
        }).catch(() => {
            // Fallback for older browsers
            const textArea = document.createElement('textarea');
            textArea.value = text;
            document.body.appendChild(textArea);
            textArea.select();
            document.execCommand('copy');
            document.body.removeChild(textArea);
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
            if (document.body.contains(notification)) {
                document.body.removeChild(notification);
            }
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
    // Wait for Supabase to be fully loaded
    if (typeof window.supabase !== 'undefined') {
        const app = new AllForGooners();
        // Make app globally available for debugging
        window.allForGoonersApp = app;
    } else {
        console.error('Supabase not loaded. Please check your internet connection.');
        // Show error message to user
        document.body.innerHTML += `
            <div style="
                position: fixed;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                background: #DC143C;
                color: white;
                padding: 2rem;
                border-radius: 8px;
                text-align: center;
                z-index: 9999;
            ">
                <h3>Connection Error</h3>
                <p>Unable to load the application. Please check your internet connection and reload the page.</p>
                <button onclick="location.reload()" style="
                    background: white;
                    color: #DC143C;
                    border: none;
                    padding: 0.5rem 1rem;
                    border-radius: 4px;
                    margin-top: 1rem;
                    cursor: pointer;
                ">Reload Page</button>
            </div>
        `;
    }
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