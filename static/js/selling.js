// Testimonials Carousel
let currentSlide = 0;
const totalSlides = 3; // We show 3 cards at a time, so we have 3 slides
const cardsPerSlide = 3;
const totalCards = 9;

const slider = document.getElementById("testimonialsSlider");
const prevBtn = document.getElementById("prevBtn");
const nextBtn = document.getElementById("nextBtn");
const dots = document.querySelectorAll(".dot");

function updateSlider() {
  const translateX = -(currentSlide * 100);
  slider.style.transform = `translateX(${translateX}%)`;

  // Update dots
  dots.forEach((dot, index) => {
    dot.classList.toggle("active", index === currentSlide);
  });
}

function nextSlide() {
  currentSlide = (currentSlide + 1) % totalSlides;
  updateSlider();
}

function prevSlide() {
  currentSlide = (currentSlide - 1 + totalSlides) % totalSlides;
  updateSlider();
}

// Event listeners for navigation
if (nextBtn) nextBtn.addEventListener("click", nextSlide);
if (prevBtn) prevBtn.addEventListener("click", prevSlide);

// Dot navigation
dots.forEach((dot, index) => {
  dot.addEventListener("click", () => {
    currentSlide = index;
    updateSlider();
  });
});

// Auto-slide (optional)
setInterval(nextSlide, 5000);

// Why Sell Dropdown functionality - Unique Implementation
const whySellDropdownHeader = document.getElementById("whySellDropdownHeader");
const whySellDropdownContent = document.getElementById("whySellDropdownContent");
const whySellDropdownArrow = document.getElementById("whySellDropdownArrow");

if (whySellDropdownHeader && whySellDropdownContent && whySellDropdownArrow) {
  whySellDropdownHeader.addEventListener("click", function () {
    const isOpen = whySellDropdownContent.classList.contains("why-sell-open");

    if (isOpen) {
      whySellDropdownContent.classList.remove("why-sell-open");
      whySellDropdownArrow.classList.remove("why-sell-rotated");
      whySellDropdownArrow.innerHTML = '<i class="fa-solid fa-angle-down"></i>';
    } else {
      whySellDropdownContent.classList.add("why-sell-open");
      whySellDropdownArrow.classList.add("why-sell-rotated");
      whySellDropdownArrow.innerHTML = '<i class="fa-solid fa-angle-up"></i>';
    }
  });
}

// Package selection functionality - FIXED
const packageCards = document.querySelectorAll(".package-card");
const packageButtons = document.querySelectorAll(".package-btn");

packageCards.forEach((packageCard) => {
  packageCard.addEventListener("click", function () {
    // Remove selected class from all packages
    packageCards.forEach((p) => p.classList.remove("selected"));
    // Add selected class to clicked package
    this.classList.add("selected");
  });
});

packageButtons.forEach((button) => {
  button.addEventListener("click", function (e) {
    e.stopPropagation(); // Prevent triggering package card click
    
    const packageType = this.classList.contains("basic")
      ? "Basic"
      : this.classList.contains("super")
      ? "Super"
      : "Hyper";
    
    alert(`You selected the ${packageType} package! Proceeding to next step...`);
    
    // Here you can add navigation to next step
    // window.location.href = "/next-step";
  });
});

// Step indicator functionality
const steps = document.querySelectorAll(".step");

function activateStep(stepIndex) {
  steps.forEach((step, index) => {
    if (index <= stepIndex) {
      step.classList.add("active");
    } else {
      step.classList.remove("active");
    }
  });
}

// Initialize first step as active
activateStep(0);

// Smooth scrolling for better UX
function smoothScroll(target) {
  const element = document.querySelector(target);
  if (element) {
    element.scrollIntoView({
      behavior: "smooth",
    });
  }
}

// Add some hover effects
document.addEventListener("DOMContentLoaded", function () {
  // Add hover effects to package cards
  packageCards.forEach((packageCard) => {
    packageCard.addEventListener("mouseenter", function () {
      if (!this.classList.contains("popular")) {
        this.style.transform = "translateY(-2px)";
        this.style.transition = "transform 0.2s ease";
      }
    });

    packageCard.addEventListener("mouseleave", function () {
      if (!this.classList.contains("popular")) {
        this.style.transform = "translateY(0)";
      }
    });
  });

  // Add hover effects to work steps
  const workSteps = document.querySelectorAll(".work-step");
  workSteps.forEach((step) => {
    step.addEventListener("mouseenter", function () {
      this.style.transform = "translateY(-2px)";
      this.style.transition = "transform 0.2s ease";
    });

    step.addEventListener("mouseleave", function () {
      this.style.transform = "translateY(0)";
    });
  });

  // Add click effects to testimonial navigation
  const navArrows = document.querySelectorAll(".nav-arrow");
  navArrows.forEach((arrow) => {
    arrow.addEventListener("mousedown", function () {
      this.style.transform = "scale(0.95)";
    });

    arrow.addEventListener("mouseup", function () {
      this.style.transform = "scale(1)";
    });

    arrow.addEventListener("mouseleave", function () {
      this.style.transform = "scale(1)";
    });
  });
});
