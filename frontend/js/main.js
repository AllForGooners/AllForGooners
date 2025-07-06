// All For Gooners - Main JavaScript
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
        this.setupNewsTicker();
        this.hideLoading();
        this.addPageAnimations();
        
        // Show the new news notification for testing
        setTimeout(() => {
            this.simulateNewNews();
        }, 2000);

        // Add intersection observer for animations
        this.observeNewsCards();
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
    
            // Fetch from Supabase
            const { data, error } = await supabaseClient
                .from('transfer_news')
                .select('*')
                .order('published_at', { ascending: false });
    
            if (error) {
                throw error;
            }
    
            this.transferData = data;
            this.filteredNews = Array.isArray(data) ? data : [];
        } catch (error) {
            console.error('Error loading transfer data:', error);
            this.handleDataLoadError();
        }
    }

    handleDataLoadError() {
        const gridContainer = document.querySelector('.grid-container');
        if (gridContainer) {
            gridContainer.innerHTML = `
                <div class="rumors__error-message" role="alert">
                    <h3>🚨 Unable to load transfer news</h3>
                    <p>Please check your connection and try again.</p>
                    <button onclick="location.reload()" class="rumors__error-retry-btn">Retry</button>
                </div>
            `;
        }
    }

    renderNews() {
        const gridContainer = document.querySelector('.grid-container');
        if (!gridContainer || !this.filteredNews) return;

        gridContainer.style.gridTemplateColumns = '';

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
            let key = (item.headline || '').trim().toLowerCase();
            if (!key) return;
            // Prefer the most recent item
            if (!deduped[key] || new Date(item.published_at) > new Date(deduped[key].published_at)) {
                deduped[key] = item;
            }
        });
        const dedupedList = Object.values(deduped);

        gridContainer.innerHTML = dedupedList.map(item => this.createNewsCard(item)).join('');
    }

    createNewsCard(article) {
        const headline = article.headline || 'All For Gooners';
        const source = article.source_name || 'Unknown';
        const url = article.url || '#';
        
        const imageUrl = article.image_url || 'images/arsenal-logo.png';
        
        const summary = article.news_summary || '';
        const publishedAt = article.published_at ? this.timeAgo(article.published_at) : '';
        const isTwitterSource = source === 'Fabrizio Romano' || source === 'David Ornstein';
        const buttonLabel = isTwitterSource ? 'View on X' : 'Read Article';
        const buttonClass = buttonLabel === 'View on X' ? 'x-link' : 'source-link';
        const buttonIcon = buttonLabel === 'View on X'
            ? `<img src="images/X_logo.svg" alt="X logo" class="x-logo">`
            : '📰 ';
    
        return `
            <div class="news-card" data-news-id="${article.id || url}">
                <div class="news-content">
                    <h2 class="news-headline">${headline}</h2>
                    <img src="${imageUrl}" alt="${headline}" class="news-image" onerror="this.onerror=null;this.src='images/arsenal-logo.png';">
                    <p class="news-summary">${summary}</p>
                    <div class="news-footer">
                        <div class="news-card__source-info">
                            <span class="source-text">${source}</span>
                            <a href="${url}" target="_blank" rel="noopener noreferrer" class="${buttonClass}">
                                ${buttonIcon}${buttonLabel}
                            </a>
                        </div>
                        <span class="news-meta">${publishedAt}</span>
                    </div>
                </div>
            </div>
        `;
    }

    timeAgo(dateString) {
        const date = new Date(dateString);
        const now = new Date();
        const diffInSeconds = Math.floor((now - date) / 1000);

        if (diffInSeconds < 60) return 'Just now';
        if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)}m ago`;
        if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)}h ago`;
        if (diffInSeconds < 604800) return `${Math.floor(diffInSeconds / 86400)}d ago`;
        return date.toLocaleDateString();
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

        // Modal accessibility: trap focus and ARIA
        if (filterModal) {
            filterModal.setAttribute('role', 'dialog');
            filterModal.setAttribute('aria-modal', 'true');
            filterModal.setAttribute('aria-labelledby', 'filterModalTitle');
            
            filterModal.addEventListener('keydown', (e) => {
                if (e.key === 'Tab') {
                    const focusableEls = filterModal.querySelectorAll('button, [tabindex]:not([tabindex="-1"]), select');
                    const firstEl = focusableEls[0];
                    const lastEl = focusableEls[focusableEls.length - 1];
                    if (e.shiftKey) {
                        if (document.activeElement === firstEl) {
                            e.preventDefault();
                            lastEl.focus();
                        }
                    } else {
                        if (document.activeElement === lastEl) {
                            e.preventDefault();
                            firstEl.focus();
                        }
                    }
                }
            });
        }
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

        this.filteredNews = Array.isArray(this.transferData) ? this.transferData.filter(news => {
            if (!news.title && !news.headline) return false;
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
        notification.className = 'rumors__notification';
        notification.setAttribute('role', 'status');
        notification.setAttribute('aria-live', 'polite');
        notification.tabIndex = 0;
        notification.innerHTML = `
            <strong>Filters Applied!</strong><br>
            Found ${this.filteredNews.length} news
        `;
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.classList.add('rumors__notification--show');
            notification.focus();
        }, 100);
        
        setTimeout(() => {
            notification.classList.remove('rumors__notification--show');
            setTimeout(() => {
                if (document.body.contains(notification)) {
                    document.body.removeChild(notification);
                }
            }, 300);
        }, 3000);
    }

    setupAutoRefresh() {
        setInterval(() => {
            this.simulateNewNews();
        }, 10000);
    }

    simulateNewNews() {
        if (!this.transferData) return;
        
        const hero = document.querySelector('.hero-section');
        if (hero) {
            const indicator = document.createElement('div');
            indicator.className = 'rumors__new-news-indicator';
            indicator.setAttribute('role', 'status');
            indicator.setAttribute('aria-live', 'polite');
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

    shareNews(newsId) {
        const news = this.transferData.find(r => r.id === newsId);
        if (news && navigator.share) {
            navigator.share({
                title: news.headline || news.title,
                text: news.summary || news.news_summary,
                url: window.location.href
            });
        } else if (news) {
            this.copyToClipboard(`${news.headline || news.title}\n\n${news.summary || news.news_summary}\n\nSource: ${news.source}`);
        }
    }

    copyToClipboard(text) {
        navigator.clipboard.writeText(text).then(() => {
            this.showNotification('Link copied to clipboard!');
        }).catch(() => {
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
        notification.className = 'rumors__notification';
        notification.setAttribute('role', 'status');
        notification.setAttribute('aria-live', 'polite');
        notification.innerHTML = message;
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.classList.add('rumors__notification--show');
        }, 100);
        
        setTimeout(() => {
            notification.classList.remove('rumors__notification--show');
            setTimeout(() => {
                if (document.body.contains(notification)) {
                    document.body.removeChild(notification);
                }
            }, 300);
        }, 3000);
    }

    setupNewsTicker() {
        const tickerContainer = document.querySelector('.news-ticker__content');
        if (!tickerContainer || !this.transferData) return;
        
        const tickerItems = Array.isArray(this.transferData) ? this.transferData.slice(0, 5) : [];
        
        if (tickerItems.length > 0) {
            tickerContainer.innerHTML = tickerItems.map(item => 
                `<span class="ticker-item">${item.headline || 'Arsenal News'}</span>`
            ).join('');
        }
    }
}

// Initialize the app when the DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new AllForGooners();
});