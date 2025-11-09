const images = [
  "/images/cars/sg-11134201-22110-z5627tkr4gjve9.jpeg",
  "/images/cars/id-11134207-7rasm-m3ll6tdd8oz37c.jpeg",
  "/images/cars/id-11134207-7rasc-m3x4wtcjzwa6f2.jpeg",
]

let currentImageIndex = 0

function selectImage(index) {
  currentImageIndex = index
  document.getElementById("mainImage").src = images[index]

  // Remove active class from all thumbnails
  const thumbnails = document.querySelectorAll(".pw-gallery-thumbnail")
  thumbnails.forEach((thumb) => thumb.classList.remove("active"))

  // Add active class to selected thumbnail
  thumbnails[index].classList.add("active")
}

function nextImage() {
  currentImageIndex = (currentImageIndex + 1) % images.length
  selectImage(currentImageIndex)
}

function previousImage() {
  currentImageIndex = (currentImageIndex - 1 + images.length) % images.length
  selectImage(currentImageIndex)
}

function increaseQuantity() {
  const quantityInput = document.getElementById("pw-quantity-input")
  const currentValue = Number.parseInt(quantityInput.value)
  quantityInput.value = currentValue + 1
}

function decreaseQuantity() {
  const quantityInput = document.getElementById("pw-quantity-input")
  const currentValue = Number.parseInt(quantityInput.value)
  if (currentValue > 1) {
    quantityInput.value = currentValue - 1
  }
}

function scrollProductsLeft() {
  const carousel = document.getElementById("productsCarousel")
  carousel.scrollBy({
    left: -300,
    behavior: "smooth",
  })
}

function scrollProductsRight() {
  const carousel = document.getElementById("productsCarousel")
  carousel.scrollBy({
    left: 300,
    behavior: "smooth",
  })
}
