// Car details data
const carDetailData = {
  id: 3,
  title: "Used 2023 BMW X7",
  model: "xDrive40i Sports Activity",
  price: "$76,800",
  originalPrice: "$82,500",
  savings: "$5,700",
  mileage: "12,450 miles",
  location: "Beverly Hills, CA",
  stock: "BX7231",
  monthlyPayment: "$1,285",
  fuelEconomy: "21 CITY / 26 HWY MPG",
  images: [
    "//images.pexels.com/photos/337909/pexels-photo-337909.jpeg?auto=compress&cs=tinysrgb&w=800&h=600&fit=crop",
    "//images.pexels.com/photos/1592384/pexels-photo-1592384.jpeg?auto=compress&cs=tinysrgb&w=800&h=600&fit=crop",
    "//images.pexels.com/photos/3802510/pexels-photo-3802510.jpeg?auto=compress&cs=tinysrgb&w=800&h=600&fit=crop",
    "//images.pexels.com/photos/1719648/pexels-photo-1719648.jpeg?auto=compress&cs=tinysrgb&w=800&h=600&fit=crop",
    "//images.pexels.com/photos/2365572/pexels-photo-2365572.jpeg?auto=compress&cs=tinysrgb&w=800&h=600&fit=crop",
    "//images.pexels.com/photos/116675/pexels-photo-116675.jpeg?auto=compress&cs=tinysrgb&w=800&h=600&fit=crop",
    "//images.pexels.com/photos/1545743/pexels-photo-1545743.jpeg?auto=compress&cs=tinysrgb&w=800&h=600&fit=crop",
    "//images.pexels.com/photos/3752169/pexels-photo-3752169.jpeg?auto=compress&cs=tinysrgb&w=800&h=600&fit=crop"
  ],
  dealer: {
    name: "Premium Auto Gallery",
    rating: "4.8",
    reviews: "324",
    address: "8920 Wilshire Blvd, Beverly Hills, CA 90211",
    phone: "(310) 555-0123",
    hours: "Open until 9:00 PM"
  }
};

// Similar cars data will be provided by the template

// Image Gallery Manager
class CarDetailImageGalleryManager {
  constructor() {
    this.currentImageIndex = 0;
    this.images = this.getImagesFromDOM();
    this.init();
  }

  getImagesFromDOM() {
    // Get actual images from the thumbnail gallery
    const thumbnails = document.querySelectorAll('.car-detail-thumbnail');
    return Array.from(thumbnails).map(thumbnail => thumbnail.src);
  }

  init() {
    this.setupThumbnails();
    this.setupNavigation();
    this.setupKeyboardNavigation();
    this.updateImageCounter();
  }

  setupThumbnails() {
    const thumbnailTrack = document.getElementById('carDetailThumbnailTrack');
    const thumbnails = thumbnailTrack.querySelectorAll('.car-detail-thumbnail');
    
    thumbnails.forEach((thumbnail, index) => {
      thumbnail.addEventListener('click', () => {
        this.showImage(index);
      });
    });
  }

  setupNavigation() {
    const prevBtn = document.querySelector('.car-detail-prev-img');
    const nextBtn = document.querySelector('.car-detail-next-img');
    const fullscreenBtn = document.querySelector('.car-detail-fullscreen-btn');

    prevBtn.addEventListener('click', () => {
      this.previousImage();
    });

    nextBtn.addEventListener('click', () => {
      this.nextImage();
    });

    fullscreenBtn.addEventListener('click', () => {
      this.toggleFullscreen();
    });
  }

  setupKeyboardNavigation() {
    document.addEventListener('keydown', (e) => {
      if (e.key === 'ArrowLeft') {
        this.previousImage();
      } else if (e.key === 'ArrowRight') {
        this.nextImage();
      } else if (e.key === 'Escape') {
        this.exitFullscreen();
      }
    });
  }

  showImage(index) {
    this.currentImageIndex = index;
    const mainImage = document.getElementById('carDetailMainImage');
    const thumbnails = document.querySelectorAll('.car-detail-thumbnail');
    
    // Update main image
    mainImage.src = this.images[index];
    
    // Update thumbnail active state
    thumbnails.forEach((thumbnail, i) => {
      thumbnail.classList.toggle('car-detail-active', i === index);
    });
    
    this.updateImageCounter();
  }

  previousImage() {
    const newIndex = this.currentImageIndex === 0 
      ? this.images.length - 1 
      : this.currentImageIndex - 1;
    this.showImage(newIndex);
  }

  nextImage() {
    const newIndex = this.currentImageIndex === this.images.length - 1 
      ? 0 
      : this.currentImageIndex + 1;
    this.showImage(newIndex);
  }

  updateImageCounter() {
    const currentImageNum = document.getElementById('carDetailCurrentImageNum');
    const totalImages = document.getElementById('carDetailTotalImages');
    
    currentImageNum.textContent = this.currentImageIndex + 1;
    totalImages.textContent = this.images.length;
  }

  toggleFullscreen() {
    const mainImageContainer = document.querySelector('.car-detail-main-image-container');
    
    if (!document.fullscreenElement) {
      mainImageContainer.requestFullscreen().catch(err => {
        console.log(`Error attempting to enable fullscreen: ${err.message}`);
      });
    } else {
      document.exitFullscreen();
    }
  }

  exitFullscreen() {
    if (document.fullscreenElement) {
      document.exitFullscreen();
    }
  }
}

// Specifications Tab Manager
class CarDetailSpecsTabManager {
  constructor() {
    this.init();
  }

  init() {
    this.setupTabs();
  }

  setupTabs() {
    const tabButtons = document.querySelectorAll('.car-detail-spec-tab-btn');
    const tabContents = document.querySelectorAll('.car-detail-spec-tab-content');

    tabButtons.forEach(button => {
      button.addEventListener('click', () => {
        const targetTab = button.getAttribute('data-tab');
        
        // Remove active class from all tabs and contents
        tabButtons.forEach(btn => btn.classList.remove('car-detail-active'));
        tabContents.forEach(content => content.classList.remove('car-detail-active'));
        
        // Add active class to clicked tab and corresponding content
        button.classList.add('car-detail-active');
        document.getElementById('carDetail' + targetTab.charAt(0).toUpperCase() + targetTab.slice(1)).classList.add('car-detail-active');
      });
    });
  }
}

// Modal Manager
class CarDetailModalManager {
  constructor() {
    this.init();
  }

  init() {
    this.setupTestDriveModal();
    this.setupContactModal();
  }

  setupTestDriveModal() {
    const testDriveBtn = document.querySelector('.car-detail-test-drive-btn');
    const modal = document.getElementById('carDetailTestDriveModal');
    const closeBtn = modal.querySelector('.car-detail-close-modal');
    const cancelBtn = modal.querySelector('.car-detail-cancel-btn');
    const form = modal.querySelector('.car-detail-test-drive-form');

    testDriveBtn.addEventListener('click', () => {
      this.showModal(modal);
    });

    closeBtn.addEventListener('click', () => {
      this.hideModal(modal);
    });

    cancelBtn.addEventListener('click', () => {
      this.hideModal(modal);
    });

    // Close modal when clicking outside
    modal.addEventListener('click', (e) => {
      if (e.target === modal) {
        this.hideModal(modal);
      }
    });

    // Form submission
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      this.handleTestDriveSubmission(form);
    });

    // ESC key to close
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && modal.classList.contains('car-detail-show')) {
        this.hideModal(modal);
      }
    });
  }

  setupContactModal() {
    const contactBtn = document.querySelector('.car-detail-contact-seller-btn');
    
    contactBtn.addEventListener('click', () => {
      // For now, just show an alert
      alert('Contact functionality would open here. Phone: ' + carDetailData.dealer.phone);
    });
  }

  showModal(modal) {
    modal.classList.add('car-detail-show');
    document.body.style.overflow = 'hidden';
    
    // Focus on first input
    const firstInput = modal.querySelector('input');
    if (firstInput) {
      setTimeout(() => firstInput.focus(), 100);
    }
  }

  hideModal(modal) {
    modal.classList.remove('car-detail-show');
    document.body.style.overflow = '';
    
    // Reset form
    const form = modal.querySelector('form');
    if (form) {
      form.reset();
    }
  }

  handleTestDriveSubmission(form) {
    const formData = new FormData(form);
    const data = Object.fromEntries(formData);
    
    // Simulate form submission
    console.log('Test drive scheduled:', data);
    
    // Show success message
    alert('Test drive scheduled successfully! We will contact you soon to confirm the details.');
    
    // Hide modal
    this.hideModal(document.getElementById('carDetailTestDriveModal'));
  }
}

// Financing Calculator
class CarDetailFinancingCalculator {
  constructor() {
    this.vehiclePrice = 76800;
    this.init();
  }

  init() {
    this.setupCalculator();
  }

  setupCalculator() {
    const calculateBtn = document.querySelector('.car-detail-calculate-btn');
    
    calculateBtn.addEventListener('click', () => {
      this.calculatePayment();
    });
  }

  calculatePayment() {
    const downPayment = this.parseNumber(document.getElementById('carDetailDownPayment').value) || 10000;
    const loanTerm = parseInt(document.getElementById('carDetailLoanTerm').value) || 60;
    const interestRate = this.parseNumber(document.getElementById('carDetailInterestRate').value) || 3.9;
    
    const loanAmount = this.vehiclePrice - downPayment;
    const monthlyRate = (interestRate / 100) / 12;
    const numberOfPayments = loanTerm;
    
    // Calculate monthly payment using loan formula
    const monthlyPayment = loanAmount * 
      (monthlyRate * Math.pow(1 + monthlyRate, numberOfPayments)) / 
      (Math.pow(1 + monthlyRate, numberOfPayments) - 1);
    
    const totalAmount = monthlyPayment * numberOfPayments + downPayment;
    const totalInterest = totalAmount - this.vehiclePrice;
    
    // Update display
    document.getElementById('carDetailMonthlyPayment').textContent = '$' + Math.round(monthlyPayment).toLocaleString();
    document.getElementById('carDetailTotalInterest').textContent = '$' + Math.round(totalInterest).toLocaleString();
    document.getElementById('carDetailTotalAmount').textContent = '$' + Math.round(totalAmount).toLocaleString();
    
    // Show result
    document.getElementById('carDetailPaymentResult').style.display = 'block';
  }

  parseNumber(str) {
    if (!str) return 0;
    return parseFloat(str.replace(/[$,%]/g, ''));
  }
}

// Similar Cars Manager
class CarDetailSimilarCarsManager {
  constructor() {
    this.init();
  }

  init() {
    this.renderSimilarCars();
  }

  renderSimilarCars() {
    const container = document.getElementById('carDetailSimilarCarsGrid');
    
    // Check if similarCarData is available
    if (typeof similarCarData === 'undefined' || !similarCarData) {
      console.warn('Similar car data not available');
      container.innerHTML = '<p class="text-center text-gray-500">No similar vehicles available</p>';
      return;
    }
    
    container.innerHTML = similarCarData.map(car => this.createCarCard(car)).join('');
    
    // Add event listeners
    container.querySelectorAll('.car-detail-similar-view-btn').forEach((btn, index) => {
      btn.addEventListener('click', () => {
        // Navigate to car details using the correct URL pattern
        if (typeof similarCarData !== 'undefined' && similarCarData[index] && similarCarData[index].slug) {
          window.location.href = `/car/${similarCarData[index].slug}/`;
        } else {
          console.log('View car:', typeof similarCarData !== 'undefined' ? similarCarData[index] : 'Data not available');
          alert('Car details not available');
        }
      });
    });

    container.querySelectorAll('.car-detail-similar-compare-btn').forEach((btn, index) => {
      btn.addEventListener('click', () => {
        if (typeof similarCarData !== 'undefined' && similarCarData[index]) {
          console.log('Compare car:', similarCarData[index]);
          alert('Added ' + similarCarData[index].title + ' to comparison');
        } else {
          alert('Car comparison not available');
        }
      });
    });
  }

  createCarCard(car) {
    return `
      <div class="car-detail-similar-car-card">
        <div class="car-detail-similar-car-image">
          <img src="${car.image}" alt="${car.title}">
        </div>
        <div class="car-detail-similar-car-details">
          <h4>${car.title}</h4>
          <p class="car-detail-similar-car-model">${car.model}</p>
          <p class="car-detail-similar-car-price">${car.price}</p>
          <p class="car-detail-similar-car-info">
            ${car.mileage} • ${car.location}
          </p>
          <div class="car-detail-similar-car-actions">
            <button class="car-detail-similar-view-btn">View Details</button>
            <button class="car-detail-similar-compare-btn">Compare</button>
          </div>
        </div>
      </div>
    `;
  }
}

// Action Handlers
class CarDetailActionHandlers {
  constructor() {
    this.init();
  }

  init() {
    this.setupQuickActions();
    this.setupMediaButtons();
  }

  setupQuickActions() {
    // Save button
    const saveBtn = document.querySelector('.car-detail-save-btn');
    saveBtn.addEventListener('click', () => {
      const isSaved = saveBtn.classList.toggle('car-detail-saved');
      const icon = saveBtn.querySelector('i');
      const text = saveBtn.querySelector('span');
      
      if (isSaved) {
        icon.className = 'ri-save-3-fill';
        text.textContent = 'Saved';
        saveBtn.style.color = '#34a853';
      } else {
        icon.className = 'ri-save-3-line';
        text.textContent = 'Save';
        saveBtn.style.color = '';
      }
      
      console.log('Car saved:', isSaved);
    });

    // Compare button
    const compareBtn = document.querySelector('.car-detail-compare-btn');
    compareBtn.addEventListener('click', () => {
      console.log('Add to comparison');
      alert('Added to comparison list');
    });

    // Share button
    const shareBtn = document.querySelector('.car-detail-share-btn');
    shareBtn.addEventListener('click', () => {
      if (navigator.share) {
        navigator.share({
          title: carDetailData.title,
          text: `Check out this ${carDetailData.title} for ${carDetailData.price}`,
          url: window.location.href
        });
      } else {
        // Fallback - copy to clipboard
        navigator.clipboard.writeText(window.location.href).then(() => {
          alert('Link copied to clipboard!');
        });
      }
    });
  }

  setupMediaButtons() {
    const videoBtn = document.querySelector('.car-detail-video-btn');
    const vrBtn = document.querySelector('.car-detail-vr-btn');

    videoBtn.addEventListener('click', () => {
      console.log('Play video tour');
      alert('Video tour would start here');
    });

    vrBtn.addEventListener('click', () => {
      console.log('Start 360° view');
      alert('360° view would open here');
    });
  }
}

// Performance Optimization
class CarDetailPerformanceOptimizer {
  constructor() {
    this.init();
  }

  init() {
    this.lazyLoadImages();
    this.optimizeAnimations();
  }

  lazyLoadImages() {
    // Implement lazy loading for similar car images
    const imageObserver = new IntersectionObserver((entries, observer) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          const img = entry.target;
          img.src = img.dataset.src;
          img.classList.remove('car-detail-lazy');
          observer.unobserve(img);
        }
      });
    });

    document.querySelectorAll('img[data-src]').forEach(img => {
      imageObserver.observe(img);
    });
  }

  optimizeAnimations() {
    // Reduce animations for users who prefer reduced motion
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      document.documentElement.style.setProperty('--car-detail-animation-duration', '0.01ms');
    }
  }
}

// Initialize all managers when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
  // Core functionality
  const imageGallery = new CarDetailImageGalleryManager();
  const specsTab = new CarDetailSpecsTabManager();
  const modal = new CarDetailModalManager();
  const calculator = new CarDetailFinancingCalculator();
  const similarCars = new CarDetailSimilarCarsManager();
  
  // UI enhancements
  const actionHandlers = new CarDetailActionHandlers();
  const performance = new CarDetailPerformanceOptimizer();
  
  // Global accessibility
  setupCarDetailAccessibility();
  
  // Analytics and tracking (placeholder)
  trackCarDetailPageView();
});

// Accessibility enhancements
function setupCarDetailAccessibility() {
  // Add skip links
  const skipLink = document.createElement('a');
  skipLink.href = '#car-detail-main-content';
  skipLink.textContent = 'Skip to main content';
  skipLink.className = 'car-detail-skip-link';
  skipLink.style.cssText = `
    position: absolute;
    top: -40px;
    left: 6px;
    background: #4d78bc;
    color: white;
    padding: 8px;
    text-decoration: none;
    border-radius: 0 0 6px 6px;
    z-index: 9999;
  `;
  
  skipLink.addEventListener('focus', () => {
    skipLink.style.top = '0';
  });
  
  skipLink.addEventListener('blur', () => {
    skipLink.style.top = '-40px';
  });
  
  document.body.insertBefore(skipLink, document.body.firstChild);
  
  // Add main content landmark
  const mainContent = document.querySelector('.car-detail-content-wrapper');
  if (mainContent) {
    mainContent.id = 'car-detail-main-content';
    mainContent.setAttribute('role', 'main');
  }
}

// Analytics placeholder
function trackCarDetailPageView() {
  console.log('Car Detail Page view tracked:', {
    page: 'car-details',
    carId: carDetailData.id,
    carTitle: carDetailData.title,
    timestamp: new Date().toISOString()
  });
}

// Error handling
window.addEventListener('error', (e) => {
  console.error('Car Detail JavaScript error:', e.error);
  // In production, you would send this to your error tracking service
});

// Unhandled promise rejections
window.addEventListener('unhandledrejection', (e) => {
  console.error('Car Detail Unhandled promise rejection:', e.reason);
  // In production, you would send this to your error tracking service
});

// Export for testing (if needed)
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    CarDetailImageGalleryManager,
    CarDetailSpecsTabManager,
    CarDetailModalManager,
    CarDetailFinancingCalculator,
    CarDetailSimilarCarsManager,
    carDetailData,
    similarCarData
  };
}