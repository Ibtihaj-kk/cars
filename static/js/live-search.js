/**
 * Live Search Manager
 * Handles real-time search suggestions for the home page sidebar
 */
class LiveSearchManager {
  constructor() {
    this.searchInput = document.querySelector('.search-input');
    this.searchContainer = document.querySelector('.search-container');
    this.debounceTimer = null;
    this.debounceDelay = 300; // 300ms delay
    this.minQueryLength = 2;
    this.isLoading = false;
    this.currentQuery = '';
    this.suggestionsDropdown = null;
    this.carGridManager = null; // Reference to car grid manager
    
    this.init();
  }

  init() {
    if (!this.searchInput || !this.searchContainer) {
      console.warn('Live search elements not found');
      return;
    }

    this.createSuggestionsDropdown();
    this.setupEventListeners();
  }

  // Method to set car grid manager reference for integration
  setCarGridManager(carGridManager) {
    this.carGridManager = carGridManager;
  }

  createSuggestionsDropdown() {
    // Create suggestions dropdown element
    this.suggestionsDropdown = document.createElement('div');
    this.suggestionsDropdown.className = 'live-search-suggestions';
    this.suggestionsDropdown.style.display = 'none';
    
    // Insert after search input
    this.searchInput.parentNode.insertBefore(
      this.suggestionsDropdown, 
      this.searchInput.nextSibling
    );
  }

  setupEventListeners() {
    // Input event for live search
    this.searchInput.addEventListener('input', (e) => {
      this.handleInput(e.target.value);
    });

    // Focus event to show suggestions if available
    this.searchInput.addEventListener('focus', () => {
      if (this.suggestionsDropdown.children.length > 0) {
        this.showSuggestions();
      }
    });

    // Blur event to hide suggestions (with delay for click handling)
    this.searchInput.addEventListener('blur', () => {
      setTimeout(() => {
        this.hideSuggestions();
      }, 200);
    });

    // Keyboard navigation
    this.searchInput.addEventListener('keydown', (e) => {
      this.handleKeyNavigation(e);
    });

    // Click outside to close
    document.addEventListener('click', (e) => {
      if (!this.searchContainer.contains(e.target)) {
        this.hideSuggestions();
      }
    });
  }

  handleInput(query) {
    this.currentQuery = query.trim();

    // Clear previous timer
    if (this.debounceTimer) {
      clearTimeout(this.debounceTimer);
    }

    // Hide suggestions if query is too short
    if (this.currentQuery.length < this.minQueryLength) {
      this.hideSuggestions();
      // Clear car grid search if query is too short
      if (this.carGridManager) {
        this.carGridManager.searchQuery = '';
        this.carGridManager.applyFilters();
      }
      return;
    }

    // Set new timer for debounced search
    this.debounceTimer = setTimeout(() => {
      this.performLiveSearch(this.currentQuery);
      // Also trigger car grid filtering
      if (this.carGridManager) {
        this.carGridManager.searchQuery = this.currentQuery;
        this.carGridManager.applyFilters();
      }
    }, this.debounceDelay);
  }

  async performLiveSearch(query) {
    if (this.isLoading || query !== this.currentQuery) {
      return;
    }

    this.isLoading = true;
    this.showLoadingState();

    try {
      const response = await fetch(`/api/listings/live-search/?q=${encodeURIComponent(query)}&limit=8`);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      this.displaySuggestions(data.suggestions);
      
    } catch (error) {
      console.error('Live search error:', error);
      this.showErrorState();
    } finally {
      this.isLoading = false;
    }
  }

  showLoadingState() {
    this.suggestionsDropdown.innerHTML = `
      <div class="live-search-loading">
        <div class="loading-spinner"></div>
        <span>Searching...</span>
      </div>
    `;
    this.showSuggestions();
  }

  showErrorState() {
    this.suggestionsDropdown.innerHTML = `
      <div class="live-search-error">
        <span>Search temporarily unavailable</span>
      </div>
    `;
    this.showSuggestions();
  }

  displaySuggestions(suggestions) {
    if (!suggestions || suggestions.length === 0) {
      this.suggestionsDropdown.innerHTML = `
        <div class="live-search-no-results">
          <span>No results found for "${this.currentQuery}"</span>
        </div>
      `;
      this.showSuggestions();
      return;
    }

    const suggestionsHTML = suggestions.map((suggestion, index) => `
      <div class="live-search-item" data-index="${index}" data-id="${suggestion.id}" data-slug="${suggestion.slug}">
        <div class="suggestion-main">
          <div class="suggestion-title">${this.highlightQuery(suggestion.title)}</div>
          <div class="suggestion-details">
            ${suggestion.year} ${suggestion.make} ${suggestion.model}
          </div>
        </div>
        <div class="suggestion-meta">
          <div class="suggestion-price">$${this.formatPrice(suggestion.price)}</div>
          <div class="suggestion-location">${suggestion.location}</div>
        </div>
      </div>
    `).join('');

    this.suggestionsDropdown.innerHTML = suggestionsHTML;
    this.setupSuggestionClickHandlers();
    this.showSuggestions();
  }

  setupSuggestionClickHandlers() {
    const items = this.suggestionsDropdown.querySelectorAll('.live-search-item');
    items.forEach(item => {
      item.addEventListener('click', () => {
        const listingSlug = item.dataset.slug;
        window.location.href = `/car/${listingSlug}/`;
      });
    });
  }

  highlightQuery(text) {
    if (!this.currentQuery) return text;
    
    const regex = new RegExp(`(${this.escapeRegex(this.currentQuery)})`, 'gi');
    return text.replace(regex, '<mark>$1</mark>');
  }

  escapeRegex(string) {
    return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  }

  formatPrice(price) {
    if (!price) return 'N/A';
    return new Intl.NumberFormat('en-US').format(price);
  }

  handleKeyNavigation(e) {
    const items = this.suggestionsDropdown.querySelectorAll('.live-search-item');
    if (items.length === 0) return;

    const currentActive = this.suggestionsDropdown.querySelector('.live-search-item.active');
    let currentIndex = currentActive ? parseInt(currentActive.dataset.index) : -1;

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        currentIndex = Math.min(currentIndex + 1, items.length - 1);
        this.setActiveItem(currentIndex);
        break;
        
      case 'ArrowUp':
        e.preventDefault();
        currentIndex = Math.max(currentIndex - 1, 0);
        this.setActiveItem(currentIndex);
        break;
        
      case 'Enter':
        e.preventDefault();
        if (currentActive) {
          currentActive.click();
        } else {
          // Fallback to regular search
          this.performRegularSearch();
        }
        break;
        
      case 'Escape':
        this.hideSuggestions();
        this.searchInput.blur();
        break;
    }
  }

  setActiveItem(index) {
    const items = this.suggestionsDropdown.querySelectorAll('.live-search-item');
    
    // Remove active class from all items
    items.forEach(item => item.classList.remove('active'));
    
    // Add active class to selected item
    if (items[index]) {
      items[index].classList.add('active');
    }
  }

  performRegularSearch() {
    // Auto-filtering is now handled in handleInput, so just hide suggestions
    this.hideSuggestions();
  }

  showSuggestions() {
    this.suggestionsDropdown.style.display = 'block';
  }

  hideSuggestions() {
    this.suggestionsDropdown.style.display = 'none';
    // Remove active states
    const activeItems = this.suggestionsDropdown.querySelectorAll('.live-search-item.active');
    activeItems.forEach(item => item.classList.remove('active'));
  }

  // Public method to clear suggestions
  clearSuggestions() {
    this.suggestionsDropdown.innerHTML = '';
    this.hideSuggestions();
  }
}

// Initialize live search when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
  window.liveSearchManager = new LiveSearchManager();
  
  // Connect live search with car grid manager when both are available
  if (window.carGridManager) {
    window.liveSearchManager.setCarGridManager(window.carGridManager);
  } else {
    // Wait for car grid manager to be initialized
    const checkCarGrid = setInterval(() => {
      if (window.carGridManager) {
        window.liveSearchManager.setCarGridManager(window.carGridManager);
        clearInterval(checkCarGrid);
      }
    }, 100);
  }
});