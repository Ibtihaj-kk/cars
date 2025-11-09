const carData = [
  {
    id: 1,
    title: "Used 2021 Audi Q7",
    model: "Quattro AWD 4dr 55 TFSI",
    price: "$429,980",
    mileage: "98 miles",
    location: "Los Angeles, CA",
    distance: "Free",
    fuelEconomy: "22 CITY / 28 HWY MPG",
    photos: 45,
    status: "JUST SOLD",
    statusClass: "just-sold",
    image: "//images.pexels.com/photos/116675/pexels-photo-116675.jpeg?auto=compress&cs=tinysrgb&w=400",
  },
  {
    id: 2,
    title: "Used 2022 Mercedes-Benz S-Class",
    model: "S 580 4MATIC Sedan",
    price: "$89,500",
    mileage: "12K miles",
    location: "Beverly Hills, CA",
    distance: "8 mi.",
    fuelEconomy: "19 CITY / 29 HWY MPG",
    photos: 52,
    status: "LUXURY PICK",
    statusClass: "luxury-pick",
    image: "//images.pexels.com/photos/1545743/pexels-photo-1545743.jpeg?auto=compress&cs=tinysrgb&w=400",
  },
  {
    id: 3,
    title: "New 2024 BMW X7",
    model: "xDrive40i Sports Activity",
    price: "$76,800",
    mileage: "0 miles",
    location: "Manhattan, NY",
    distance: "—",
    fuelEconomy: "21 CITY / 26 HWY MPG",
    photos: 38,
    status: "NEW ARRIVAL",
    statusClass: "new-arrival",
    image: "//images.pexels.com/photos/337909/pexels-photo-337909.jpeg?auto=compress&cs=tinysrgb&w=400",
  },
  {
    id: 4,
    title: "Used 2023 Tesla Model X",
    model: "Plaid AWD SUV",
    price: "$94,990",
    mileage: "3,200 miles",
    location: "San Jose, CA",
    distance: "15 mi.",
    fuelEconomy: "102 CITY / 99 HWY MPGe",
    photos: 41,
    status: "ELECTRIC PICK",
    statusClass: "electric-pick",
    image: "//images.pexels.com/photos/3752169/pexels-photo-3752169.jpeg?auto=compress&cs=tinysrgb&w=400",
  },
  {
    id: 5,
    title: "Used 2022 Porsche Cayenne",
    model: "Turbo S E-Hybrid Coupe",
    price: "$142,900",
    mileage: "5,800 miles",
    location: "Miami Beach, FL",
    distance: "12 mi.",
    fuelEconomy: "14 CITY / 17 HWY MPG",
    photos: 47,
    status: "PERFORMANCE SUV",
    statusClass: "performance-suv",
    image: "//images.pexels.com/photos/1007410/pexels-photo-1007410.jpeg?auto=compress&cs=tinysrgb&w=400",
  },
  {
    id: 6,
    title: "New 2024 Lexus LX",
    model: "600 F Sport AWD",
    price: "$108,500",
    mileage: "0 miles",
    location: "Houston, TX",
    distance: "—",
    fuelEconomy: "17 CITY / 22 HWY MPG",
    photos: 35,
    status: "LUXURY SUV",
    statusClass: "luxury-suv",
    image: "//images.pexels.com/photos/136872/pexels-photo-136872.jpeg?auto=compress&cs=tinysrgb&w=400",
  },
  {
    id: 7,
    title: "Used 2023 Jaguar F-PACE",
    model: "SVR AWD SUV",
    price: "$79,900",
    mileage: "4,100 miles",
    location: "Chicago, IL",
    distance: "18 mi.",
    fuelEconomy: "16 CITY / 23 HWY MPG",
    photos: 43,
    status: "SPORT SUV",
    statusClass: "sport-suv",
    image: "//images.pexels.com/photos/210019/pexels-photo-210019.jpeg?auto=compress&cs=tinysrgb&w=400",
  },
  {
    id: 8,
    title: "Used 2022 Range Rover Sport",
    model: "HSE Dynamic P400",
    price: "$87,500",
    mileage: "7,200 miles",
    location: "Scottsdale, AZ",
    distance: "22 mi.",
    fuelEconomy: "19 CITY / 25 HWY MPG",
    photos: 39,
    status: "PREMIUM SUV",
    statusClass: "premium-suv",
    image: "//images.pexels.com/photos/977003/pexels-photo-977003.jpeg?auto=compress&cs=tinysrgb&w=400",
  },
  {
    id: 9,
    title: "New 2024 Cadillac Escalade",
    model: "Premium Luxury AWD",
    price: "$89,990",
    mileage: "0 miles",
    location: "Dallas, TX",
    distance: "—",
    fuelEconomy: "14 CITY / 19 HWY MPG",
    photos: 44,
    status: "LUXURY SUV",
    statusClass: "luxury-suv",
    image: "//images.pexels.com/photos/1592384/pexels-photo-1592384.jpeg?auto=compress&cs=tinysrgb&w=400",
  },
  {
    id: 10,
    title: "Used 2023 Genesis GV80",
    model: "3.5T Prestige AWD",
    price: "$64,900",
    mileage: "6,500 miles",
    location: "Atlanta, GA",
    distance: "14 mi.",
    fuelEconomy: "21 CITY / 25 HWY MPG",
    photos: 36,
    status: "LUXURY PICK",
    statusClass: "luxury-pick",
    image: "//images.pexels.com/photos/2365572/pexels-photo-2365572.jpeg?auto=compress&cs=tinysrgb&w=400",
  },
  {
    id: 11,
    title: "Used 2022 Maserati Levante",
    model: "Trofeo AWD SUV",
    price: "$119,900",
    mileage: "3,800 miles",
    location: "Las Vegas, NV",
    distance: "9 mi.",
    fuelEconomy: "13 CITY / 18 HWY MPG",
    photos: 48,
    status: "EXOTIC SUV",
    statusClass: "exotic-suv",
    image: "//images.pexels.com/photos/1719648/pexels-photo-1719648.jpeg?auto=compress&cs=tinysrgb&w=400",
  },
  {
    id: 12,
    title: "New 2024 Lincoln Navigator",
    model: "Reserve L AWD",
    price: "$95,500",
    mileage: "0 miles",
    location: "Detroit, MI",
    distance: "—",
    fuelEconomy: "16 CITY / 20 HWY MPG",
    photos: 42,
    status: "LUXURY SUV",
    statusClass: "luxury-suv",
    image: "//images.pexels.com/photos/3802510/pexels-photo-3802510.jpeg?auto=compress&cs=tinysrgb&w=400",
  },
  {
    id: 13,
    title: "Used 2023 Alfa Romeo Stelvio",
    model: "Quadrifoglio AWD",
    price: "$72,900",
    mileage: "4,200 miles",
    location: "Boston, MA",
    distance: "11 mi.",
    fuelEconomy: "17 CITY / 24 HWY MPG",
    photos: 37,
    status: "PERFORMANCE SUV",
    statusClass: "performance-suv",
    image: "//images.pexels.com/photos/1149137/pexels-photo-1149137.jpeg?auto=compress&cs=tinysrgb&w=400",
  },
  {
    id: 14,
    title: "Used 2022 Volvo XC90",
    model: "T8 Inscription AWD",
    price: "$58,900",
    mileage: "8,100 miles",
    location: "Seattle, WA",
    distance: "16 mi.",
    fuelEconomy: "27 CITY / 29 HWY MPG",
    photos: 33,
    status: "HYBRID SUV",
    statusClass: "hybrid-suv",
    image: "//images.pexels.com/photos/2365572/pexels-photo-2365572.jpeg?auto=compress&cs=tinysrgb&w=400",
  },
  {
    id: 15,
    title: "New 2024 Acura MDX",
    model: "Type-S SH-AWD",
    price: "$67,300",
    mileage: "0 miles",
    location: "Denver, CO",
    distance: "—",
    fuelEconomy: "17 CITY / 21 HWY MPG",
    photos: 40,
    status: "SPORT SUV",
    statusClass: "sport-suv",
    image: "//images.pexels.com/photos/1592384/pexels-photo-1592384.jpeg?auto=compress&cs=tinysrgb&w=400",
  },
  {
    id: 16,
    title: "Used 2023 Infiniti QX80",
    model: "Luxe AWD SUV",
    price: "$69,500",
    mileage: "5,900 miles",
    location: "Phoenix, AZ",
    distance: "13 mi.",
    fuelEconomy: "14 CITY / 20 HWY MPG",
    photos: 34,
    status: "LUXURY SUV",
    statusClass: "luxury-suv",
    image: "//images.pexels.com/photos/3802510/pexels-photo-3802510.jpeg?auto=compress&cs=tinysrgb&w=400",
  },
  {
    id: 17,
    title: "Used 2022 Ferrari 488",
    model: "GTB Coupe",
    price: "$289,900",
    mileage: "1,200 miles",
    location: "Newport Beach, CA",
    distance: "7 mi.",
    fuelEconomy: "15 CITY / 19 HWY MPG",
    photos: 55,
    status: "SUPERCAR",
    statusClass: "supercar",
    image: "//images.pexels.com/photos/1719648/pexels-photo-1719648.jpeg?auto=compress&cs=tinysrgb&w=400",
  },
  {
    id: 18,
    title: "Used 2023 Lamborghini Urus",
    model: "Performante AWD",
    price: "$279,900",
    mileage: "2,100 miles",
    location: "Miami, FL",
    distance: "5 mi.",
    fuelEconomy: "12 CITY / 17 HWY MPG",
    photos: 62,
    status: "SUPER SUV",
    statusClass: "super-suv",
    image: "//images.pexels.com/photos/1149137/pexels-photo-1149137.jpeg?auto=compress&cs=tinysrgb&w=400",
  },
  {
    id: 19,
    title: "New 2024 Bentley Bentayga",
    model: "V8 AWD SUV",
    price: "$219,900",
    mileage: "0 miles",
    location: "San Francisco, CA",
    distance: "—",
    fuelEconomy: "14 CITY / 24 HWY MPG",
    photos: 46,
    status: "ULTRA LUXURY",
    statusClass: "ultra-luxury",
    image: "//images.pexels.com/photos/1592384/pexels-photo-1592384.jpeg?auto=compress&cs=tinysrgb&w=400",
  },
  {
    id: 20,
    title: "Used 2022 Rolls-Royce Cullinan",
    model: "Black Badge AWD",
    price: "$389,900",
    mileage: "3,500 miles",
    location: "Beverly Hills, CA",
    distance: "4 mi.",
    fuelEconomy: "12 CITY / 18 HWY MPG",
    photos: 58,
    status: "ULTRA LUXURY",
    statusClass: "ultra-luxury",
    image: "//images.pexels.com/photos/1592384/pexels-photo-1592384.jpeg?auto=compress&cs=tinysrgb&w=400",
  },
  {
    id: 21,
    title: "Used 2023 McLaren 720S",
    model: "Spider Convertible",
    price: "$319,900",
    mileage: "1,800 miles",
    location: "Austin, TX",
    distance: "6 mi.",
    fuelEconomy: "15 CITY / 22 HWY MPG",
    photos: 51,
    status: "SUPERCAR",
    statusClass: "supercar",
    image: "//images.pexels.com/photos/3802510/pexels-photo-3802510.jpeg?auto=compress&cs=tinysrgb&w=400",
  },
  {
    id: 22,
    title: "New 2024 Aston Martin DBX",
    model: "707 AWD SUV",
    price: "$239,900",
    mileage: "0 miles",
    location: "Nashville, TN",
    distance: "—",
    fuelEconomy: "13 CITY / 18 HWY MPG",
    photos: 49,
    status: "EXOTIC SUV",
    statusClass: "exotic-suv",
    image: "//images.pexels.com/photos/1719648/pexels-photo-1719648.jpeg?auto=compress&cs=tinysrgb&w=400",
  },
  {
    id: 23,
    title: "Used 2022 Bugatti Chiron",
    model: "Sport Coupe",
    price: "$2,899,900",
    mileage: "800 miles",
    location: "Monaco",
    distance: "International",
    fuelEconomy: "9 CITY / 14 HWY MPG",
    photos: 67,
    status: "HYPERCAR",
    statusClass: "hypercar",
    image: "//images.pexels.com/photos/1149137/pexels-photo-1149137.jpeg?auto=compress&cs=tinysrgb&w=400",
  },
  {
    id: 24,
    title: "Used 2023 Koenigsegg Regera",
    model: "Hybrid Megacar",
    price: "$1,899,900",
    mileage: "1,100 miles",
    location: "Monterey, CA",
    distance: "25 mi.",
    fuelEconomy: "12 CITY / 16 HWY MPG",
    photos: 72,
    status: "HYPERCAR",
    statusClass: "hypercar",
    image: "//images.pexels.com/photos/2365572/pexels-photo-2365572.jpeg?auto=compress&cs=tinysrgb&w=400",
  },
  {
    id: 25,
    title: "New 2024 Ford Mustang",
    model: "GT Premium Fastback",
    price: "$47,900",
    mileage: "0 miles",
    location: "Detroit, MI",
    distance: "—",
    fuelEconomy: "16 CITY / 24 HWY MPG",
    photos: 28,
    status: "MUSCLE CAR",
    statusClass: "muscle-car",
    image: "//images.pexels.com/photos/1592384/pexels-photo-1592384.jpeg?auto=compress&cs=tinysrgb&w=400",
  },
  {
    id: 26,
    title: "Used 2023 Chevrolet Corvette",
    model: "Z06 Coupe",
    price: "$129,900",
    mileage: "2,800 miles",
    location: "Charlotte, NC",
    distance: "19 mi.",
    fuelEconomy: "12 CITY / 20 HWY MPG",
    photos: 45,
    status: "SPORTS CAR",
    statusClass: "sports-car",
    image: "//images.pexels.com/photos/3802510/pexels-photo-3802510.jpeg?auto=compress&cs=tinysrgb&w=400",
  },
  {
    id: 27,
    title: "Used 2022 Dodge Challenger",
    model: "SRT Hellcat Redeye",
    price: "$89,900",
    mileage: "4,500 miles",
    location: "Las Vegas, NV",
    distance: "11 mi.",
    fuelEconomy: "13 CITY / 22 HWY MPG",
    photos: 32,
    status: "MUSCLE CAR",
    statusClass: "muscle-car",
    image: "//images.pexels.com/photos/1719648/pexels-photo-1719648.jpeg?auto=compress&cs=tinysrgb&w=400",
  },
  {
    id: 28,
    title: "New 2024 Toyota Supra",
    model: "3.0 Premium RWD",
    price: "$56,500",
    mileage: "0 miles",
    location: "Los Angeles, CA",
    distance: "—",
    fuelEconomy: "22 CITY / 30 HWY MPG",
    photos: 31,
    status: "SPORTS CAR",
    statusClass: "sports-car",
    image: "//images.pexels.com/photos/1149137/pexels-photo-1149137.jpeg?auto=compress&cs=tinysrgb&w=400",
  },
  {
    id: 29,
    title: "Used 2023 Nissan GT-R",
    model: "NISMO AWD Coupe",
    price: "$219,900",
    mileage: "1,900 miles",
    location: "San Diego, CA",
    distance: "17 mi.",
    fuelEconomy: "16 CITY / 22 HWY MPG",
    photos: 41,
    status: "SUPERCAR",
    statusClass: "supercar",
    image: "//images.pexels.com/photos/2365572/pexels-photo-2365572.jpeg?auto=compress&cs=tinysrgb&w=400",
  },
  {
    id: 30,
    title: "Used 2022 Honda NSX",
    model: "Type S Hybrid AWD",
    price: "$189,900",
    mileage: "3,200 miles",
    location: "Portland, OR",
    distance: "23 mi.",
    fuelEconomy: "21 CITY / 22 HWY MPG",
    photos: 38,
    status: "HYBRID SUPERCAR",
    statusClass: "hybrid-supercar",
    image: "//images.pexels.com/photos/1592384/pexels-photo-1592384.jpeg?auto=compress&cs=tinysrgb&w=400",
  },
  {
    id: 31,
    title: "New 2024 Rivian R1S",
    model: "Adventure Package AWD",
    price: "$78,900",
    mileage: "0 miles",
    location: "Denver, CO",
    distance: "—",
    fuelEconomy: "102 CITY / 88 HWY MPGe",
    photos: 35,
    status: "ELECTRIC SUV",
    statusClass: "electric-suv",
    image: "//images.pexels.com/photos/3802510/pexels-photo-3802510.jpeg?auto=compress&cs=tinysrgb&w=400",
  },
  {
    id: 32,
    title: "Used 2023 Lucid Air",
    model: "Dream Edition RWD",
    price: "$149,900",
    mileage: "2,100 miles",
    location: "Palo Alto, CA",
    distance: "8 mi.",
    fuelEconomy: "131 CITY / 126 HWY MPGe",
    photos: 44,
    status: "LUXURY ELECTRIC",
    statusClass: "luxury-electric",
    image: "//images.pexels.com/photos/1719648/pexels-photo-1719648.jpeg?auto=compress&cs=tinysrgb&w=400",
  },
]

// Pagination variables
let currentPage = 1
const cardsPerPage = 8
const totalPages = Math.ceil(carData.length / cardsPerPage)

// DOM elements
const carGrid = document.getElementById("carGrid")
const pageNumbers = document.getElementById("pageNumbers")
const prevBtn = document.getElementById("prevBtn")
const nextBtn = document.getElementById("nextBtn")

// Function to create car card HTML
function createCarCard(car) {
  return `
        <div class="car-card">
            <div class="car-image">
                <img src="${car.image}" alt="${car.title}">
                <div class="status-label ${car.statusClass}">${car.status}</div>
                </div>
                <div class="car-header">
                    <span class="photo-count">${car.photos} Photos</span>
                    <span class="video-icon"><a href="#"><ion-icon name="caret-forward-outline"></ion-icon> Video Tour</a></span>
                </div>
            <div class="car-details">
                <h3>${car.title}</h3>
                <p class="car-model">${car.model}</p>
                <p class="car-price">${car.price}</p>
                <p class="car-info">
                    <span class="mileage">${car.mileage}</span> • 
                    <span class="location">${car.location}</span> • 
                    <span class="distance">${car.distance}</span>
                </p>
                <p class="fuel-economy">${car.fuelEconomy}</p>
                <div class="card-actions">
                    <button class="primary-btn">🗓 Schedule Test Drive</button>
                    <a href="#" class="secondary-btn">Learn More</a>
                </div>
                <div class="card-footer">
                    <a href="#"><ion-icon name="git-compare-outline"></ion-icon> Compare</a>
                    <a href="#"><i class="ri-save-3-line"></i> Save</a>
                    <a href="./car-details.html">👁 View Details</a>
                </div>
            </div>
        </div>
    `
}

// Function to display cars for current page
function displayCars(page) {
  const startIndex = (page - 1) * cardsPerPage
  const endIndex = startIndex + cardsPerPage

  const carsToDisplay = carData.slice(startIndex, endIndex)

  carGrid.innerHTML = carsToDisplay.map((car) => createCarCard(car)).join("")
}

// Function to create page numbers
function createPageNumbers() {
  pageNumbers.innerHTML = ""

  for (let i = 1; i <= totalPages; i++) {
    const pageBtn = document.createElement("button")
    pageBtn.className = `page-btn ${i === currentPage ? "current" : ""}`
    pageBtn.textContent = i
    pageBtn.addEventListener("click", () => {
      currentPage = i
      displayCars(currentPage)
      updatePaginationControls()
    })
    pageNumbers.appendChild(pageBtn)
  }
}

// Function to update pagination controls
function updatePaginationControls() {
  // Update page number buttons
  const allPageBtns = pageNumbers.querySelectorAll(".page-btn")
  allPageBtns.forEach((btn, index) => {
    btn.classList.toggle("current", index + 1 === currentPage)
  })

  // Update previous/next buttons
  prevBtn.disabled = currentPage === 1
  nextBtn.disabled = currentPage === totalPages
}

// Event listeners for previous/next buttons - commented out for static HTML
/*
prevBtn.addEventListener("click", () => {
  if (currentPage > 1) {
    currentPage--
    displayCars(currentPage)
    updatePaginationControls()
  }
})

nextBtn.addEventListener("click", () => {
  if (currentPage < totalPages) {
    currentPage++
    displayCars(currentPage)
    updatePaginationControls()
  }
})
*/

// Homepage Filter Carousel Manager
class CarouselManager {
  constructor() {
    this.activeTab = "category"
    this.carousels = {}
    this.isDragging = false
    this.startX = 0
    this.scrollLeft = 0

    this.init()
  }

  init() {
    this.setupTabs()
    this.setupCarousels()
    this.setupDragAndDrop()
    this.setupItemSelection()
    this.setupResponsiveHandling()
    
    // Set initial state - only show category carousel
    this.setInitialState()
  }

  setInitialState() {
    // Remove active class from all carousels
    document.querySelectorAll(".carousel").forEach((carousel) => {
      carousel.classList.remove("active")
    })
    
    // Add active class to category carousel
    const categoryCarousel = document.getElementById("category-carousel")
    if (categoryCarousel) {
      categoryCarousel.classList.add("active")
    }
  }

  setupTabs() {
    const tabButtons = document.querySelectorAll(".tab-btn")

    tabButtons.forEach((btn) => {
      btn.addEventListener("click", (e) => {
        const tabId = e.target.getAttribute("data-tab")
        this.switchTab(tabId)
      })
    })
  }

  switchTab(tabId) {
    // Update active tab button
    document.querySelectorAll(".tab-btn").forEach((btn) => {
      btn.classList.remove("active")
    })
    document.querySelector(`[data-tab="${tabId}"]`).classList.add("active")

    // Hide all carousels and show the target one
    document.querySelectorAll(".carousel").forEach((carousel) => {
      carousel.classList.remove("active")
    })

    const targetCarousel = document.getElementById(`${tabId}-carousel`)
    if (targetCarousel) {
      targetCarousel.classList.add("active")
      this.activeTab = tabId

      // Reset scroll position for new carousel
      const track = targetCarousel.querySelector(".carousel-track")
      if (track) {
        track.scrollLeft = 0
      }
    }
  }

  setupCarousels() {
    const carousels = document.querySelectorAll(".carousel")

    carousels.forEach((carousel) => {
      const track = carousel.querySelector(".carousel-track")
      if (track) {
        this.carousels[carousel.id] = {
          element: carousel,
          track: track,
          scrollPosition: 0,
        }
      }
    })
  }

  setupDragAndDrop() {
    const tracks = document.querySelectorAll(".carousel-track")

    tracks.forEach((track) => {
      // Mouse events
      track.addEventListener("mousedown", (e) => this.handleDragStart(e, track))
      track.addEventListener("mousemove", (e) => this.handleDragMove(e, track))
      track.addEventListener("mouseup", () => this.handleDragEnd(track))
      track.addEventListener("mouseleave", () => this.handleDragEnd(track))

      // Touch events for mobile
      track.addEventListener("touchstart", (e) => this.handleTouchStart(e, track))
      track.addEventListener("touchmove", (e) => this.handleTouchMove(e, track))
      track.addEventListener("touchend", () => this.handleTouchEnd(track))

      // Prevent text selection during drag
      track.addEventListener("selectstart", (e) => {
        if (this.isDragging) e.preventDefault()
      })
    })
  }

  handleDragStart(e, track) {
    this.isDragging = true
    this.startX = e.pageX - track.offsetLeft
    this.scrollLeft = track.scrollLeft
    track.classList.add("dragging")
    e.preventDefault()
  }

  handleDragMove(e, track) {
    if (!this.isDragging) return

    e.preventDefault()
    const x = e.pageX - track.offsetLeft
    const walk = (x - this.startX) * 2
    track.scrollLeft = this.scrollLeft - walk
  }

  handleDragEnd(track) {
    this.isDragging = false
    track.classList.remove("dragging")
  }

  handleTouchStart(e, track) {
    this.isDragging = true
    this.startX = e.touches[0].pageX - track.offsetLeft
    this.scrollLeft = track.scrollLeft
    track.classList.add("dragging")
  }

  handleTouchMove(e, track) {
    if (!this.isDragging) return

    const x = e.touches[0].pageX - track.offsetLeft
    const walk = (x - this.startX) * 2
    track.scrollLeft = this.scrollLeft - walk
  }

  handleTouchEnd(track) {
    this.isDragging = false
    track.classList.remove("dragging")
  }

  setupItemSelection() {
    const filterItems = document.querySelectorAll(".filter-item")

    filterItems.forEach((item) => {
      item.addEventListener("click", (e) => {
        // Don't trigger selection if we were dragging
        if (this.isDragging) return

        const track = e.target.closest(".carousel-track")

        // Remove previous selection in this track
        track.querySelectorAll(".filter-item").forEach((i) => {
          i.classList.remove("selected")
        })

        // Add selection to clicked item
        item.classList.add("selected")

        // Emit custom event for external handling
        this.emitSelectionEvent(item, this.activeTab)
      })
    })
  }

  emitSelectionEvent(item, tab) {
    const event = new CustomEvent("filterSelected", {
      detail: {
        tab: tab,
        value: item.querySelector("span").textContent.trim(),
        element: item,
        data: {
          category: item.dataset.category,
          make: item.dataset.make,
          minPrice: item.dataset.minPrice,
          maxPrice: item.dataset.maxPrice,
          city: item.dataset.city,
          bodyType: item.dataset.bodyType,
          year: item.dataset.year
        }
      },
    })
    document.dispatchEvent(event)
  }

  setupResponsiveHandling() {
    let resizeTimeout

    window.addEventListener("resize", () => {
      clearTimeout(resizeTimeout)
      resizeTimeout = setTimeout(() => {
        this.handleResize()
      }, 150)
    })
  }

  handleResize() {
    // Reset scroll positions on resize to prevent layout issues
    Object.values(this.carousels).forEach((carousel) => {
      if (carousel.track) {
        carousel.track.scrollLeft = 0
      }
    })
  }
}

// Mobile Menu Manager
class MobileMenuManager {
  constructor() {
    this.init()
  }

  init() {
    this.setupMobileToggle()
    this.setupSidebarToggle()
    this.setupOutsideClick()
    this.setupResizeHandler()
  }

  setupMobileToggle() {
    const mobileToggle = document.querySelector(".mobile-menu-toggle")
    const navbar = document.querySelector(".navbar")

    if (mobileToggle && navbar) {
      mobileToggle.addEventListener("click", () => {
        mobileToggle.classList.toggle("active")
        navbar.classList.toggle("active")
        document.body.classList.toggle("mobile-navbar-open")
      })
    }
  }

  setupSidebarToggle() {
    // Create sidebar toggle button if it doesn't exist
    let sidebarToggle = document.querySelector(".mobile-sidebar-toggle")
    if (!sidebarToggle) {
      sidebarToggle = document.createElement("button")
      sidebarToggle.className = "mobile-sidebar-toggle"
      sidebarToggle.innerHTML = "☰ Filters"
      sidebarToggle.style.cssText = `
        position: fixed;
        bottom: 20px;
        left: 20px;
        z-index: 1001;
        padding: 12px 16px;
        background: #4d78bc;
        color: white;
        border: none;
        border-radius: 25px;
        font-size: 14px;
        font-weight: 600;
        cursor: pointer;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        display: none;
      `
      document.body.appendChild(sidebarToggle)
    }

    const sidebar = document.querySelector(".left-sidebar")

    if (sidebarToggle && sidebar) {
      sidebarToggle.addEventListener("click", () => {
        sidebar.classList.toggle("active")
        document.body.classList.toggle("mobile-sidebar-open")
      })
    }

    // Show/hide sidebar toggle based on screen size
    const checkScreenSize = () => {
      if (window.innerWidth <= 768) {
        sidebarToggle.style.display = "block"
      } else {
        sidebarToggle.style.display = "none"
        sidebar.classList.remove("active")
        document.body.classList.remove("mobile-sidebar-open")
      }
    }

    window.addEventListener("resize", checkScreenSize)
    checkScreenSize()
  }

  setupOutsideClick() {
    document.addEventListener("click", (e) => {
      const sidebar = document.querySelector(".left-sidebar")
      const navbar = document.querySelector(".navbar")
      const mobileToggle = document.querySelector(".mobile-menu-toggle")
      const sidebarToggle = document.querySelector(".mobile-sidebar-toggle")

      // Close mobile navbar if clicking outside
      if (navbar.classList.contains("active") && !navbar.contains(e.target) && !mobileToggle.contains(e.target)) {
        navbar.classList.remove("active")
        mobileToggle.classList.remove("active")
        document.body.classList.remove("mobile-navbar-open")
      }

      // Close sidebar if clicking outside
      if (sidebar.classList.contains("active") && !sidebar.contains(e.target) && !sidebarToggle.contains(e.target)) {
        sidebar.classList.remove("active")
        document.body.classList.remove("mobile-sidebar-open")
      }
    })
  }

  setupResizeHandler() {
    window.addEventListener("resize", () => {
      if (window.innerWidth > 768) {
        const sidebar = document.querySelector(".left-sidebar")
        const navbar = document.querySelector(".navbar")
        const mobileToggle = document.querySelector(".mobile-menu-toggle")

        // Close mobile menus on desktop
        sidebar.classList.remove("active")
        navbar.classList.remove("active")
        mobileToggle.classList.remove("active")
        document.body.classList.remove("mobile-sidebar-open", "mobile-navbar-open")
      }
    })
  }
}

// Sidebar tab functionality
const sidebarTabBtns = document.querySelectorAll(".sidebar-tab-btn")
const sidebarTabContents = document.querySelectorAll(".sidebar-tab-content")

sidebarTabBtns.forEach((btn) => {
  btn.addEventListener("click", function () {
    const targetTab = this.dataset.tab

    // Remove active class from all tabs and contents
    sidebarTabBtns.forEach((b) => b.classList.remove("active"))
    sidebarTabContents.forEach((c) => c.classList.remove("active"))

    // Add active class to clicked tab and corresponding content
    this.classList.add("active")
    document.getElementById(targetTab + "-tab").classList.add("active")
  })
})

// Accordion functionality for filters
const detailsElements = document.querySelectorAll("details")

detailsElements.forEach((details) => {
  details.addEventListener("toggle", function () {
    const arrow = this.querySelector(".arrow")
    if (this.open) {
      arrow.style.transform = "rotate(180deg)"
    } else {
      arrow.style.transform = "rotate(0deg)"
    }
  })
})

// Search functionality
const searchBtn = document.querySelector(".search-btn")
const searchInput = document.querySelector(".search-input")

if (searchBtn && searchInput) {
  searchBtn.addEventListener("click", () => {
    const searchTerm = searchInput.value.trim()
    console.log("Search clicked:", searchTerm)
    // Add search logic here
  })

  searchInput.addEventListener("keypress", function (e) {
    if (e.key === "Enter") {
      const searchTerm = this.value.trim()
      console.log("Search entered:", searchTerm)
      // Add search logic here
    }
  })
}

// Sort button functionality
const sortBtn = document.querySelector(".sort-btn")
if (sortBtn) {
  sortBtn.addEventListener("click", () => {
    console.log("Sort clicked")
    // Add sorting logic here
  })
}

// Slider functionality for real-time value updates
function initializeSliders() {
  // Distance slider
  const distanceSlider = document.getElementById("distanceSlider")
  const distanceValue = document.getElementById("distanceValue")

  if (distanceSlider && distanceValue) {
    distanceSlider.addEventListener("input", function () {
      const value = this.value
      if (value >= 100) {
        distanceValue.textContent = "100+ mi"
      } else {
        distanceValue.textContent = value + " mi"
      }
    })
  }

  // Price slider
  const priceSlider = document.getElementById("priceSlider")
  const priceValue = document.getElementById("priceValue")
  const minPriceInput = document.getElementById("minPrice")
  const maxPriceInput = document.getElementById("maxPrice")

  if (priceSlider && priceValue) {
    priceSlider.addEventListener("input", function () {
      const value = Number.parseInt(this.value)
      if (value >= 200000) {
        priceValue.textContent = "$200k+"
      } else {
        priceValue.textContent = "$" + value.toLocaleString()
      }

      // Update max price input
      if (maxPriceInput) {
        maxPriceInput.value = value.toLocaleString()
      }
    })
  }

  // Connect price inputs to slider
  if (minPriceInput && priceSlider) {
    minPriceInput.addEventListener("input", function () {
      const value = Number.parseInt(this.value.replace(/,/g, "")) || 0
      if (value <= Number.parseInt(priceSlider.max)) {
        priceSlider.min = value
      }
    })
  }

  if (maxPriceInput && priceSlider) {
    maxPriceInput.addEventListener("input", function () {
      const value = Number.parseInt(this.value.replace(/,/g, "")) || 200000
      if (value >= Number.parseInt(priceSlider.min)) {
        priceSlider.value = value
        priceSlider.dispatchEvent(new Event("input"))
      }
    })
  }

  // Year slider
  const yearSlider = document.getElementById("yearSlider")
  const yearValue = document.getElementById("yearValue")

  if (yearSlider && yearValue) {
    yearSlider.addEventListener("input", function () {
      yearValue.textContent = this.value
    })
  }

  // Mileage slider
  const mileageSlider = document.getElementById("mileageSlider")
  const mileageValue = document.getElementById("mileageValue")

  if (mileageSlider && mileageValue) {
    mileageSlider.addEventListener("input", function () {
      const value = Number.parseInt(this.value)
      if (value >= 100000) {
        mileageValue.textContent = "100k+ mi"
      } else if (value >= 1000) {
        mileageValue.textContent = Math.round(value / 1000) + "k mi"
      } else {
        mileageValue.textContent = value + " mi"
      }
    })
  }

  // Fuel Economy slider
  const fuelEconomySlider = document.getElementById("fuelEconomySlider")
  const fuelEconomyValue = document.getElementById("fuelEconomyValue")

  if (fuelEconomySlider && fuelEconomyValue) {
    fuelEconomySlider.addEventListener("input", function () {
      const value = Number.parseInt(this.value)
      if (value >= 50) {
        fuelEconomyValue.textContent = "50+ MPG"
      } else {
        fuelEconomyValue.textContent = value + " MPG"
      }
    })
  }
}

// Initialize the application
document.addEventListener("DOMContentLoaded", () => {
  // Car grid functionality commented out - now using static HTML
  // displayCars(currentPage)
  // createPageNumbers()
  // updatePaginationControls()

  initializeSliders()

  // Initialize carousel manager
  const carouselManager = new CarouselManager()
  window.carouselManager = carouselManager

  // Initialize mobile menu manager
  const mobileMenuManager = new MobileMenuManager()
  window.mobileMenuManager = mobileMenuManager

  // Listen to filter selections
  document.addEventListener("filterSelected", (e) => {
    console.log("Filter selected:", e.detail)
  })
})

// Smooth scrolling for anchor links
document.querySelectorAll('a[href^="#"]').forEach((anchor) => {
  anchor.addEventListener("click", function (e) {
    e.preventDefault()
    const target = document.querySelector(this.getAttribute("href"))
    if (target) {
      target.scrollIntoView({
        behavior: "smooth",
      })
    }
  })
})

// Debounced resize handler
let resizeTimeout
window.addEventListener("resize", () => {
  clearTimeout(resizeTimeout)
  resizeTimeout = setTimeout(() => {
    // Handle any resize-specific logic here
    console.log("Window resized:", window.innerWidth, "x", window.innerHeight)
  }, 250)
})


