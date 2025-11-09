/**
 * Dynamic Filters Manager - Optimized for PostgreSQL
 * Handles dynamic population of filter dropdowns and their interactions
 * with enhanced performance and caching
 */

class DynamicFiltersManager {
    constructor() {
        this.filterData = {
            makes: [],
            models: [],
            cities: [],
            years: [],
            fuel_types: [],
            transmissions: [],
            conditions: [],
            body_types: [],
            exterior_colors: [],
            price_range: { min: 0, max: 200000 },
            year_range: { min: 2000, max: 2024 },
            price_ranges: [],
            year_ranges: [],
            kilometers_ranges: []
        };
        
        this.selectedFilters = {
            makes: [],
            models: [],
            cities: [],
            years: [],
            fuel_types: [],
            transmissions: [],
            conditions: [],
            body_types: [],
            exterior_colors: [],
            price_min: null,
            price_max: null,
            year_min: null,
            year_max: null,
            kilometers_max: null,
            search: null
        };
        
        this.cache = new Map();
        this.debounceTimeout = null;
        this.isLoading = false;
        
        this.init();
    }
    
    async init() {
        try {
            await this.loadFilterData();
            this.populateFilters();
            this.setupEventListeners();
        } catch (error) {
            console.error('Failed to initialize dynamic filters:', error);
        }
    }
    
    async loadFilterData() {
        // Check cache first
        const cacheKey = 'filter_data';
        const cachedData = this.cache.get(cacheKey);
        
        if (cachedData && Date.now() - cachedData.timestamp < 300000) { // 5 minutes cache
            this.filterData = cachedData.data;
            console.log('Filter data loaded from cache');
            return;
        }
        
        this.isLoading = true;
        this.showLoadingState();
        
        try {
            const response = await fetch('/api/listings/filter-data/', {
                headers: {
                    'Accept': 'application/json',
                    'Cache-Control': 'max-age=300'
                }
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            this.filterData = {
                makes: data.makes || [],
                models: data.models || [],
                cities: data.cities || [],
                years: data.years || [],
                fuel_types: data.fuel_types || [],
                transmissions: data.transmissions || [],
                conditions: data.conditions || [],
                body_types: data.body_types || [],
                exterior_colors: data.exterior_colors || [],
                price_range: data.price_range || { min: 0, max: 200000 },
                year_range: data.year_range || { min: 2000, max: 2024 },
                price_ranges: data.price_ranges || [],
                year_ranges: data.year_ranges || [],
                kilometers_ranges: data.kilometers_ranges || []
            };
            
            // Cache the data
            this.cache.set(cacheKey, {
                data: this.filterData,
                timestamp: Date.now()
            });
            
            console.log('Filter data loaded from API:', this.filterData);
        } catch (error) {
            console.error('Error loading filter data:', error);
            // Use fallback data if API fails
            this.setFallbackData();
        } finally {
            this.isLoading = false;
            this.hideLoadingState();
        }
    }
    
    setFallbackData() {
        this.filterData = {
            makes: [
                { name: 'Acura', count: 1 },
                { name: 'Audi', count: 58 },
                { name: 'BMW', count: 45 },
                { name: 'Mercedes-Benz', count: 32 },
                { name: 'Tesla', count: 28 },
                { name: 'Porsche', count: 15 },
                { name: 'Lexus', count: 22 },
                { name: 'Jaguar', count: 8 },
                { name: 'Range Rover', count: 6 },
                { name: 'Rolls Royce', count: 10 }
            ],
            models: [],
            cities: [
                { name: 'Los Angeles', count: 45 },
                { name: 'Beverly Hills', count: 32 },
                { name: 'Manhattan', count: 28 },
                { name: 'San Jose', count: 22 },
                { name: 'Miami Beach', count: 18 },
                { name: 'Houston', count: 15 },
                { name: 'Chicago', count: 12 },
                { name: 'Scottsdale', count: 10 }
            ],
            years: Array.from({ length: 25 }, (_, i) => ({ year: 2024 - i, count: Math.floor(Math.random() * 20) + 1 })),
            bodyTypes: [
                { name: 'SUV', count: 85 },
                { name: 'Sedan', count: 65 },
                { name: 'Coupe', count: 45 },
                { name: 'Convertible', count: 25 },
                { name: 'Hatchback', count: 15 },
                { name: 'Wagon', count: 8 }
            ],
            priceRange: { min: 0, max: 500000 }
        };
    }
    
    populateFilters() {
        this.populateMakeFilter();
        this.populateBodyTypeFilter();
        this.populateCityFilter();
        this.populateFuelTypeFilter();
        this.populateTransmissionFilter();
        this.populateConditionFilter();
        this.populateColorFilter();
        this.updatePriceRange();
        this.updateYearRange();
        this.populatePredefinedRanges();
    }
    
    populateMakeFilter() {
        const makeFilterContent = this.findFilterContent('Make');
        if (!makeFilterContent) return;
        
        makeFilterContent.innerHTML = '';
        
        if (this.filterData.makes.length === 0) {
            makeFilterContent.innerHTML = '<p class="no-data">No makes available</p>';
            return;
        }
        
        this.filterData.makes.forEach(make => {
            const label = document.createElement('label');
            label.className = 'filter-option';
            label.innerHTML = `
                <input type="checkbox" value="${make.value}" data-filter="make"> 
                <span class="filter-label">${make.label}</span>
                <span class="filter-count">(${make.count})</span>
            `;
            makeFilterContent.appendChild(label);
        });
    }
    
    populateBodyTypeFilter() {
        const bodyTypeFilterContent = this.findFilterContent('Body Type');
        if (!bodyTypeFilterContent) return;
        
        bodyTypeFilterContent.innerHTML = '';
        
        if (this.filterData.body_types.length === 0) {
            bodyTypeFilterContent.innerHTML = '<p class="no-data">No body types available</p>';
            return;
        }
        
        this.filterData.body_types.forEach(bodyType => {
            const label = document.createElement('label');
            label.className = 'filter-option';
            label.innerHTML = `
                <input type="checkbox" value="${bodyType.value}" data-filter="body_type"> 
                <span class="filter-label">${bodyType.label}</span>
                <span class="filter-count">(${bodyType.count})</span>
            `;
            bodyTypeFilterContent.appendChild(label);
        });
    }
    
    populateFuelTypeFilter() {
        const fuelTypeFilterContent = this.findOrCreateFilterContent('Fuel Type');
        if (!fuelTypeFilterContent) return;
        
        fuelTypeFilterContent.innerHTML = '';
        
        if (this.filterData.fuel_types.length === 0) {
            fuelTypeFilterContent.innerHTML = '<p class="no-data">No fuel types available</p>';
            return;
        }
        
        this.filterData.fuel_types.forEach(fuelType => {
            const label = document.createElement('label');
            label.className = 'filter-option';
            label.innerHTML = `
                <input type="checkbox" value="${fuelType.value}" data-filter="fuel_type"> 
                <span class="filter-label">${fuelType.label}</span>
                <span class="filter-count">(${fuelType.count})</span>
            `;
            fuelTypeFilterContent.appendChild(label);
        });
    }
    
    populateTransmissionFilter() {
        const transmissionFilterContent = this.findOrCreateFilterContent('Transmission');
        if (!transmissionFilterContent) return;
        
        transmissionFilterContent.innerHTML = '';
        
        if (this.filterData.transmissions.length === 0) {
            transmissionFilterContent.innerHTML = '<p class="no-data">No transmissions available</p>';
            return;
        }
        
        this.filterData.transmissions.forEach(transmission => {
            const label = document.createElement('label');
            label.className = 'filter-option';
            label.innerHTML = `
                <input type="checkbox" value="${transmission.value}" data-filter="transmission"> 
                <span class="filter-label">${transmission.label}</span>
                <span class="filter-count">(${transmission.count})</span>
            `;
            transmissionFilterContent.appendChild(label);
        });
    }
    
    populateConditionFilter() {
        const conditionFilterContent = this.findOrCreateFilterContent('Condition');
        if (!conditionFilterContent) return;
        
        conditionFilterContent.innerHTML = '';
        
        if (this.filterData.conditions.length === 0) {
            conditionFilterContent.innerHTML = '<p class="no-data">No conditions available</p>';
            return;
        }
        
        this.filterData.conditions.forEach(condition => {
            const label = document.createElement('label');
            label.className = 'filter-option';
            label.innerHTML = `
                <input type="checkbox" value="${condition.value}" data-filter="condition"> 
                <span class="filter-label">${condition.label}</span>
                <span class="filter-count">(${condition.count})</span>
            `;
            conditionFilterContent.appendChild(label);
        });
    }
    
    populateColorFilter() {
        const colorFilterContent = this.findOrCreateFilterContent('Color');
        if (!colorFilterContent) return;
        
        colorFilterContent.innerHTML = '';
        
        if (this.filterData.exterior_colors.length === 0) {
            colorFilterContent.innerHTML = '<p class="no-data">No colors available</p>';
            return;
        }
        
        this.filterData.exterior_colors.forEach(color => {
            const label = document.createElement('label');
            label.className = 'filter-option';
            label.innerHTML = `
                <input type="checkbox" value="${color.value}" data-filter="exterior_color"> 
                <span class="filter-label">${color.label}</span>
                <span class="filter-count">(${color.count})</span>
            `;
            colorFilterContent.appendChild(label);
        });
    }
    
    populateCityFilter() {
        // Find or create city filter section
        const filterSections = document.querySelectorAll('.filter-section');
        let cityFilterSection = null;
        
        for (const section of filterSections) {
            const summary = section.querySelector('summary');
            if (summary && summary.textContent.includes('City')) {
                cityFilterSection = section;
                break;
            }
        }
        
        if (!cityFilterSection) {
            // Create city filter section if it doesn't exist
            const filtersContainer = document.querySelector('.filters');
            if (filtersContainer) {
                cityFilterSection = document.createElement('details');
                cityFilterSection.className = 'filter-section';
                cityFilterSection.innerHTML = `
                    <summary>City <span class="arrow">▼</span></summary>
                    <div class="filter-content"></div>
                `;
                // Insert after Body Type filter
                const allFilterSections = document.querySelectorAll('.filter-section');
                let bodyTypeFilter = null;
                
                for (const section of allFilterSections) {
                    const summary = section.querySelector('summary');
                    if (summary && summary.textContent.includes('Body Type')) {
                        bodyTypeFilter = section;
                        break;
                    }
                }
                
                if (bodyTypeFilter) {
                    bodyTypeFilter.insertAdjacentElement('afterend', cityFilterSection);
                } else {
                    filtersContainer.appendChild(cityFilterSection);
                }
            }
        }
        
        const cityFilterContent = cityFilterSection?.querySelector('.filter-content');
        if (!cityFilterContent) return;
        
        cityFilterContent.innerHTML = '';
        
        this.filterData.cities.forEach(city => {
            const label = document.createElement('label');
            label.innerHTML = `
                <input type="checkbox" value="${city.name}" data-filter="city"> 
                ${city.name} ${city.count ? `(${city.count})` : ''}
            `;
            cityFilterContent.appendChild(label);
        });
    }
    
    // Helper methods
    findFilterContent(filterName) {
        const filterSections = document.querySelectorAll('.filter-section');
        for (const section of filterSections) {
            const summary = section.querySelector('summary');
            if (summary && summary.textContent.includes(filterName)) {
                return section.querySelector('.filter-content');
            }
        }
        return null;
    }
    
    findOrCreateFilterContent(filterName) {
        let filterContent = this.findFilterContent(filterName);
        
        if (!filterContent) {
            const filtersContainer = document.querySelector('.filters');
            if (filtersContainer) {
                const filterSection = document.createElement('details');
                filterSection.className = 'filter-section';
                filterSection.innerHTML = `
                    <summary>${filterName} <span class="arrow">▼</span></summary>
                    <div class="filter-content"></div>
                `;
                filtersContainer.appendChild(filterSection);
                filterContent = filterSection.querySelector('.filter-content');
            }
        }
        
        return filterContent;
    }
    
    showLoadingState() {
        const filtersContainer = document.querySelector('.filters');
        if (filtersContainer) {
            filtersContainer.classList.add('loading');
            const loadingIndicator = document.createElement('div');
            loadingIndicator.className = 'filter-loading';
            loadingIndicator.innerHTML = '<span>Loading filters...</span>';
            filtersContainer.prepend(loadingIndicator);
        }
    }
    
    hideLoadingState() {
        const filtersContainer = document.querySelector('.filters');
        if (filtersContainer) {
            filtersContainer.classList.remove('loading');
            const loadingIndicator = filtersContainer.querySelector('.filter-loading');
            if (loadingIndicator) {
                loadingIndicator.remove();
            }
        }
    }
    
    updatePriceRange() {
        const priceSlider = document.getElementById('priceSlider');
        const priceValue = document.getElementById('priceValue');
        
        if (priceSlider && this.filterData.price_range) {
            priceSlider.min = this.filterData.price_range.min;
            priceSlider.max = this.filterData.price_range.max;
            priceSlider.value = Math.floor(this.filterData.price_range.max / 2);
            
            if (priceValue) {
                priceValue.textContent = this.formatPrice(priceSlider.value);
            }
        }
    }
    
    updateYearRange() {
        const yearSlider = document.getElementById('yearSlider');
        const yearValue = document.getElementById('yearValue');
        
        if (yearSlider && this.filterData.year_range) {
            yearSlider.min = this.filterData.year_range.min;
            yearSlider.max = this.filterData.year_range.max;
            yearSlider.value = this.filterData.year_range.max - 2; // Default to 2 years ago
            
            if (yearValue) {
                yearValue.textContent = yearSlider.value;
            }
        }
    }
    
    populatePredefinedRanges() {
        this.populatePriceRanges();
        this.populateYearRanges();
        this.populateKilometersRanges();
    }
    
    populatePriceRanges() {
        const priceRangesContainer = document.getElementById('priceRanges');
        if (!priceRangesContainer || !this.filterData.price_ranges) return;
        
        priceRangesContainer.innerHTML = '';
        
        this.filterData.price_ranges.forEach(range => {
            const label = document.createElement('label');
            label.className = 'filter-option range-option';
            label.innerHTML = `
                <input type="radio" name="priceRange" value="${range.value}" data-filter="price_range"> 
                <span class="filter-label">${range.label}</span>
            `;
            priceRangesContainer.appendChild(label);
        });
    }
    
    populateYearRanges() {
        const yearRangesContainer = document.getElementById('yearRanges');
        if (!yearRangesContainer || !this.filterData.year_ranges) return;
        
        yearRangesContainer.innerHTML = '';
        
        this.filterData.year_ranges.forEach(range => {
            const label = document.createElement('label');
            label.className = 'filter-option range-option';
            label.innerHTML = `
                <input type="radio" name="yearRange" value="${range.value}" data-filter="year_range"> 
                <span class="filter-label">${range.label}</span>
            `;
            yearRangesContainer.appendChild(label);
        });
    }
    
    populateKilometersRanges() {
        const kilometersRangesContainer = document.getElementById('kilometersRanges');
        if (!kilometersRangesContainer || !this.filterData.kilometers_ranges) return;
        
        kilometersRangesContainer.innerHTML = '';
        
        this.filterData.kilometers_ranges.forEach(range => {
            const label = document.createElement('label');
            label.className = 'filter-option range-option';
            label.innerHTML = `
                <input type="radio" name="kilometersRange" value="${range.value}" data-filter="kilometers_range"> 
                <span class="filter-label">${range.label}</span>
            `;
            kilometersRangesContainer.appendChild(label);
        });
    }
    
    setupEventListeners() {
        // Checkbox and radio filters
        document.addEventListener('change', (e) => {
            if ((e.target.type === 'checkbox' || e.target.type === 'radio') && e.target.dataset.filter) {
                if (e.target.type === 'checkbox') {
                    this.handleCheckboxFilter(e.target);
                } else if (e.target.type === 'radio') {
                    this.handleRadioFilter(e.target);
                }
                
                // Load models when make filter changes
                if (e.target.dataset.filter === 'make') {
                    this.loadModelsForSelectedMakes();
                }
            }
        });
        
        // Price slider
        const priceSlider = document.getElementById('priceSlider');
        if (priceSlider) {
            priceSlider.addEventListener('input', (e) => {
                const priceValue = document.getElementById('priceValue');
                if (priceValue) {
                    priceValue.textContent = this.formatPrice(e.target.value);
                }
                this.selectedFilters.price_max = parseInt(e.target.value);
                this.debounceFilterUpdate();
            });
        }
        
        // Year slider
        const yearSlider = document.getElementById('yearSlider');
        if (yearSlider) {
            yearSlider.addEventListener('input', (e) => {
                const yearValue = document.getElementById('yearValue');
                if (yearValue) {
                    yearValue.textContent = e.target.value;
                }
                this.selectedFilters.year_min = parseInt(e.target.value);
                this.debounceFilterUpdate();
            });
        }
        
        // Kilometers slider
        const kilometersSlider = document.getElementById('kilometersSlider');
        if (kilometersSlider) {
            kilometersSlider.addEventListener('input', (e) => {
                const kilometersValue = document.getElementById('kilometersValue');
                if (kilometersValue) {
                    kilometersValue.textContent = this.formatKilometers(e.target.value);
                }
                this.selectedFilters.kilometers_max = parseInt(e.target.value);
                this.debounceFilterUpdate();
            });
        }
        
        // Fuel economy slider
        const fuelEconomySlider = document.getElementById('fuelEconomySlider');
        if (fuelEconomySlider) {
            fuelEconomySlider.addEventListener('input', (e) => {
                const fuelEconomyValue = document.getElementById('fuelEconomyValue');
                if (fuelEconomyValue) {
                    fuelEconomyValue.textContent = `${e.target.value} L/100km`;
                }
                this.selectedFilters.fuel_economy_min = parseInt(e.target.value);
                this.debounceFilterUpdate();
            });
        }
        
        // Price input fields
        const minPriceInput = document.getElementById('minPrice');
        const maxPriceInput = document.getElementById('maxPrice');
        
        if (minPriceInput) {
            minPriceInput.addEventListener('change', (e) => {
                this.selectedFilters.price_min = this.parsePrice(e.target.value);
                this.debounceFilterUpdate();
            });
        }
        
        if (maxPriceInput) {
            maxPriceInput.addEventListener('change', (e) => {
                this.selectedFilters.price_max = this.parsePrice(e.target.value);
                this.debounceFilterUpdate();
            });
        }
        
        // Clear filters button
        const clearFiltersBtn = document.getElementById('clearFilters');
        if (clearFiltersBtn) {
            clearFiltersBtn.addEventListener('click', () => {
                this.clearAllFilters();
            });
        }
    }
    
    handleCheckboxFilter(checkbox) {
        const filterType = checkbox.dataset.filter;
        const value = checkbox.value;
        
        if (checkbox.checked) {
            if (!this.selectedFilters[filterType + 's']) {
                this.selectedFilters[filterType + 's'] = [];
            }
            this.selectedFilters[filterType + 's'].push(value);
        } else {
            if (this.selectedFilters[filterType + 's']) {
                this.selectedFilters[filterType + 's'] = this.selectedFilters[filterType + 's'].filter(v => v !== value);
            }
        }
        
        this.debounceFilterUpdate();
    }
    
    handleRadioFilter(radio) {
        const filterType = radio.dataset.filter;
        const value = radio.value;
        
        if (radio.checked) {
            this.selectedFilters[filterType] = value;
        }
        
        this.debounceFilterUpdate();
    }
    
    async loadModelsForSelectedMakes() {
        const selectedMakes = this.selectedFilters.makes;
        if (selectedMakes.length === 0) {
            this.populateModelFilter([]);
            return;
        }
        
        try {
            const makeParams = selectedMakes.map(make => `make=${encodeURIComponent(make)}`).join('&');
            const response = await fetch(`/api/listings/models-by-make/?${makeParams}`);
            
            if (response.ok) {
                const data = await response.json();
                this.populateModelFilter(data.models || []);
            }
        } catch (error) {
            console.error('Error loading models:', error);
        }
    }
    
    populateModelFilter(models) {
        // Find or create model filter section
        const filterSections = document.querySelectorAll('.filter-section');
        let modelFilterSection = null;
        
        for (const section of filterSections) {
            const summary = section.querySelector('summary');
            if (summary && summary.textContent.includes('Model')) {
                modelFilterSection = section;
                break;
            }
        }
        
        if (!modelFilterSection) {
            // Create model filter section if it doesn't exist
            const filtersContainer = document.querySelector('.filters');
            if (filtersContainer) {
                modelFilterSection = document.createElement('details');
                modelFilterSection.className = 'filter-section';
                modelFilterSection.innerHTML = `
                    <summary>Model <span class="arrow">▼</span></summary>
                    <div class="filter-content"></div>
                `;
                // Insert after Make filter
                const allFilterSections = document.querySelectorAll('.filter-section');
                let makeFilter = null;
                
                for (const section of allFilterSections) {
                    const summary = section.querySelector('summary');
                    if (summary && summary.textContent.includes('Make')) {
                        makeFilter = section;
                        break;
                    }
                }
                
                if (makeFilter) {
                    makeFilter.insertAdjacentElement('afterend', modelFilterSection);
                } else {
                    filtersContainer.appendChild(modelFilterSection);
                }
            }
        }
        
        const modelFilterContent = modelFilterSection?.querySelector('.filter-content');
        if (!modelFilterContent) return;
        
        modelFilterContent.innerHTML = '';
        
        if (models.length === 0) {
            modelFilterContent.innerHTML = '<p class="no-models">Select a make to see models</p>';
            return;
        }
        
        models.forEach(model => {
            const label = document.createElement('label');
            label.innerHTML = `
                <input type="checkbox" value="${model.name}" data-filter="model"> 
                ${model.name} ${model.count ? `(${model.count})` : ''}
            `;
            modelFilterContent.appendChild(label);
        });
    }
    
    debounceFilterUpdate() {
        clearTimeout(this.filterUpdateTimeout);
        this.filterUpdateTimeout = setTimeout(() => {
            this.notifyFilterChange();
        }, 300);
    }
    
    notifyFilterChange() {
        // Emit custom event for car grid to listen to
        const event = new CustomEvent('filtersChanged', {
            detail: { filters: this.getActiveFilters() }
        });
        document.dispatchEvent(event);
    }
    
    getActiveFilters() {
        const filters = {};
        
        // Collect checkbox filters
        ['makes', 'models', 'cities', 'fuel_types', 'transmissions', 'conditions', 'body_types', 'exterior_colors'].forEach(filterType => {
            if (this.selectedFilters[filterType] && this.selectedFilters[filterType].length > 0) {
                filters[filterType] = this.selectedFilters[filterType];
            }
        });
        
        // Collect range filters
        ['price_min', 'price_max', 'year_min', 'year_max', 'kilometers_max', 'fuel_economy_min'].forEach(filterType => {
            if (this.selectedFilters[filterType] !== null && this.selectedFilters[filterType] !== undefined) {
                filters[filterType] = this.selectedFilters[filterType];
            }
        });
        
        // Collect predefined range filters
        ['price_range', 'year_range', 'kilometers_range'].forEach(filterType => {
            if (this.selectedFilters[filterType]) {
                filters[filterType] = this.selectedFilters[filterType];
            }
        });
        
        return filters;
    }
    
    // Utility methods
    formatPrice(value) {
        const price = parseInt(value);
        if (price >= 1000000) {
            return `$${(price / 1000000).toFixed(1)}M`;
        } else if (price >= 1000) {
            return `$${(price / 1000).toFixed(0)}k`;
        } else {
            return `$${price}`;
        }
    }
    
    formatMileage(value) {
        const mileage = parseInt(value);
        if (mileage >= 1000) {
            return `${(mileage / 1000).toFixed(0)}k mi`;
        } else {
            return `${mileage} mi`;
        }
    }
    
    formatKilometers(value) {
        const kilometers = parseInt(value);
        if (kilometers >= 1000) {
            return `${(kilometers / 1000).toFixed(0)}k km`;
        } else {
            return `${kilometers} km`;
        }
    }
    
    parsePrice(priceStr) {
        if (!priceStr) return null;
        
        // Remove currency symbols and commas
        const cleanStr = priceStr.replace(/[$,]/g, '');
        const price = parseFloat(cleanStr);
        
        return isNaN(price) ? null : price;
    }
    
    // Public methods for external use
    clearAllFilters() {
        // Reset all filters
        this.selectedFilters = {
            makes: [],
            models: [],
            cities: [],
            years: [],
            fuel_types: [],
            transmissions: [],
            conditions: [],
            body_types: [],
            exterior_colors: [],
            price_min: null,
            price_max: null,
            year_min: null,
            year_max: null,
            kilometers_max: null,
            fuel_economy_min: null,
            price_range: null,
            year_range: null,
            kilometers_range: null
        };
        
        // Clear all checkboxes and radio buttons
        document.querySelectorAll('input[type="checkbox"][data-filter], input[type="radio"][data-filter]').forEach(input => {
            input.checked = false;
        });
        
        // Reset sliders to default values
        this.resetSliders();
        
        // Clear price inputs
        const minPriceInput = document.getElementById('minPrice');
        const maxPriceInput = document.getElementById('maxPrice');
        if (minPriceInput) minPriceInput.value = '';
        if (maxPriceInput) maxPriceInput.value = '';
        
        // Notify change
        this.notifyFilterChange();
    }
    
    resetSliders() {
        // Reset price slider
        const priceSlider = document.getElementById('priceSlider');
        const priceValue = document.getElementById('priceValue');
        if (priceSlider && this.filterData.price_range) {
            priceSlider.value = Math.floor(this.filterData.price_range.max / 2);
            if (priceValue) {
                priceValue.textContent = this.formatPrice(priceSlider.value);
            }
        }
        
        // Reset year slider
        const yearSlider = document.getElementById('yearSlider');
        const yearValue = document.getElementById('yearValue');
        if (yearSlider && this.filterData.year_range) {
            yearSlider.value = this.filterData.year_range.max - 2;
            if (yearValue) {
                yearValue.textContent = yearSlider.value;
            }
        }
        
        // Reset kilometers slider
        const kilometersSlider = document.getElementById('kilometersSlider');
        const kilometersValue = document.getElementById('kilometersValue');
        if (kilometersSlider) {
            kilometersSlider.value = kilometersSlider.max;
            if (kilometersValue) {
                kilometersValue.textContent = this.formatKilometers(kilometersSlider.value);
            }
        }
        
        // Reset fuel economy slider
        const fuelEconomySlider = document.getElementById('fuelEconomySlider');
        const fuelEconomyValue = document.getElementById('fuelEconomyValue');
        if (fuelEconomySlider) {
            fuelEconomySlider.value = fuelEconomySlider.min;
            if (fuelEconomyValue) {
                fuelEconomyValue.textContent = fuelEconomySlider.value + ' L/100km';
            }
        }
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.dynamicFiltersManager = new DynamicFiltersManager();
});
