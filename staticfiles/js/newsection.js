// Car brands data with emojis as logos
const carBrands = [
  { name: "Toyota", image: "/images/cars/toyota-logos-brands-10.png" },
  { name: "Nissan", image: "/images/cars/pngwing.com.png" },
  { name: "Hyundai", image: "/images/cars/hyundai-logo-white.jpg" },
  { name: "Mercedes-Benz", image: "/images/cars/Mercedes-Benz-Logo.png" },
  { name: "BMW", image: "/images/cars/BMW-Logo.png" },
  { name: "Chevrolet", image: "/images/cars/Chevrolet-Logo-2010.png" },
  { name: "Ford", image: "/images/cars/Ford-Logo-1965-present.png" },
  { name: "Honda", image: "/images/cars/wp3351340.png" },
  { name: "Lexus", image: "/images/cars/Lexus-Logo.png" },
  { name: "Audi", image: "/images/cars/Audi-Symbol.png" },
  { name: "KIA", image: "/images/cars/Kia-Logo.png" },
  { name: "Mitsubishi", image: "/images/cars/Mitsubishi-emblem-1024x768.png" },
  { name: "BYD", image: "/images/cars/byd-logo-1-01.jpg" },
  { name: "Bestune", image: "/images/cars/bestune-logo-600x1100-show.png" },
  { name: "DFSK", image: "/images/cars/DFSK-logo-2025-klein.png" },
  { name: "Mahindra", image: "/images/cars/Mahindra-Mahindra-New-Logo.png" },
  { name: "Volkswagen", image: "/images/cars/brand-volkswagen-png-logo-17.png" },
  {
    name: "Infiniti",
    image:
      "/images/cars/257-2576555_infiniti-car-logo-infiniti-car-logo-png-transparent.png",
  },
  { name: "Jeep", image: "/images/cars/Jeep_logo.png" },
  { name: "Land Rover", image: "/images/cars/Land-Rover-Logo-1986-present.png" },
  { name: "Porsche", image: "/images/cars/Porsche-Logo.png" },
  { name: "Maserati", image: "/images/cars/Maserati-Symbol.png" },
  { name: "Ferrari", image: "/images/cars/Ferrari-Logo.png" },
  { name: "Lamborghini", image: "/images/cars/lamborghini_PNG10709.png" },
  { name: "Bentley", image: "/images/cars/Bentley-Symbol.png" },
  {
    name: "Rolls-Royce",
    image:
      "/images/cars/rolls-royce-brand-logo-car-symbol-black-design-british-automobile-illustration-free-vector.jpg",
  },
  { name: "McLaren", image: "/images/cars/Mclaren_PNG49.png" },
  {
    name: "Bugatti",
    image: "/images/cars/5a953454320e8d398b2dcc5babf78014.jpg",
  },
  { name: "Pagani", image: "/images/cars/419-4194037_pagani-logo-png.png" },
  {
    name: "Koenigsegg",
    image: "/images/cars/f2bf43_179328483f634f938a5a638b192b6005~mv2.png",
  },
  { name: "Tesla", image: "/images/cars/tesla-logo-7408969_1280.png" },
  { name: "Lucid", image: "/images/cars/lucid-motors3169.jpg" },
  { name: "Rivian", image: "/images/cars/Rivian-Logo-Electric.png" },
  { name: "Polestar", image: "/images/cars/polestar.png" },
  { name: "Genesis", image: "/images/cars/Genesis-Logo.png" },
  { name: "Acura", image: "/images/cars/Acura-Embleme.jpg" },
  { name: "Cadillac", image: "/images/cars/Cadillac-Logo-PNG-Isolated-HD.png" },
  { name: "Lincoln", image: "/images/cars/10418.jpg" },
  { name: "Chrysler", image: "/images/cars/Chrysler-Emblem.png" },
  { name: "Dodge", image: "/images/cars/dodge-logo-black-and-white.png" },
  { name: "Ram", image: "/images/cars/Los-Angeles-Rams-logo.png" },
  { name: "GMC", image: "/images/cars/gmc-logo-vector-21.jpg" },
];

// Cars for sale data
const carsForSale = [
  {
    id: 1,
    title: "New Mercedes-Benz S-Class S 580 4MATIC 2025",
    price: "AED 650,000",
    image:
      "//images.pexels.com/photos/170811/pexels-photo-170811.jpeg?auto=compress&cs=tinysrgb&w=800",
    specs: ["0 KM", "Automatic", "2025"],
    badge: "20",
  },
  {
    id: 2,
    title: "New Mitsubishi Attrage 2022",
    price: "AED 22,299",
    image:
      "//images.pexels.com/photos/248747/pexels-photo-248747.jpeg?auto=compress&cs=tinysrgb&w=800",
    specs: ["87,701 KM", "Automatic", "2022"],
    badge: "4",
  },
  {
    id: 3,
    title: "New Mercedes-Benz V Class 2025",
    price: "AED 895,000",
    image:
      "//images.pexels.com/photos/244206/pexels-photo-244206.jpeg?auto=compress&cs=tinysrgb&w=800",
    specs: ["0 KM", "Automatic", "2025"],
    badge: "10",
  },
  {
    id: 4,
    title: "New Nissan Sunny 2025",
    price: "AED 44,899",
    image:
      "//images.pexels.com/photos/1592384/pexels-photo-1592384.jpeg?auto=compress&cs=tinysrgb&w=800",
    specs: ["22 KM", "Automatic", "2025"],
    badge: "8",
  },
  {
    id: 5,
    title: "New Infiniti Q50 2023",
    price: "AED 79,900",
    image:
      "//images.pexels.com/photos/1545743/pexels-photo-1545743.jpeg?auto=compress&cs=tinysrgb&w=800",
    specs: ["68,659 KM", "Automatic", "2023"],
    badge: "1",
  },
  {
    id: 6,
    title: "New Kia K3 1.6L LX 2025",
    price: "AED 62,500",
    image:
      "//images.pexels.com/photos/193999/pexels-photo-193999.jpeg?auto=compress&cs=tinysrgb&w=800",
    specs: ["0 KM", "Automatic", "2025"],
    badge: "20",
  },
  {
    id: 7,
    title: "New JAC JS3 2026",
    price: "AED 41,900",
    image:
      "//images.pexels.com/photos/3802510/pexels-photo-3802510.jpeg?auto=compress&cs=tinysrgb&w=800",
    specs: ["948 KM", "Automatic", "2026"],
    badge: "22",
  },
  {
    id: 8,
    title: "New Toyota Corolla 2023",
    price: "AED 51,899",
    image:
      "//images.pexels.com/photos/1974596/pexels-photo-1974596.jpeg?auto=compress&cs=tinysrgb&w=800",
    specs: ["59,562 KM", "Automatic", "2023"],
    badge: "2",
  },
];

// Videos data
const videosData = [
  {
    id: 1,
    title: "We Took On 15 Insane Challenges Each in Audi RS M...",
    thumbnail: "audi-episode",
    overlayText: "The Ultimate Audi Episode",
    channel: "Cars Portal",
    duration: "45:33 min",
    date: "24 July 2025",
    videoUrl: "#",
  },
  {
    id: 2,
    title: "New 2025 C63 S Hybrid - Love It or Hate It?",
    thumbnail: "c63-hybrid",
    overlayText: "GoodBye V8 ? Hello E-Hybrid?",
    channel: "Cars Portal",
    duration: "15:59 min",
    date: "22 July 2025",
    videoUrl: "#",
  },
  {
    id: 3,
    title: "The Fastest SUV in the world? Audi RSQ8 2025",
    thumbnail: "rsq8-suv",
    overlayText: "Fastest SUV in the world ? The Audi RSQ8",
    channel: "Cars Portal",
    duration: "07:52 min",
    date: "20 July 2025",
    videoUrl: "#",
  },
];

let selectedBrand = "";
let showingAllBrands = false;
let selectedPriceRange = "";
let currentCarouselPosition = 0;

// Initialize the page
document.addEventListener("DOMContentLoaded", function () {
  renderBrands();
  populateModalBrands();
  renderVideos();
  renderCarsForSale();
  initializeCarsTabs();
});

// Scroll to search section
function scrollToSearch() {
  document.getElementById("searchSection").scrollIntoView({
    behavior: "smooth",
    block: "start",
  });
}

// Render brands grid
function renderBrands() {
  const brandsGrid = document.getElementById("brandsGrid");
  const showMoreBtn = document.getElementById("showMoreBtn");

  const brandsToShow = showingAllBrands ? carBrands : carBrands.slice(0, 16);

  brandsGrid.innerHTML = "";

  brandsToShow.forEach((brand, index) => {
    const brandItem = document.createElement("div");
    brandItem.className = "brand-item";
    brandItem.style.animationDelay = `${index * 0.05}s`;
    brandItem.onclick = () => selectBrand(brand.name);

    brandItem.innerHTML = `
            <div class="brand-logo">
                <img src="${brand.image}" alt="${brand.name}" />
            </div>
            <div class="brand-name">${brand.name}</div>
        `;

    brandsGrid.appendChild(brandItem);
  });

  // Update show more button
  if (showingAllBrands) {
    showMoreBtn.textContent = "Show Less";
    showMoreBtn.style.background = "#1e40af";
    showMoreBtn.style.color = "white";
    showMoreBtn.style.borderColor = "#1e40af";
  } else {
    showMoreBtn.textContent = "Show More";
    showMoreBtn.style.background = "#f3f4f6";
    showMoreBtn.style.color = "#374151";
    showMoreBtn.style.borderColor = "#e5e7eb";
  }
}

// Render cars for sale
function renderCarsForSale() {
  const carsCarousel = document.getElementById("carsCarousel");
  carsCarousel.innerHTML = "";

  carsForSale.forEach((car, index) => {
    const carCard = document.createElement("div");
    carCard.className = "car-card";
    carCard.style.animationDelay = `${index * 0.1}s`;
    carCard.onclick = () => viewCarDetails(car.id);

    carCard.innerHTML = `
            <div class="car-image" style="background-image: url('${
              car.image
            }')">
                <div class="car-badge">${car.badge}</div>
            </div>
            <div class="car-info">
                <div class="car-title">${car.title}</div>
                <div class="car-price">${car.price}</div>
                <div class="car-specs">
                    ${car.specs.map((spec) => `<span>${spec}</span>`).join(" | ")}
                </div>
            </div>
        `;

    carsCarousel.appendChild(carCard);
  });
}

// Initialize cars tabs
function initializeCarsTabs() {
  const tabButtons = document.querySelectorAll(".tab-btn");

  tabButtons.forEach((button) => {
    button.addEventListener("click", function () {
      // Remove active class from all tabs
      tabButtons.forEach((btn) => btn.classList.remove("active"));

      // Add active class to clicked tab
      this.classList.add("active");

      // Here you would typically filter the cars based on the selected tab
      // For now, we'll just show the same cars
      renderCarsForSale();
    });
  });
}

// Cars carousel navigation
function scrollCarsCarousel(direction) {
  const carousel = document.getElementById("carsCarousel");
  const cardWidth = 280 + 24; // card width + gap
  const maxScroll = (carsForSale.length - 4) * cardWidth;

  currentCarouselPosition += direction * cardWidth * 2;

  if (currentCarouselPosition < 0) {
    currentCarouselPosition = 0;
  } else if (currentCarouselPosition > maxScroll) {
    currentCarouselPosition = maxScroll;
  }

  carousel.scrollTo({
    left: currentCarouselPosition,
    behavior: "smooth",
  });
}

// Render videos grid
function renderVideos() {
  const videosGrid = document.getElementById("videosGrid");
  videosGrid.innerHTML = "";

  videosData.forEach((video, index) => {
    const videoCard = document.createElement("div");
    videoCard.className = "video-card";
    videoCard.style.animationDelay = `${index * 0.1}s`;
    videoCard.onclick = () => playVideo(video.videoUrl);

    videoCard.innerHTML = `
            <div class="video-thumbnail ${video.thumbnail}">
                <div class="play-button">
                    <div class="play-icon"></div>
                </div>
                <div class="video-overlay-text">${video.overlayText}</div>
            </div>
            <div class="video-info">
                <div class="video-title">${video.title}</div>
                <div class="video-meta">
                    <div class="video-channel">
                        <div class="channel-icon">Y</div>
                        <span>${video.channel}</span>|
                    </div>
                    <span class="video-duration">${video.duration}</span>|
                    <span class="video-date">${video.date}</span>|
                </div>
            </div>
        `;

    videosGrid.appendChild(videoCard);
  });
}

// Toggle show more/less brands
function toggleShowMore() {
  showingAllBrands = !showingAllBrands;
  renderBrands();
}

// Open brand selection modal
function openBrandModal() {
  const modal = document.getElementById("brandModal");
  modal.classList.add("active");
  document.body.style.overflow = "hidden";
  document.getElementById("modalSearch").focus();
}

// Close brand selection modal
function closeBrandModal() {
  const modal = document.getElementById("brandModal");
  modal.classList.remove("active");
  document.body.style.overflow = "auto";
  document.getElementById("modalSearch").value = "";
  populateModalBrands();
}

// Populate modal brands list
function populateModalBrands(filteredBrands = carBrands) {
  const modalBrandsList = document.getElementById("modalBrandsList");
  modalBrandsList.innerHTML = "";

  filteredBrands.forEach((brand) => {
    const brandItem = document.createElement("div");
    brandItem.className = "modal-brand-item";
    brandItem.textContent = brand.name;
    brandItem.onclick = () => selectBrandFromModal(brand.name);
    modalBrandsList.appendChild(brandItem);
  });

  if (filteredBrands.length === 0) {
    const noBrands = document.createElement("div");
    noBrands.className = "modal-brand-item";
    noBrands.textContent = "No brands found";
    noBrands.style.color = "#6b7280";
    noBrands.style.fontStyle = "italic";
    modalBrandsList.appendChild(noBrands);
  }
}

// Filter brands in modal
function filterBrands() {
  const searchTerm = document.getElementById("modalSearch").value.toLowerCase();
  const filteredBrands = carBrands.filter((brand) =>
    brand.name.toLowerCase().includes(searchTerm)
  );
  populateModalBrands(filteredBrands);
}

// Select brand from modal
function selectBrandFromModal(brandName) {
  selectedBrand = brandName;
  document.getElementById("brandInput").value = brandName;
  closeBrandModal();
}

// Select brand from grid
function selectBrand(brandName) {
  selectedBrand = brandName;
  document.getElementById("brandInput").value = brandName;

  // Scroll to search section
  document.getElementById("searchSection").scrollIntoView({
    behavior: "smooth",
    block: "start",
  });
}

// Toggle price dropdown
function togglePriceDropdown() {
  const btn = document.getElementById("priceDropdownBtn");
  const panel = document.getElementById("priceDropdownPanel");

  btn.classList.toggle("active");
  panel.classList.toggle("active");
}

// Reset price selection
function resetPriceSelection() {
  document.getElementById("minPriceInput").value = "";
  document.getElementById("maxPriceInput").value = "";

  // Uncheck all radio buttons
  const radioButtons = document.querySelectorAll('input[name="priceRange"]');
  radioButtons.forEach((radio) => (radio.checked = false));

  selectedPriceRange = "";
  document.getElementById("priceDropdownText").textContent = "Price Range";
}

// Apply price selection
function applyPriceSelection() {
  const minPrice = document.getElementById("minPriceInput").value;
  const maxPrice = document.getElementById("maxPriceInput").value;
  const selectedRadio = document.querySelector(
    'input[name="priceRange"]:checked'
  );

  let displayText = "Price Range";

  if (minPrice && maxPrice) {
    displayText = `${minPrice} - ${maxPrice} AED`;
    selectedPriceRange = `${minPrice}-${maxPrice}`;
  } else if (minPrice) {
    displayText = `${minPrice}+ AED`;
    selectedPriceRange = `${minPrice}+`;
  } else if (maxPrice) {
    displayText = `Up to ${maxPrice} AED`;
    selectedPriceRange = `0-${maxPrice}`;
  } else if (selectedRadio) {
    displayText = `${selectedRadio.value} AED`;
    selectedPriceRange = selectedRadio.value;
  }

  document.getElementById("priceDropdownText").textContent = displayText;
  togglePriceDropdown();
}

// Close price dropdown when clicking outside
document.addEventListener("click", function (e) {
  const dropdown = document.querySelector(".price-dropdown");
  const panel = document.getElementById("priceDropdownPanel");
  const btn = document.getElementById("priceDropdownBtn");

  if (!dropdown.contains(e.target)) {
    panel.classList.remove("active");
    btn.classList.remove("active");
  }
});

// Handle radio button selection
document.addEventListener("change", function (e) {
  if (e.target.name === "priceRange") {
    // Clear manual inputs when radio is selected
    document.getElementById("minPriceInput").value = "";
    document.getElementById("maxPriceInput").value = "";
  }
});

// Handle manual input changes
document.addEventListener("DOMContentLoaded", function () {
  const minPriceInput = document.getElementById("minPriceInput");
  const maxPriceInput = document.getElementById("maxPriceInput");

  if (minPriceInput) {
    minPriceInput.addEventListener("input", function () {
      // Uncheck radio buttons when manual input is used
      const radioButtons = document.querySelectorAll(
        'input[name="priceRange"]'
      );
      radioButtons.forEach((radio) => (radio.checked = false));
    });
  }

  if (maxPriceInput) {
    maxPriceInput.addEventListener("input", function () {
      // Uncheck radio buttons when manual input is used
      const radioButtons = document.querySelectorAll(
        'input[name="priceRange"]'
      );
      radioButtons.forEach((radio) => (radio.checked = false));
    });
  }
});

// Perform search
function performSearch() {
  const brand = document.getElementById("brandInput").value;
  const priceRange = selectedPriceRange;

  if (!brand && !priceRange) {
    alert("Please select a car brand or price range to search.");
    return;
  }

  let searchSummary = "Search completed for cars";
  if (brand) {
    searchSummary += ` from ${brand}`;
  }
  if (priceRange) {
    searchSummary += ` in price range ${priceRange} AED`;
  }

  // Show search results (placeholder)
  alert(
    `${searchSummary}.\n\nThis is a demo. In a real application, this would redirect to search results page.`
  );
}

// View car details
function viewCarDetails(carId) {
  alert(
    `Viewing details for car ID: ${carId}. In a real application, this would redirect to the car details page.`
  );
}

// View all cars
function viewAllCars() {
  alert(
    "Showing all cars for sale... In a real application, this would redirect to the cars listing page."
  );
}

// Video functions
function playVideo(videoUrl) {
  // In a real application, this would play the video or redirect to YouTube
  alert(
    "Playing video... In a real application, this would open the video player or redirect to YouTube."
  );
  console.log("Playing video:", videoUrl);
}

function subscribeYoutube() {
  // In a real application, this would redirect to the YouTube channel
  alert("Redirecting to Cars Portal YouTube channel...");
    // window.open('https://youtube.com/carsportal', '_blank');
}

function viewAllVideos() {
  // In a real application, this would redirect to a videos page
  alert(
    "Showing all videos... In a real application, this would redirect to the videos page."
  );
}

// News functions
function viewAllNews() {
  alert(
    "Showing all news articles... In a real application, this would redirect to the news page."
  );
}

// Keyboard navigation for modal
document.addEventListener("keydown", function (e) {
  const modal = document.getElementById("brandModal");
  if (modal.classList.contains("active")) {
    if (e.key === "Escape") {
      closeBrandModal();
    }
  }
});

// Close modal when clicking outside
document.getElementById("brandModal").addEventListener("click", function (e) {
  if (e.target === this) {
    closeBrandModal();
  }
});

// Smooth scrolling for all anchor links
document.querySelectorAll('a[href^="#"]').forEach((anchor) => {
  anchor.addEventListener("click", function (e) {
    e.preventDefault();
    const target = document.querySelector(this.getAttribute("href"));
    if (target) {
      target.scrollIntoView({
        behavior: "smooth",
        block: "start",
      });
    }
  });
});

// Add loading animation for search
function showLoading() {
  const searchBtn = document.querySelector(".search-btn");
  const originalText = searchBtn.textContent;
  searchBtn.textContent = "Searching...";
  searchBtn.disabled = true;

  setTimeout(() => {
    searchBtn.textContent = originalText;
    searchBtn.disabled = false;
  }, 1500);
}

// Enhanced search function with loading
function performSearchWithLoading() {
  const brand = document.getElementById("brandInput").value;
  const priceRange = selectedPriceRange;

  if (!brand && !priceRange) {
    alert("Please select a car brand or price range to search.");
    return;
  }

  showLoading();

  setTimeout(() => {
    let searchSummary = "Search completed for cars";
    if (brand) {
      searchSummary += ` from ${brand}`;
    }
    if (priceRange) {
      searchSummary += ` in price range ${priceRange} AED`;
    }

    alert(
      `${searchSummary}!\n\nFound 25+ matching vehicles. In a real application, you would see the results page now.`
    );
  }, 1500);
}

// Add smooth scrolling animation
function addScrollAnimation() {
  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.style.opacity = "1";
        entry.target.style.transform = "translateY(0)";
      }
    });
  });

  document
    .querySelectorAll(".video-card, .brand-item, .car-card, .news-item")
    .forEach((el) => {
      observer.observe(el);
    });
}

// Initialize animations
document.addEventListener("DOMContentLoaded", function () {
  setTimeout(addScrollAnimation, 100);
});
