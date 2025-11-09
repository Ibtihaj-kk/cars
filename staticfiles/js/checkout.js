// Saudi Arabia cities and their areas
const saudiCities = {
  Riyadh: [
    "Al-Malaz",
    "Al-Olaya",
    "Al-Murabba",
    "King Fahd District",
    "Al-Sahafa",
    "Al-Nakheel",
    "Al-Wurud",
    "Al-Hamra",
    "Al-Sulaimaniyah",
    "Al-Qadisiyah",
  ],
  Jeddah: [
    "Al-Balad",
    "Al-Hamra",
    "Al-Rawdah",
    "Al-Zahra",
    "Al-Salamah",
    "Al-Marwah",
    "Al-Sharafiyah",
    "Al-Baghdadiyah",
    "Al-Ruwais",
    "Al-Aziziyah",
  ],
  Mecca: [
    "Al-Haram",
    "Al-Aziziyah",
    "Al-Rusaifah",
    "Al-Kakiyah",
    "Al-Hindawiyah",
    "Al-Utaibiyah",
    "Ajyad",
    "Al-Ghassalah",
    "Al-Khadra",
    "Al-Taneem",
  ],
  Medina: [
    "Al-Haram",
    "Al-Anbariyah",
    "Al-Iskan",
    "Qurban",
    "Al-Khalil",
    "Al-Uyun",
    "Al-Hijrah",
    "Al-Azhar",
    "Al-Jubailah",
    "Al-Rawabeh",
  ],
  Dammam: [
    "Al-Faisaliyah",
    "Al-Shati",
    "Al-Mazruiyah",
    "Al-Adamah",
    "Al-Jalawiyah",
    "Al-Badiyah",
    "Al-Manar",
    "Ash Shulah",
    "Al-Noor",
    "Al-Anoud",
  ],
  Khobar: [
    "Al-Aqrabiyah",
    "Al-Olaya",
    "Al-Thuqbah",
    "Al-Bandariyah",
    "Al-Hizam",
    "Corniche",
    "Al-Yarmouk",
    "Al-Khuzama",
    "Al-Dana",
    "Al-Jisr",
  ],
  Dhahran: [
    "KFUPM",
    "Aramco",
    "Al-Doha",
    "Al-Khobar Road",
    "Aviation District",
    "Dhahran Hills",
    "Al-Murjan",
    "Sunset Beach",
    "Golf Course",
    "Al-Bustan",
  ],
  Qatif: [
    "Al-Qatif Center",
    "Safwa",
    "Saihat",
    "Tarout",
    "Al-Awamiyah",
    "Al-Jish",
    "Umm al-Hamam",
    "Al-Malahah",
    "Al-Tubi",
    "Al-Jaroudiyah",
  ],
  Hofuf: [
    "Al-Hofuf Center",
    "Al-Mubarraz",
    "Al-Oyoun",
    "Al-Jubayl",
    "Al-Omran",
    "Al-Natheel",
    "Al-Khadra",
    "Al-Bustan",
    "Al-Waha",
    "Al-Andalus",
  ],
  "Al Hasa": [
    "Al-Hofuf",
    "Al-Mubarraz",
    "Al-Oyoun",
    "Haradh",
    "Al-Ahsa Oasis",
    "Al-Jafr",
    "Al-Markaz",
    "Al-Qarah",
    "Al-Thuqbah",
    "Al-Kilabiyah",
  ],
  Abha: [
    "Al-Manhal",
    "Al-Nazlah",
    "Ash Shafa",
    "Al-Muftahah",
    "Al-Wurud",
    "Al-Sahab",
    "Al-Mahalah",
    "Al-Dabab",
    "Al-Qabil",
    "New Abha",
  ],
  "Khamis Mushait": [
    "Al-Namas Road",
    "King Khalid University",
    "Al-Mohandeseen",
    "Al-Rehab",
    "Al-Nuzha",
    "Al-Wurud",
    "Al-Andalus",
    "Al-Rawdah",
    "Al-Iskan",
    "Al-Shurta",
  ],
  Taif: [
    "Al-Hawiyah",
    "Al-Rudaf",
    "Ash Shafa",
    "Al-Hada",
    "Al-Salamah",
    "Al-Naseem",
    "Al-Aziziyah",
    "Al-Faisaliyah",
    "Al-Qadisiyah",
    "Al-Shubra",
  ],
  Jizan: [
    "Corniche",
    "Al-Rabi",
    "Al-Mahrajan",
    "Al-Mohamadiyah",
    "Al-Nakheel",
    "Al-Salam",
    "Al-Shati",
    "Al-Rawdah",
    "Port Area",
    "Al-Hamra",
  ],
  Najran: [
    "Al-Faisaliyah",
    "Al-Dira",
    "Al-Yamama",
    "Al-Mishash",
    "Al-Okhdood",
    "Al-Janubiyah",
    "Al-Fath",
    "Al-Bustan",
    "Al-Khalij",
    "University District",
  ],
  Tabuk: [
    "Prince Fahd Bin Sultan",
    "Al-Wurud",
    "Al-Hamra",
    "Al-Zahra",
    "Al-Nakheel",
    "Al-Montazah",
    "King Khalid",
    "Al-Murjan",
    "Al-Shati",
    "Al-Rawdah",
  ],
  Hail: [
    "Al-Yamamah",
    "Al-Naqra",
    "Al-Matar",
    "Al-Zubair",
    "Al-Wadi",
    "Al-Samah",
    "Al-Andalus",
    "Al-Aziziyah",
    "Al-Faisaliyah",
    "Al-Shurta",
  ],
  "Al Bahah": [
    "Al-Zahra",
    "Al-Aqiq",
    "Al-Mikhwah",
    "Baljurashi",
    "Al-Mandaq",
    "Al-Baha Center",
    "Al-Sarawat",
    "Al-Qura",
    "Al-Tihama",
    "Al-Sarah",
  ],
  Arar: [
    "Al-Nuzha",
    "Industrial",
    "Al-Masif",
    "Al-Wurud",
    "Al-Aziziyah",
    "Al-Salamah",
    "Government District",
    "Al-Sulay",
    "Al-Muraba",
    "Al-Khaleej",
  ],
  Sakaka: [
    "Prince Abdul Ilah",
    "Al-Nuzha",
    "Al-Malek Faisal",
    "Industrial Area",
    "Al-Iskan",
    "Al-Wurud",
    "Al-Rawdah",
    "Al-Hamra",
    "Al-Andalus",
    "Al-Zahra",
  ],
}

// Global variables
let cartItems = []
let selectedCity = ""
let selectedArea = ""
let currentStep = 1

const topSellingProducts = [
  {
    id: 1,
    title: "CarsPortal Interior Protectant Spray",
    price: "$ 999",
    originalPrice: "$ 1,297",
    image: "/images/brands/OIP.jpeg",
    discount: "25% OFF",
  },
  {
    id: 2,
    title: "Ke Pioneer Professional Ceramic Coating",
    price: "$ 1,777",
    originalPrice: "$ 2,596",
    image: "/images/brands/AUTOWashfront_713e8127-fd0f-4be2-802b-2195f71ceec5_700x700.webp",
    discount: "30% OFF",
  },
  {
    id: 3,
    title: "CarsPortal Waterless Car Wash",
    price: "$ 699",
    originalPrice: "$ 897",
    image: "/images/brands/81VB7au6D2L._AC_.jpg",
    discount: "20% OFF",
  },
  {
    id: 4,
    title: "CarsPortal Spotless Car Wash Twin Pack",
    price: "$ 1,199",
    originalPrice: "$ 1,399",
    image: "/images/brands/Slide_pakwheels-spotless-car-wash-shampoo-pack-of-2-69417151.jpg",
    discount: "15% OFF",
  },
  {
    id: 5,
    title: "Premium Tire Shine & Protectant",
    price: "$ 799",
    originalPrice: "$ 1,199",
    image: "/images/brands/OIP (1).jpeg",
    discount: "35% OFF",
  },
  {
    id: 6,
    title: "Dashboard Cleaner & Conditioner",
    price: "$ 599",
    originalPrice: "$ 999",
    image: "/images/brands/DashboardCleaner_500ml_large.webp",
    discount: "40% OFF",
  },
  {
    id: 7,
    title: "Crystal Clear Glass Cleaner",
    price: "$ 449",
    originalPrice: "$ 599",
    image: "/images/brands/OIP (2).jpeg",
    discount: "25% OFF",
  },
  {
    id: 8,
    title: "Leather Care & Conditioner",
    price: "$ 899",
    originalPrice: "$ 1,299",
    image: "/images/brands/b9a259ab-1f14-48fb-a895-b1e70467e1a0.c7b1bd16611648fba5345c63146bd8f8.webp",
    discount: "30% OFF",
  },
  {
    id: 9,
    title: "Premium Car Wax & Polish",
    price: "$ 1,299",
    originalPrice: "$ 1,599",
    image: "/images/brands/816r2OhrB4L.jpg",
    discount: "20% OFF",
  },
  {
    id: 10,
    title: "Upholstery & Fabric Cleaner",
    price: "$ 699",
    originalPrice: "$ 1,299",
    image: "/images/brands/OIP (3).jpeg",
    discount: "45% OFF",
  },
  {
    id: 11,
    title: "Heavy Duty Engine Degreaser",
    price: "$ 999",
    originalPrice: "$ 1,499",
    image: "/images/brands/OIP (4).jpeg",
    discount: "35% OFF",
  },
  {
    id: 12,
    title: "Complete Car Detailing Kit",
    price: "$ 2,499",
    originalPrice: "$ 4,999",
    image: "/images/brands/51XuKnmlAvL.jpg",
    discount: "50% OFF",
  },
]

// Load cart data from localStorage
function loadCartData() {
  const savedCartItems = localStorage.getItem("cartItems")
  if (savedCartItems) {
    cartItems = JSON.parse(savedCartItems)
  }
}

function addToCartFromProducts(productId) {
  const product = topSellingProducts.find((p) => p.id === productId)
  if (!product) return

  // Check if product already exists in cart
  const existingItemIndex = cartItems.findIndex((item) => item.id === productId)

  if (existingItemIndex !== -1) {
    // If product exists, increase quantity
    cartItems[existingItemIndex].quantity += 1
  } else {
    // If new product, add to cart
    cartItems.push({
      id: product.id,
      title: product.title,
      price: product.price,
      image: product.image,
      quantity: 1,
    })
  }

  // Save to localStorage
  localStorage.setItem("cartItems", JSON.stringify(cartItems))

  // Update UI
  renderCartItems()
  calculateTotals()

  // Show success message
  showAddToCartSuccess(product.title)
}

function showAddToCartSuccess(productName) {
  // Create success notification
  const notification = document.createElement("div")
  notification.className = "cart-success-notification"
  notification.innerHTML = `
        <div class="success-content">
            <i class="ri-check-line"></i>
            <span>${productName} added to cart!</span>
        </div>
    `

  // Add styles
  notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: #4CAF50;
        color: white;
        padding: 15px 20px;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        z-index: 10000;
        animation: slideInRight 0.3s ease-out;
    `

  document.body.appendChild(notification)

  // Remove after 3 seconds
  setTimeout(() => {
    notification.style.animation = "slideOutRight 0.3s ease-in"
    setTimeout(() => {
      if (notification.parentNode) {
        notification.parentNode.removeChild(notification)
      }
    }, 300)
  }, 3000)
}

// Initialize checkout page
document.addEventListener("DOMContentLoaded", () => {
  loadCartData()
  renderCartItems()
  calculateTotals()
  populateCityList()

  initializeCarousel()
  initializeAddToCartButtons()
})

function initializeAddToCartButtons() {
  const addToCartButtons = document.querySelectorAll(".psc-hover-btn")

  addToCartButtons.forEach((button, index) => {
    if (button.textContent.trim() === "Add To Cart") {
      // Calculate product ID based on button index (each product has 2 buttons: Add to Cart and View)
      const productId = Math.floor(index / 2) + 1

      button.addEventListener("click", (e) => {
        e.stopPropagation()
        addToCartFromProducts(productId)
      })
    } else if (button.textContent.trim() === "View") {
      button.addEventListener("click", (e) => {
        e.stopPropagation()
        const productId = Math.floor(index / 2) + 1
        const product = topSellingProducts.find((p) => p.id === productId)
        alert(`Viewing ${product.title}...`)
      })
    }
  })
}

// Render cart items in order summary
function renderCartItems() {
  const cartItemsContainer = document.getElementById("cartItems")
  const itemCount = document.getElementById("itemCount")

  if (!cartItems || cartItems.length === 0) {
    cartItemsContainer.innerHTML = '<div class="empty-cart">Your cart is empty</div>'
    itemCount.textContent = "0"
    return
  }

  itemCount.textContent = cartItems.length

  let cartHTML = ""
  cartItems.forEach((item, index) => {
    // Convert price string to number (remove $ and commas)
    const price = Number.parseFloat(item.price.replace(/[$,]/g, ""))
    const total = price * item.quantity

    cartHTML += `
            <div class="cart-item">
                <div class="item-details">
                    <img src="${item.image}" alt="${item.title}" class="item-image">
                    <div class="item-info">
                        <div class="item-title">${item.title}</div>
                        <div class="item-shipping">Shipping: $ 149</div>
                    </div>
                </div>
                <div class="item-price">$ ${price.toLocaleString()}</div>
                <div class="quantity-controls">
                    <button class="qty-btn" onclick="updateQuantity(${index}, -1)">−</button>
                    <input type="number" class="qty-input" value="${item.quantity}" onchange="setQuantity(${index}, this.value)" min="1">
                    <button class="qty-btn" onclick="updateQuantity(${index}, 1)">+</button>
                </div>
                <div class="item-total">${total.toLocaleString()}</div>
                <div class="item-action">
                    <button class="remove-btn" onclick="removeItem(${index})">Remove</button>
                </div>
            </div>
        `
  })

  cartItemsContainer.innerHTML = cartHTML
}

// Update item quantity
function updateQuantity(index, change) {
  if (cartItems[index]) {
    cartItems[index].quantity = Math.max(1, cartItems[index].quantity + change)
    localStorage.setItem("cartItems", JSON.stringify(cartItems))
    renderCartItems()
    calculateTotals()
  }
}

// Set specific quantity
function setQuantity(index, quantity) {
  const qty = Number.parseInt(quantity)
  if (cartItems[index] && qty >= 1) {
    cartItems[index].quantity = qty
    localStorage.setItem("cartItems", JSON.stringify(cartItems))
    renderCartItems()
    calculateTotals()
  }
}

// Remove item from cart
function removeItem(index) {
  if (cartItems[index]) {
    cartItems.splice(index, 1)
    localStorage.setItem("cartItems", JSON.stringify(cartItems))

    // Update addedToCart in localStorage
    const addedToCart = JSON.parse(localStorage.getItem("addedToCart") || "[]")
    localStorage.setItem("addedToCart", JSON.stringify(addedToCart))

    renderCartItems()
    calculateTotals()
  }
}

// Calculate totals
function calculateTotals() {
  if (!cartItems || cartItems.length === 0) {
    document.getElementById("itemsTotal").textContent = "$ 0"
    document.getElementById("grandTotal").textContent = "$ 0"
    return
  }

  let itemsTotal = 0
  cartItems.forEach((item) => {
    const price = Number.parseFloat(item.price.replace(/[$,]/g, ""))
    itemsTotal += price * item.quantity
  })

  const shippingCharges = 149
  const salesTaxRate = 0.02
  const salesTax = Math.round(itemsTotal * salesTaxRate)
  const discount = 0 // Can be updated when discount is applied

  const grandTotal = itemsTotal + shippingCharges + salesTax - discount

  document.getElementById("itemsTotal").textContent = `$ ${itemsTotal.toLocaleString()}`
  document.getElementById("shippingCharges").textContent = shippingCharges.toString()
  document.getElementById("salesTax").textContent = salesTax.toString()
  document.getElementById("discount").textContent = discount.toString()
  document.getElementById("grandTotal").textContent = `$ ${grandTotal.toLocaleString()}`
}

// Apply discount code
function applyDiscount() {
  const discountCode = document.getElementById("discountCode").value.trim()
  if (discountCode) {
    // Simple discount logic - you can expand this
    if (discountCode.toUpperCase() === "SAVE10") {
      alert("Discount applied: 10% off")
      // Update discount calculation
      calculateTotals()
    } else {
      alert("Invalid discount code")
    }
  }
}

// Navigation functions
function goToShippingInfo() {
  if (validateOrderSummary()) {
    currentStep = 2
    updateSteps()
    showSection("shippingInfoSection")
  }
}

function goToOrderSummary() {
  currentStep = 1
  updateSteps()
  showSection("orderSummarySection")
}

function goToPaymentMethod() {
  if (validateShippingInfo()) {
    currentStep = 3
    updateSteps()
    showSection("paymentMethodSection")
  }
}

// Show specific section
function showSection(sectionId) {
  // Hide all sections
  document.querySelectorAll(".checkout-section").forEach((section) => {
    section.classList.remove("active")
  })

  // Show target section
  document.getElementById(sectionId).classList.add("active")
}

// Update progress steps
function updateSteps() {
  document.querySelectorAll(".step").forEach((step, index) => {
    step.classList.remove("active", "completed")

    if (index + 1 < currentStep) {
      step.classList.add("completed")
    } else if (index + 1 === currentStep) {
      step.classList.add("active")
    }
  })
}

// Validation functions
function validateOrderSummary() {
  if (!cartItems || cartItems.length === 0) {
    alert("Your cart is empty")
    return false
  }
  return true
}

function validateShippingInfo() {
  const name = document.getElementById("customerName").value.trim()
  const mobile = document.getElementById("mobileNumber").value.trim()
  const city = document.getElementById("cityInput").value.trim()
  const address = document.getElementById("address").value.trim()

  if (!name) {
    alert("Please enter your name")
    return false
  }

  if (!mobile) {
    alert("Please enter your mobile number")
    return false
  }

  if (!city) {
    alert("Please select a city")
    return false
  }

  if (!address) {
    alert("Please enter your address")
    return false
  }

  return true
}

// City modal functions
function openCityModal() {
  const modal = document.getElementById("cityModal")
  const overlay = document.getElementById("modalOverlay")

  modal.classList.add("show")
  overlay.classList.add("show")
}

function closeCityModal() {
  const modal = document.getElementById("cityModal")
  const overlay = document.getElementById("modalOverlay")

  modal.classList.remove("show")
  overlay.classList.remove("show")
}

function populateCityList() {
  const cityList = document.getElementById("cityList")

  let cityHTML = ""
  Object.keys(saudiCities).forEach((city) => {
    cityHTML += `
            <div class="city-item" onclick="selectCity('${city}')">
                <span>${city}</span>
                <i class="ri-arrow-right-s-line"></i>
            </div>
        `
  })

  cityList.innerHTML = cityHTML
}

function selectCity(city) {
  selectedCity = city
  selectedArea = ""

  // Update UI
  document.querySelectorAll(".city-item").forEach((item) => {
    item.classList.remove("selected")
  })

  event.target.classList.add("selected")

  // Populate areas
  populateAreaList(city)
}

function populateAreaList(city) {
  const areaList = document.getElementById("areaList")
  const areas = saudiCities[city] || []

  let areaHTML = ""
  areas.forEach((area) => {
    areaHTML += `
            <div class="area-item" onclick="selectArea('${area}')">
                <span>${area}</span>
            </div>
        `
  })

  areaList.innerHTML = areaHTML
}

function selectArea(area) {
  selectedArea = area

  // Update UI
  document.querySelectorAll(".area-item").forEach((item) => {
    item.classList.remove("selected")
  })

  event.target.classList.add("selected")
}

function confirmCitySelection() {
  if (selectedCity) {
    const cityInput = document.getElementById("cityInput")
    const cityAreaGroup = document.getElementById("cityAreaGroup")
    const cityAreaSelect = document.getElementById("cityAreaSelect")

    cityInput.value = selectedCity

    // Show city area dropdown if areas are available
    if (saudiCities[selectedCity]) {
      cityAreaGroup.style.display = "block"

      // Populate city area select
      let optionsHTML = '<option value="">Select Area</option>'
      saudiCities[selectedCity].forEach((area) => {
        optionsHTML += `<option value="${area}">${area}</option>`
      })
      cityAreaSelect.innerHTML = optionsHTML

      // Set selected area if any
      if (selectedArea) {
        cityAreaSelect.value = selectedArea
      }
    }

    closeCityModal()
  } else {
    alert("Please select a city")
  }
}

// Payment processing
function processPayment() {
  if (validateShippingInfo()) {
    showVerifyModal()
  }
}

function showVerifyModal() {
  const modal = document.getElementById("verifyModal")
  const overlay = document.getElementById("modalOverlay")

  modal.classList.add("show")
  overlay.classList.add("show")
}

function closeVerifyModal() {
  const modal = document.getElementById("verifyModal")
  const overlay = document.getElementById("modalOverlay")

  modal.classList.remove("show")
  overlay.classList.remove("show")
}

function verifyNumber() {
  const code = document.getElementById("verifyCode").value.trim()

  if (!code) {
    alert("Please enter the verification code")
    return
  }

  if (code.length < 4) {
    alert("Please enter a valid verification code")
    return
  }

  // Simulate verification success
  closeVerifyModal()
  showSuccessAlert()

  // Clear cart after successful order
  setTimeout(() => {
    clearCart()
    // Redirect back to main page or order confirmation
    window.location.href = "index.html"
  }, 3000)
}

function showSuccessAlert() {
  const alert = document.getElementById("successAlert")
  alert.classList.add("show")
}

function closeSuccessAlert() {
  const alert = document.getElementById("successAlert")
  alert.classList.remove("show")
}

function clearCart() {
  cartItems = []
  localStorage.removeItem("cartItems")
  localStorage.removeItem("addedToCart")
}

// Close modals when clicking outside
document.addEventListener("click", (e) => {
  if (e.target.id === "cityModal") {
    closeCityModal()
  }
  if (e.target.id === "verifyModal") {
    closeVerifyModal()
  }
  if (e.target.id === "modalOverlay") {
    closeCityModal()
    closeVerifyModal()
  }
})

// Handle ESC key to close modals
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") {
    closeCityModal()
    closeVerifyModal()
  }
})

function initializeCarousel() {
  const carouselWrapper = document.getElementById("pscCarouselWrapper")
  const prevBtn = document.getElementById("pscPrevBtn")
  const nextBtn = document.getElementById("pscNextBtn")

  if (!carouselWrapper || !prevBtn || !nextBtn) return

  let currentIndex = 0
  const cardWidth = 300 // 280px card + 20px margin
  const visibleCards = 4
  const totalCards = 12
  const maxIndex = totalCards - visibleCards

  function updateCarousel() {
    const translateX = -currentIndex * cardWidth
    carouselWrapper.style.transform = `translateX(${translateX}px)`

    // Update button states
    prevBtn.disabled = currentIndex === 0
    nextBtn.disabled = currentIndex >= maxIndex
  }

  prevBtn.addEventListener("click", () => {
    if (currentIndex > 0) {
      currentIndex--
      updateCarousel()
    }
  })

  nextBtn.addEventListener("click", () => {
    if (currentIndex < maxIndex) {
      currentIndex++
      updateCarousel()
    }
  })

  // Initialize carousel
  updateCarousel()
}

const style = document.createElement("style")
style.textContent = `
    @keyframes slideInRight {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOutRight {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
    
    .cart-success-notification .success-content {
        display: flex;
        align-items: center;
        gap: 10px;
    }
    
    .cart-success-notification i {
        font-size: 18px;
    }
`
document.head.appendChild(style)
