// Car brands data with images
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

// Category data for different filter types
const categoryData = {
  "body-style": [
    {
      name: "SUV",
      icon: "/images/cars/SUV-Car-PNG-Pic.png",
    },
    {
      name: "Sedan",
      icon: "/images/cars/Sedan-Car.png",
    },
    {
      name: "Coupe",
      icon: "/images/cars/purepng.com-grey-mercedes-benz-c-class-coupe-carcarvehicletransportmercedes-benz-9615246453744edlm.png",
    },
    {
      name: "Hatchback",
      icon: "/images/cars/Done-SuzukiBalenoFront45ºV2.png",
    },
    {
      name: "Convertible",
      icon: "/images/cars/Convertible-Car-PNG-Download-Image.png",
    },
    {
      name: "Pickup Truck",
      icon: "/images/cars/pickup_truck_PNG16300.png",
    },
    {
      name: "Wagon",
      icon: "/images/cars/Mercedes-Benz-G-Class-Transparent-PNG.png",
    },
    {
      name: "Van",
      icon: "/images/cars/van-png-hd-toyota-png-hd-580.png",
    },
    {
      name: "Truck",
      icon: "/images/cars/truck_PNG16252.png",
    },
    {
      name: "Bus",
      icon: "/images/cars/bus_PNG8615.png",
    },
    {
      name: "Other",
      icon: "/images/cars/steering_wheel_PNG102832.png",
    },
  ],
  "fuel-type": [
    { name: "Gasoline", icon: "/images/cars/897482.png" },
    { name: "Diesel", icon: "/images/cars/2006812.png" },
    { name: "Hybrid", icon: "/images/cars/902566.png" },
    { name: "Electric", icon: "/images/cars/589799-200.png" },
    { name: "CNG", icon: "/images/cars/natural-gas-icon-png-10.png" },
    { name: "LPG", icon: "/images/cars/propane-icon-30.png" },
  ],
  transmission: [
    { name: "Automatic", icon: "/images/cars/6792345.png" },
    { name: "Manual", icon: "/images/cars/55205.png" },
    { name: "CVT", icon: "/images/cars/pngtree-gears-flat-icon-png-image_9064366.png" },
    { name: "Semi-Automatic", icon: "/images/cars/3154721.png" },
  ],
  year: [
    { name: "2025", icon: "/images/cars/year-icon-png-1.png" },
    { name: "2024", icon: "/images/cars/year-icon-png-1.png" },
    { name: "2023", icon: "/images/cars/year-icon-png-1.png" },
    { name: "2022", icon: "/images/cars/year-icon-png-1.png" },
    { name: "2021", icon: "/images/cars/year-icon-png-1.png" },
    { name: "2020", icon: "/images/cars/year-icon-png-1.png" },
    { name: "2019", icon: "/images/cars/year-icon-png-1.png" },
    { name: "2018", icon: "/images/cars/year-icon-png-1.png" },
    { name: "Older", icon: "/images/cars/year-icon-png-1.png" },
  ],
  city: [
    { name: "Dubai", icon: "/images/cars/courthouse-clipart-vector-14.png" },
    { name: "Abu Dhabi", icon: "/images/cars/courthouse-clipart-vector-14.png" },
    { name: "Sharjah", icon: "/images/cars/courthouse-clipart-vector-14.png" },
    { name: "Ajman", icon: "/images/cars/courthouse-clipart-vector-14.png" },
    { name: "Ras Al Khaimah", icon: "/images/cars/courthouse-clipart-vector-14.png" },
    { name: "Fujairah", icon: "/images/cars/courthouse-clipart-vector-14.png" },
    { name: "Umm Al Quwain", icon: "/images/cars/courthouse-clipart-vector-14.png" },
  ],
  budget: [
    { name: "Under 20,000 AED", icon: "/images/cars/pngtree-budget-line-icon-png-image_6620500.png" },
    { name: "20,000 - 50,000 AED", icon: "/images/cars/pngtree-budget-line-icon-png-image_6620500.png" },
    { name: "50,000 - 100,000 AED", icon: "/images/cars/pngtree-budget-line-icon-png-image_6620500.png" },
    { name: "100,000 - 200,000 AED", icon: "/images/cars/pngtree-budget-line-icon-png-image_6620500.png" },
    { name: "200,000 - 500,000 AED", icon: "/images/cars/pngtree-budget-line-icon-png-image_6620500.png" },
    { name: "Above 500,000 AED", icon: "/images/cars/pngtree-budget-line-icon-png-image_6620500.png" },
  ],
};

// Used cars for sale data
const usedCarsForSale = [
  {
    id: 1,
    title: "Used Mercedes-Benz C-Class C 200 2022",
    price: "AED 85,000",
    image:
      "//images.pexels.com/photos/170811/pexels-photo-170811.jpeg?auto=compress&cs=tinysrgb&w=800",
    specs: ["45,000 KM", "Automatic", "2022"],
    badge: "Verified",
  },
  {
    id: 2,
    title: "Used Toyota Camry 2021",
    price: "AED 67,500",
    image:
      "//images.pexels.com/photos/248747/pexels-photo-248747.jpeg?auto=compress&cs=tinysrgb&w=800",
    specs: ["32,000 KM", "Automatic", "2021"],
    badge: "Certified",
  },
  {
    id: 3,
    title: "Used BMW X5 2023",
    price: "AED 295,000",
    image:
      "//images.pexels.com/photos/244206/pexels-photo-244206.jpeg?auto=compress&cs=tinysrgb&w=800",
    specs: ["18,500 KM", "Automatic", "2023"],
    badge: "Premium",
  },
  {
    id: 4,
    title: "Used Nissan Altima 2020",
    price: "AED 42,000",
    image:
      "//images.pexels.com/photos/1592384/pexels-photo-1592384.jpeg?auto=compress&cs=tinysrgb&w=800",
    specs: ["75,000 KM", "Automatic", "2020"],
    badge: "Good Deal",
  },
  {
    id: 5,
    title: "Used Honda Civic 2022",
    price: "AED 54,900",
    image:
      "//images.pexels.com/photos/1545743/pexels-photo-1545743.jpeg?auto=compress&cs=tinysrgb&w=800",
    specs: ["28,000 KM", "Manual", "2022"],
    badge: "Inspected",
  },
  {
    id: 6,
    title: "Used Hyundai Elantra 2023",
    price: "AED 59,500",
    image:
      "//images.pexels.com/photos/193999/pexels-photo-193999.jpeg?auto=compress&cs=tinysrgb&w=800",
    specs: ["15,000 KM", "Automatic", "2023"],
    badge: "Low KM",
  },
  {
    id: 7,
    title: "Used Ford Explorer 2021",
    price: "AED 125,000",
    image:
      "//images.pexels.com/photos/3802510/pexels-photo-3802510.jpeg?auto=compress&cs=tinysrgb&w=800",
    specs: ["48,000 KM", "Automatic", "2021"],
    badge: "Family SUV",
  },
  {
    id: 8,
    title: "Used Chevrolet Malibu 2022",
    price: "AED 48,999",
    image:
      "//images.pexels.com/photos/1974596/pexels-photo-1974596.jpeg?auto=compress&cs=tinysrgb&w=800",
    specs: ["38,000 KM", "Automatic", "2022"],
    badge: "Warranty",
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
let activeCategory = "body-style";

// Initialize the page
document.addEventListener("DOMContentLoaded", function () {
  renderBrands();
  populateModalBrands();
  renderVideos();
  renderUsedCarsForSale();
  initializeUsedCarsTabs();
  renderCategoryContent();
  initializeCategoryTabs();
});

// Scroll to search section
function scrollToSearch() {
  document.getElementById("searchSection").scrollIntoView({
    behavior: "smooth",
    block: "start",
  });
}

// Render category content
function renderCategoryContent() {
  const categoryContent = document.getElementById("categoryContent");
  const categories = categoryData[activeCategory];

  const categoryGrid = document.createElement("div");
  categoryGrid.className = "category-grid";

  categories.forEach((category, index) => {
    const categoryItem = document.createElement("div");
    categoryItem.className = "category-item";
    categoryItem.style.animationDelay = `${index * 0.05}s`;
    categoryItem.onclick = () => selectCategory(category.name);

    categoryItem.innerHTML = `
  <div class="category-icon">
    ${
      category.icon.startsWith("http") ||
      category.icon.endsWith(".png") ||
      category.icon.endsWith(".jpg") ||
      category.icon.endsWith(".jpeg")
        ? `<img src="${category.icon}" alt="${category.name}" />`
        : `<span style="font-size: 24px;">${category.icon}</span>`
    }
  </div>
  <div class="category-name">${category.name}</div>
`;

    categoryGrid.appendChild(categoryItem);
  });

  categoryContent.innerHTML = "";
  categoryContent.appendChild(categoryGrid);
}

// Initialize category tabs
function initializeCategoryTabs() {
  const tabButtons = document.querySelectorAll(".category-tab-btn");

  tabButtons.forEach((button) => {
    button.addEventListener("click", function () {
      // Remove active class from all tabs
      tabButtons.forEach((btn) => btn.classList.remove("active"));

      // Add active class to clicked tab
      this.classList.add("active");

      // Update active category
      activeCategory = this.getAttribute("data-tab");

      // Render category content
      renderCategoryContent();
    });
  });
}

// Select category
function selectCategory(categoryName) {
  alert(
    `Selected category: ${categoryName}. In a real application, this would filter cars by ${categoryName}.`
  );
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

// Render used cars for sale
function renderUsedCarsForSale() {
  const carsCarousel = document.getElementById("carsCarousel");
  carsCarousel.innerHTML = "";

  usedCarsForSale.forEach((car, index) => {
    const carCard = document.createElement("div");
    carCard.className = "car-card";
    carCard.style.animationDelay = `${index * 0.1}s`;
    carCard.onclick = () => viewCarDetails(car.id);

    carCard.innerHTML = `
      <div class="cars-car-image" style="background-image: url('${car.image}')">
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

// Initialize used cars tabs
function initializeUsedCarsTabs() {
  const tabButtons = document.querySelectorAll(".tab-btn");

  tabButtons.forEach((button) => {
    button.addEventListener("click", function () {
      // Remove active class from all tabs
      tabButtons.forEach((btn) => btn.classList.remove("active"));

      // Add active class to clicked tab
      this.classList.add("active");

      // Here you would typically filter the cars based on the selected tab
      // For now, we'll just show the same cars
      renderUsedCarsForSale();
    });
  });
}

// Cars carousel navigation
function scrollCarsCarousel(direction) {
  const carousel = document.getElementById("carsCarousel");
  const cardWidth = 280 + 24; // card width + gap
  const maxScroll = (usedCarsForSale.length - 4) * cardWidth;

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
  document.getElementById("brandSearchInput").value = brandName;
  closeBrandModal();
}

// Select brand from grid
function selectBrand(brandName) {
  selectedBrand = brandName;
  document.getElementById("brandSearchInput").value = brandName;

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

  if (dropdown && !dropdown.contains(e.target)) {
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
  const aiSearch = document.getElementById("aiSearchInput").value;
  const brandSearch = document.getElementById("brandSearchInput").value;
  const priceRange = selectedPriceRange;

  if (!aiSearch && !brandSearch && !priceRange) {
    alert("Please enter search criteria to find used cars.");
    return;
  }

  let searchSummary = "Search completed for used cars";
  if (aiSearch) {
    searchSummary += ` matching "${aiSearch}"`;
  }
  if (brandSearch) {
    searchSummary += ` from ${brandSearch}`;
  }
  if (priceRange) {
    searchSummary += ` in price range ${priceRange} AED`;
  }

  // Show search results (placeholder)
  alert(
    `${searchSummary}.\n\nFound 150+ matching used vehicles. In a real application, this would redirect to search results page.`
  );
}

// View car details
function viewCarDetails(carId) {
  alert(
    `Viewing details for used car ID: ${carId}. In a real application, this would redirect to the car details page.`
  );
}

// View all cars
function viewAllCars() {
  alert(
    "Showing all used cars for sale... In a real application, this would redirect to the used cars listing page."
  );
}

// Sell car for free
function sellCarForFree() {
  alert(
    "Redirecting to sell your car page... In a real application, this would redirect to the car selling form."
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
  if (modal && modal.classList.contains("active")) {
    if (e.key === "Escape") {
      closeBrandModal();
    }
  }
});

// Close modal when clicking outside
document.getElementById("brandModal")?.addEventListener("click", function (e) {
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
  searchBtn.innerHTML = '<i class="ri-loader-line"></i> Searching...';
  searchBtn.disabled = true;

  setTimeout(() => {
    searchBtn.innerHTML = '<i class="ri-sparkling-2-line"></i> Search';
    searchBtn.disabled = false;
  }, 1500);
}

// Enhanced search function with loading
function performSearchWithLoading() {
  const aiSearch = document.getElementById("aiSearchInput").value;
  const brandSearch = document.getElementById("brandSearchInput").value;
  const priceRange = selectedPriceRange;

  if (!aiSearch && !brandSearch && !priceRange) {
    alert("Please enter search criteria to find used cars.");
    return;
  }

  showLoading();

  setTimeout(() => {
    let searchSummary = "Search completed for used cars";
    if (aiSearch) {
      searchSummary += ` matching "${aiSearch}"`;
    }
    if (brandSearch) {
      searchSummary += ` from ${brandSearch}`;
    }
    if (priceRange) {
      searchSummary += ` in price range ${priceRange} AED`;
    }

    alert(
      `${searchSummary}!\n\nFound 150+ matching used vehicles. In a real application, you would see the results page now.`
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
    .querySelectorAll(
      ".video-card, .brand-item, .car-card, .news-item, .category-item"
    )
    .forEach((el) => {
      observer.observe(el);
    });
}

// Initialize animations
document.addEventListener("DOMContentLoaded", function () {
  setTimeout(addScrollAnimation, 100);
});
