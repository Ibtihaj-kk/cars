const dropdownTimeouts = {}

// Mobile Menu Functionality
function initializeMobileMenu() {
  const mobileMenuToggle = document.getElementById("mobileMenuToggle")
  const mobileMenuOverlay = document.getElementById("mobileMenuOverlay")
  const mobileMenuClose = document.getElementById("mobileMenuClose")

  if (mobileMenuToggle && mobileMenuOverlay && mobileMenuClose) {
    mobileMenuToggle.addEventListener("click", () => {
      mobileMenuToggle.classList.toggle("active")
      mobileMenuOverlay.classList.toggle("active")
      document.body.style.overflow = mobileMenuOverlay.classList.contains("active") ? "hidden" : ""
    })

    mobileMenuClose.addEventListener("click", () => {
      mobileMenuToggle.classList.remove("active")
      mobileMenuOverlay.classList.remove("active")
      document.body.style.overflow = ""
    })

    mobileMenuOverlay.addEventListener("click", (e) => {
      if (e.target === mobileMenuOverlay) {
        mobileMenuToggle.classList.remove("active")
        mobileMenuOverlay.classList.remove("active")
        document.body.style.overflow = ""
      }
    })

    initializeMobileDropdowns()
  }
}

// Mobile Dropdown Functionality
function initializeMobileDropdowns() {
  const mobileDropdownTriggers = document.querySelectorAll(".mobile-dropdown-trigger")

  mobileDropdownTriggers.forEach((trigger) => {
    trigger.addEventListener("click", function () {
      const dropdownType = this.getAttribute("data-dropdown")
      const dropdownContent = document.getElementById(`mobile-${dropdownType}-dropdown`)

      if (dropdownContent) {
        this.classList.toggle("active")
        dropdownContent.classList.toggle("active")

        // Close other open dropdowns
        mobileDropdownTriggers.forEach((otherTrigger) => {
          if (otherTrigger !== this) {
            const otherDropdownType = otherTrigger.getAttribute("data-dropdown")
            const otherDropdownContent = document.getElementById(`mobile-${otherDropdownType}-dropdown`)
            if (otherDropdownContent) {
              otherTrigger.classList.remove("active")
              otherDropdownContent.classList.remove("active")
            }
          }
        })
      }
    })
  })
}

// Load navbar and footer
function loadNavbarAndFooter() {
  console.log("[v0] Starting to load navbar and footer")

  // Load navbar
  fetch("/navbar.html")
    .then((res) => {
      if (!res.ok) {
        throw new Error(`HTTP error! status: ${res.status}`)
      }
      return res.text()
    })
    .then((data) => {
      const navbarElement = document.getElementById("navbar")
      if (navbarElement) {
        navbarElement.innerHTML = data
        console.log("[v0] Navbar loaded successfully")
        initializeDropdowns()
        initializeMobileMenu() // Initialize mobile menu after navbar loads
      } else {
        console.error("[v0] Navbar element not found")
      }
    })
    .catch((error) => {
      console.error("[v0] Error loading navbar:", error)
    })

  // Load footer
  fetch("/footer.html")
    .then((res) => {
      if (!res.ok) {
        throw new Error(`HTTP error! status: ${res.status}`)
      }
      return res.text()
    })
    .then((data) => {
      const footerElement = document.getElementById("footer")
      if (footerElement) {
        footerElement.innerHTML = data
        console.log("[v0] Footer loaded successfully")
      } else {
        console.error("[v0] Footer element not found")
      }
    })
    .catch((error) => {
      console.error("[v0] Error loading footer:", error)
    })
}

// Updated dropdown functions with improved handling
function showDropdown(dropdownId = "dropdown-content") {
  // Clear any existing timeout for this dropdown
  if (dropdownTimeouts[dropdownId]) {
    clearTimeout(dropdownTimeouts[dropdownId])
    delete dropdownTimeouts[dropdownId]
  }

  const dropdown = document.getElementById(dropdownId)
  if (dropdown) {
    dropdown.classList.add("show")
    console.log("[v0] Dropdown shown:", dropdownId)
  }
}

function hideDropdown(dropdownId = "dropdown-content") {
  // Clear any existing timeout first
  if (dropdownTimeouts[dropdownId]) {
    clearTimeout(dropdownTimeouts[dropdownId])
  }

  // Set new timeout with shorter delay for faster response
  dropdownTimeouts[dropdownId] = setTimeout(() => {
    const dropdown = document.getElementById(dropdownId)
    if (dropdown) {
      dropdown.classList.remove("show")
      console.log("[v0] Dropdown hidden:", dropdownId)
    }
    // Clean up the timeout reference
    delete dropdownTimeouts[dropdownId]
  }, 50)
}

// Tab switching function
function switchTab(tabId, clickedLink, dropdownId = "dropdown-content") {
  console.log("[v0] Switching to tab:", tabId, "in dropdown:", dropdownId)

  // Get the dropdown container
  const dropdownContainer = document.getElementById(dropdownId)
  if (!dropdownContainer) {
    console.error("[v0] Dropdown container not found:", dropdownId)
    return
  }

  // Remove active class from all tab links within this dropdown
  const allTabLinks = dropdownContainer.querySelectorAll(".tab-link")
  allTabLinks.forEach((link) => link.classList.remove("active"))

  // Add active class to current tab link
  if (clickedLink) {
    clickedLink.classList.add("active")
  }

  // Hide all tab contents within this dropdown
  const allTabContents = dropdownContainer.querySelectorAll(".tab-content")
  allTabContents.forEach((content) => content.classList.remove("active"))

  // Show the selected tab content within this dropdown
  const selectedContent = dropdownContainer.querySelector("#" + tabId + "-content")
  if (selectedContent) {
    selectedContent.classList.add("active")
    console.log("[v0] Tab content shown:", tabId + "-content")
  } else {
    console.error("[v0] Tab content not found:", tabId + "-content")
  }
}

// Initialize dropdown functionality for multiple dropdowns
function initializeDropdowns() {
  console.log("[v0] Initializing dropdown functionality")

  setTimeout(() => {
    // Initialize dropdown triggers first
    initializeDropdownTriggers()

    // Get all dropdown containers
    const dropdownContainers = document.querySelectorAll(".dropdown-content")

    dropdownContainers.forEach((dropdownContainer) => {
      const dropdownId = dropdownContainer.id
      console.log("[v0] Initializing dropdown:", dropdownId)

      // Set default active tab for this dropdown
      const defaultTab = dropdownContainer.querySelector(".tab-link.active")
      if (defaultTab) {
        const tabId = defaultTab.getAttribute("data-tab")
        if (tabId) {
          switchTab(tabId, defaultTab, dropdownId)
        }
      } else {
        const firstTab = dropdownContainer.querySelector(".tab-link")
        if (firstTab) {
          const tabId = firstTab.getAttribute("data-tab")
          if (tabId) {
            firstTab.classList.add("active")
            switchTab(tabId, firstTab, dropdownId)
          }
        }
      }

      // Add hover event listeners to tab links within this dropdown
      const tabLinks = dropdownContainer.querySelectorAll(".tab-link")
      console.log("[v0] Found tab links in", dropdownId, ":", tabLinks.length)
      tabLinks.forEach((tabLink) => {
        tabLink.addEventListener("mouseenter", function () {
          const tabId = this.getAttribute("data-tab")
          if (tabId) {
            switchTab(tabId, this, dropdownId)
          }
        })
      })

      // Keep dropdown open when hovering over dropdown content
      dropdownContainer.addEventListener("mouseenter", () => {
        if (dropdownTimeouts[dropdownId]) {
          clearTimeout(dropdownTimeouts[dropdownId])
          delete dropdownTimeouts[dropdownId]
        }
      })

      dropdownContainer.addEventListener("mouseleave", () => {
        hideDropdown(dropdownId)
      })
    })

    console.log("[v0] All dropdowns initialization complete")
  }, 100)
}

// New function to properly initialize dropdown triggers
function initializeDropdownTriggers() {
  // Find all dropdown triggers
  const dropdownTriggers = document.querySelectorAll(".new-dropdown")

  dropdownTriggers.forEach((trigger) => {
    // Remove existing event listeners to prevent duplicates
    const newTrigger = trigger.cloneNode(true)
    trigger.parentNode.replaceChild(newTrigger, trigger)

    // Find the dropdown content ID for this trigger
    const dropdownContent = newTrigger.querySelector(".dropdown-content")
    if (dropdownContent) {
      const dropdownId = dropdownContent.id

      // Add mouseenter event
      newTrigger.addEventListener("mouseenter", () => {
        showDropdown(dropdownId)
      })

      // Add mouseleave event
      newTrigger.addEventListener("mouseleave", () => {
        hideDropdown(dropdownId)
      })

      console.log("[v0] Initialized dropdown trigger for:", dropdownId)
    }
  })
}

// Additional function to ensure dropdowns work on all pages
function ensureDropdownFunctionality() {
  // Wait a bit longer and try again if dropdowns aren't working
  setTimeout(() => {
    const dropdowns = document.querySelectorAll(".dropdown-content")
    if (dropdowns.length === 0) {
      console.log("[v0] No dropdowns found, retrying...")
      initializeDropdowns()
    }
  }, 500)
}

function handleWindowResize() {
  const mobileMenuToggle = document.getElementById("mobileMenuToggle")
  const mobileMenuOverlay = document.getElementById("mobileMenuOverlay")

  if (window.innerWidth > 768) {
    if (mobileMenuToggle) mobileMenuToggle.classList.remove("active")
    if (mobileMenuOverlay) mobileMenuOverlay.classList.remove("active")
    document.body.style.overflow = ""
  }
}

// Check if DOM is already loaded, if not wait for it
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => {
    loadNavbarAndFooter()
    ensureDropdownFunctionality()
    initializeMobileMenu() // Initialize mobile menu on DOM load
    window.addEventListener("resize", handleWindowResize) // Add resize listener
  })
} else {
  // DOM is already loaded, execute immediately
  loadNavbarAndFooter()
  ensureDropdownFunctionality()
  initializeMobileMenu() // Initialize mobile menu immediately
  window.addEventListener("resize", handleWindowResize) // Add resize listener
}

// Make functions globally available
window.showDropdown = showDropdown
window.hideDropdown = hideDropdown
window.switchTab = switchTab
