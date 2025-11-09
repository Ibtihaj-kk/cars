/**
 * Dynamic Car Grid Manager
 * Handles fetching, filtering, and displaying car listings from the backend API
 */
class CarGridManager {
  constructor() {
    this.currentPage = 1;
    this.itemsPerPage = 8;
    this.totalItems = 0;
    this.totalPages = 0;
    this.currentFilters = {};
    this.isLoading = false;
    this.searchQuery = '';
    
    // DOM elements
    this.carGrid = document.getElementById('carGrid');
    this.pagination = document.getElementById('pagination');
    this.pageNumbers = document.getElementById('pageNumbers');
    this.prevBtn = document.getElementById('prevBtn');
    this.nextBtn = document.getElementById('nextBtn');
    this.sidebarHeader = document.querySelector('.sidebar-header h2');
    this.sortBtn = document.querySelector('.sort-btn');
    this.searchInput = document.querySelector('.search-input');
    
    this.init();
  }

  init() {
    this.setupEventListeners();
    this.loadInitialData();
  }

  setupEventListeners() {
    // Pagination event listeners
    if (this.prevBtn) {
      this.prevBtn.addEventListener('click', () => this.goToPreviousPage());
    }
    
    if (this.nextBtn) {
      this.nextBtn.addEventListener('click', () => this.goToNextPage());
    }

    // Search functionality
    if (this.searchInput) {
      this.searchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
          this.handleSearch();
        }
      });
    }

    // Sort functionality
    if (this.sortBtn) {
      this.sortBtn.addEventListener('click', () => this.handleSort());
    }

    // Filter selection from homepage carousel
    document.addEventListener('filterSelected', (e) => {
      this.handleFilterSelection(e.detail);
    });

    // Dynamic filters integration
    document.addEventListener('filtersChanged', (e) => {
      const { filters } = e.detail;
      this.handleDynamicFilters(filters);
    });

    // Sidebar filter changes
    this.setupSidebarFilters();
  }

  setupSidebarFilters() {
    // Price range filters
    const minPriceInput = document.getElementById('minPrice');
    const maxPriceInput = document.getElementById('maxPrice');
    const priceSlider = document.getElementById('priceSlider');

    if (minPriceInput) {
      minPriceInput.addEventListener('change', () => this.updatePriceFilter());
    }
    
    if (maxPriceInput) {
      maxPriceInput.addEventListener('change', () => this.updatePriceFilter());
    }
    
    if (priceSlider) {
      priceSlider.addEventListener('change', () => this.updatePriceFilter());
    }

    // Year filter
    const yearSlider = document.getElementById('yearSlider');
    if (yearSlider) {
      yearSlider.addEventListener('change', () => {
        this.currentFilters.year = yearSlider.value;
        this.applyFilters();
      });
    }

    // Mileage filter
    const mileageSlider = document.getElementById('mileageSlider');
    if (mileageSlider) {
      mileageSlider.addEventListener('change', () => {
        this.currentFilters.max_mileage = mileageSlider.value;
        this.applyFilters();
      });
    }

    // Checkbox filters
    const checkboxes = document.querySelectorAll('.filter-content input[type="checkbox"]');
    checkboxes.forEach(checkbox => {
      checkbox.addEventListener('change', () => this.handleCheckboxFilter(checkbox));
    });
  }

  updatePriceFilter() {
    const minPrice = document.getElementById('minPrice')?.value.replace(/,/g, '') || '';
    const maxPrice = document.getElementById('maxPrice')?.value.replace(/,/g, '') || '';
    const priceSlider = document.getElementById('priceSlider')?.value || '';

    if (minPrice) this.currentFilters.min_price = parseInt(minPrice);
    if (maxPrice) this.currentFilters.max_price = parseInt(maxPrice);
    if (priceSlider) this.currentFilters.max_price = parseInt(priceSlider);

    this.applyFilters();
  }

  handleCheckboxFilter(checkbox) {
    const filterSection = checkbox.closest('.filter-section');
    const filterType = this.getFilterTypeFromSection(filterSection);
    
    if (!filterType) return;

    const checkedBoxes = filterSection.querySelectorAll('input[type="checkbox"]:checked');
    const values = Array.from(checkedBoxes).map(cb => cb.parentElement.textContent.trim());
    
    if (values.length > 0) {
      this.currentFilters[filterType] = values;
    } else {
      delete this.currentFilters[filterType];
    }
    
    this.applyFilters();
  }

  getFilterTypeFromSection(section) {
    const summary = section.querySelector('summary');
    if (!summary) return null;
    
    const text = summary.textContent.toLowerCase();
    
    if (text.includes('make')) return 'make';
    if (text.includes('body type')) return 'body_type';
    if (text.includes('fuel type')) return 'fuel_type';
    if (text.includes('transmission')) return 'transmission';
    if (text.includes('condition')) return 'condition';
    if (text.includes('color')) return 'color';
    if (text.includes('features')) return 'features';
    
    return null;
  }

  handleFilterSelection(detail) {
    const { tab, value, data } = detail;
    console.log('Filter selection:', { tab, value, data });
    
    switch (tab) {
      case 'category':
        if (data.category) {
          this.currentFilters.body_type = data.category;
        } else {
          this.currentFilters.body_type = value;
        }
        break;
      case 'brand':
        if (data.make) {
          this.currentFilters.make = data.make;
        } else {
          this.currentFilters.make = value;
        }
        break;
      case 'model':
        this.currentFilters.model = value;
        break;
      case 'cities':
        if (data.city) {
          this.currentFilters.city = data.city;
        } else {
          this.currentFilters.city = value;
        }
        break;
      case 'body-types':
        if (data.bodyType) {
          this.currentFilters.body_type = data.bodyType;
        } else {
          this.currentFilters.body_type = value;
        }
        break;
      case 'years':
        if (data.year) {
          this.currentFilters.year = data.year;
        } else {
          this.currentFilters.year = value;
        }
        break;
      case 'budget':
        if (data.minPrice) this.currentFilters.price_min = parseInt(data.minPrice);
        if (data.maxPrice) this.currentFilters.price_max = parseInt(data.maxPrice);
        break;
    }
    
    this.currentPage = 1; // Reset to first page when filtering
    this.applyFilters();
  }

  handleSearch() {
    this.searchQuery = this.searchInput?.value.trim() || '';
    this.currentPage = 1;
    this.applyFilters();
  }

  handleSort() {
    // Implement sorting logic
    console.log('Sort functionality to be implemented');
  }

  async loadInitialData() {
    await this.fetchListings();
  }

  async applyFilters() {
    this.currentPage = 1; // Reset to first page
    await this.fetchListings();
  }

  async fetchListings() {
    if (this.isLoading) return;
    
    this.isLoading = true;
    this.showLoadingState();

    try {
      const params = new URLSearchParams({
        page: this.currentPage,
        page_size: this.itemsPerPage,
        ...this.currentFilters
      });

      if (this.searchQuery) {
        params.append('search', this.searchQuery);
      }

      console.log('Current filters:', this.currentFilters);
      console.log('API URL:', `/api/listings/search/?${params}`);
      
      const response = await fetch(`/api/listings/search/?${params}`);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      
      this.totalItems = data.count;
      this.totalPages = Math.ceil(this.totalItems / this.itemsPerPage);
      
      this.renderListings(data.results);
      this.updatePagination();
      this.updateResultsCount();
      
    } catch (error) {
      console.error('Error fetching listings:', error);
      this.showErrorState();
    } finally {
      this.isLoading = false;
    }
  }

  showLoadingState() {
    if (this.carGrid) {
      this.carGrid.innerHTML = `
        <div class="loading-state">
          <div class="loading-spinner"></div>
          <p>Loading vehicles...</p>
        </div>
      `;
    }
  }

  showErrorState() {
    if (this.carGrid) {
      this.carGrid.innerHTML = `
        <div class="error-state">
          <p>Sorry, we couldn't load the vehicles. Please try again.</p>
          <button onclick="window.carGridManager.fetchListings()" class="retry-btn">Retry</button>
        </div>
      `;
    }
  }

  renderListings(listings) {
    if (!this.carGrid) return;

    if (listings.length === 0) {
      this.carGrid.innerHTML = `
        <div class="no-results">
          <h3>No vehicles found</h3>
          <p>Try adjusting your filters or search criteria.</p>
        </div>
      `;
      return;
    }

    this.carGrid.innerHTML = listings.map(listing => this.createCarCard(listing)).join('');
  }

  createCarCard(listing) {
    // Use the primary_image from API response or fallback to our sample images
    const carImages = ['/media/car/car1.svg', '/media/car/car2.svg', '/media/car/car3.svg', '/media/car/car4.svg', '/media/car/car5.svg'];
    const primaryImage = listing.primary_image 
      ? listing.primary_image 
      : carImages[(listing.id % carImages.length)];
    
    const imageCount = listing.image_count || 1;
    const hasVideo = listing.videos && listing.videos.length > 0;
    
    const statusClass = this.getStatusClass(listing);
    const statusLabel = this.getStatusLabel(listing);
    
    return `
      <div class="car-card" data-listing-id="${listing.id}">
        <div class="car-image">
          <img src="${primaryImage}" alt="${listing.title}" loading="lazy">
          ${statusLabel ? `<div class="status-label ${statusClass}">${statusLabel}</div>` : ''}
        </div>
        <div class="car-header">
          <span class="photo-count">${imageCount} Photos</span>
          ${hasVideo ? '<span class="video-icon"><a href="#"><ion-icon name="caret-forward-outline"></ion-icon> Video Tour</a></span>' : ''}
        </div>
        <div class="car-details">
          <h3>${listing.title}</h3>
          <p class="car-model">${listing.make || ''} ${listing.model || ''}</p>
          <p class="car-price">$${this.formatPrice(listing.price)}</p>
          <p class="car-info">
            <span class="mileage">${this.formatMileage(listing.kilometers)}</span> • 
            <span class="location">${listing.city || 'Location not specified'}</span> • 
            <span class="year">${listing.year || 'N/A'}</span>
          </p>
          <p class="fuel-economy">${listing.body_type?.name || 'Vehicle'}</p>
          <div class="card-actions">
            <button class="primary-btn" onclick="window.carGridManager.scheduleTestDrive(${listing.id})">🗓 Schedule Test Drive</button>
            <a href="/car/${listing.slug}/" class="secondary-btn">Learn More</a>
          </div>
          <div class="card-footer">
            <a href="#" onclick="window.carGridManager.compareListing(${listing.id})"><ion-icon name="git-compare-outline"></ion-icon> Compare</a>
            <a href="#" onclick="window.carGridManager.saveListing(${listing.id})"><i class="ri-save-3-line"></i> Save</a>
            <a href="/car/${listing.slug}/">👁 View Details</a>
          </div>
        </div>
      </div>
    `;
  }

  getStatusClass(listing) {
    if (listing.is_featured) return 'featured';
    if (listing.year >= new Date().getFullYear()) return 'new-arrival';
    if (listing.price > 100000) return 'luxury-pick';
    return 'used-vehicle';
  }

  getStatusLabel(listing) {
    if (listing.is_featured) return 'FEATURED';
    if (listing.year >= new Date().getFullYear()) return 'NEW';
    if (listing.price > 100000) return 'LUXURY';
    return null;
  }

  formatPrice(price) {
    if (!price) return 'Price on request';
    return new Intl.NumberFormat('en-US').format(price);
  }

  formatMileage(kilometers) {
    if (!kilometers) return '0 miles';
    const miles = Math.round(kilometers * 0.621371);
    return `${new Intl.NumberFormat('en-US').format(miles)} miles`;
  }

  updatePagination() {
    if (!this.pageNumbers || !this.prevBtn || !this.nextBtn) return;

    // Update previous/next buttons
    this.prevBtn.disabled = this.currentPage === 1;
    this.nextBtn.disabled = this.currentPage === this.totalPages || this.totalPages === 0;

    // Generate page numbers
    this.pageNumbers.innerHTML = this.generatePageNumbers();
  }

  generatePageNumbers() {
    if (this.totalPages <= 1) return '';

    let pages = [];
    const maxVisiblePages = 5;
    
    if (this.totalPages <= maxVisiblePages) {
      // Show all pages if total is small
      for (let i = 1; i <= this.totalPages; i++) {
        pages.push(i);
      }
    } else {
      // Show smart pagination
      if (this.currentPage <= 3) {
        pages = [1, 2, 3, 4, '...', this.totalPages];
      } else if (this.currentPage >= this.totalPages - 2) {
        pages = [1, '...', this.totalPages - 3, this.totalPages - 2, this.totalPages - 1, this.totalPages];
      } else {
        pages = [1, '...', this.currentPage - 1, this.currentPage, this.currentPage + 1, '...', this.totalPages];
      }
    }

    return pages.map(page => {
      if (page === '...') {
        return '<span class="page-ellipsis">...</span>';
      }
      
      const isActive = page === this.currentPage;
      return `<button class="page-btn ${isActive ? 'current' : ''}" onclick="window.carGridManager.goToPage(${page})">${page}</button>`;
    }).join('');
  }

  updateResultsCount() {
    if (this.sidebarHeader) {
      const count = this.totalItems.toLocaleString();
      this.sidebarHeader.textContent = `${count} VEHICLES FOUND`;
    }
  }

  goToPage(page) {
    if (page < 1 || page > this.totalPages || page === this.currentPage) return;
    
    this.currentPage = page;
    this.fetchListings();
    
    // Scroll to top of results
    if (this.carGrid) {
      this.carGrid.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }

  goToPreviousPage() {
    this.goToPage(this.currentPage - 1);
  }

  goToNextPage() {
    this.goToPage(this.currentPage + 1);
  }

  // Action methods for car cards
  scheduleTestDrive(listingId) {
    console.log('Schedule test drive for listing:', listingId);
    // Implement test drive scheduling
  }

  compareListing(listingId) {
    console.log('Compare listing:', listingId);
    // Implement comparison functionality
  }

  async saveListing(listingId) {
    try {
      const response = await fetch('/api/listings/saved/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': this.getCSRFToken()
        },
        body: JSON.stringify({ listing: listingId })
      });
      
      if (response.ok) {
        console.log('Listing saved successfully');
        // Update UI to show saved state
      }
    } catch (error) {
      console.error('Error saving listing:', error);
    }
  }

  getCSRFToken() {
    return document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
  }

  // Handle dynamic filters from filter components
    handleDynamicFilters(filters) {
        // Map dynamic filter format to API format
        const apiFilters = {};
        
        if (filters.makes && filters.makes.length > 0) {
            apiFilters.make = filters.makes[0]; // Backend expects single value, not array
        }
        
        if (filters.models && filters.models.length > 0) {
            apiFilters.model = filters.models[0]; // Backend expects single value, not array
        }
        
        if (filters.cities && filters.cities.length > 0) {
            apiFilters.city = filters.cities[0]; // Backend expects single value, not array
        }
        
        if (filters.bodyTypes && filters.bodyTypes.length > 0) {
            apiFilters.body_type = filters.bodyTypes[0]; // Backend expects single value, not array
        }
        
        if (filters.priceMin !== null && filters.priceMin !== undefined) {
            apiFilters.min_price = filters.priceMin;
        }
        
        if (filters.priceMax !== null && filters.priceMax !== undefined) {
            apiFilters.max_price = filters.priceMax;
        }
        
        if (filters.yearMin !== null && filters.yearMin !== undefined) {
            apiFilters.min_year = filters.yearMin;
        }
        
        if (filters.yearMax !== null && filters.yearMax !== undefined) {
            apiFilters.max_year = filters.yearMax;
        }
        
        if (filters.mileageMax !== null && filters.mileageMax !== undefined) {
            apiFilters.max_kilometers = filters.mileageMax;
        }
        
        // Note: fuel_economy_min is not supported by the backend API
        
        // Update current filters
        this.currentFilters = { ...this.currentFilters, ...apiFilters };
        this.currentPage = 1;
        this.applyFilters();
    }

  // Public method to clear all filters
  clearAllFilters() {
    this.currentFilters = {};
    this.searchQuery = '';
    this.currentPage = 1;
    
    // Reset UI elements
    if (this.searchInput) this.searchInput.value = '';
    
    // Reset sliders and checkboxes
    const sliders = document.querySelectorAll('.slider');
    sliders.forEach(slider => {
      slider.value = slider.getAttribute('value') || slider.min;
      slider.dispatchEvent(new Event('input'));
    });
    
    const checkboxes = document.querySelectorAll('.filter-content input[type="checkbox"]');
    checkboxes.forEach(checkbox => checkbox.checked = false);
    
    // Dispatch event to notify filter components
    document.dispatchEvent(new CustomEvent('filtersCleared'));
    
    this.fetchListings();
  }
}

// Initialize the car grid manager when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
  window.carGridManager = new CarGridManager();
});

// Add loading spinner CSS if not already present
if (!document.querySelector('#car-grid-styles')) {
  const style = document.createElement('style');
  style.id = 'car-grid-styles';
  style.textContent = `
    .loading-state, .error-state, .no-results {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 60px 20px;
      text-align: center;
      grid-column: 1 / -1;
    }
    
    .loading-spinner {
      width: 40px;
      height: 40px;
      border: 4px solid #f3f3f3;
      border-top: 4px solid #4d78bc;
      border-radius: 50%;
      animation: spin 1s linear infinite;
      margin-bottom: 20px;
    }
    
    @keyframes spin {
      0% { transform: rotate(0deg); }
      100% { transform: rotate(360deg); }
    }
    
    .retry-btn {
      background: #4d78bc;
      color: white;
      border: none;
      padding: 10px 20px;
      border-radius: 5px;
      cursor: pointer;
      margin-top: 10px;
    }
    
    .retry-btn:hover {
      background: #3a5a94;
    }
    
    .page-ellipsis {
      padding: 8px 12px;
      color: #666;
    }
    
    .car-card img {
      transition: transform 0.3s ease;
    }
    
    .car-card:hover img {
      transform: scale(1.05);
    }
  `;
  document.head.appendChild(style);
}
