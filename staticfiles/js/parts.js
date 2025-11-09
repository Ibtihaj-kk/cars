// Product data
const products = [
{
id: 1,
title: "AIRR High Pressure Washer",
price: "$5,176",
originalPrice: "$6,470",
location: "Riyadh",
image: "/images/cars/OIP.jpeg",
onSale: true,
rating: 4.5,
reviews: 12,
category: "GTX MOTORSPORTS",
link: "products.html",
},
{
id: 2,
title: "Wiper Blades Toyota Prius",
price: "$13,999",
originalPrice: "$15,999",
location: "Riyadh",
image: "//images.pexels.com/photos/13065690/pexels-photo-13065690.jpeg?auto=compress&cs=tinysrgb&w=300",
onSale: true,
rating: 4.4,
reviews: 9,
category: "GTX MOTORSPORTS",
},
{
id: 3,
title: "TOYOTA PRIUS HYBRID",
price: "$17,499",
originalPrice: "$25,801",
location: "Madinah",
image: "//images.pexels.com/photos/3964736/pexels-photo-3964736.jpeg?auto=compress&cs=tinysrgb&w=300",
onSale: true,
rating: 4.6,
reviews: 5,
category: "GTX MOTORSPORTS",
},
{
id: 4,
title: "Toyota Corolla Engine Oil Filter Premium",
price: "$1,250",
originalPrice: "$1,500",
location: "Taif",
image: "//images.pexels.com/photos/3807277/pexels-photo-3807277.jpeg?auto=compress&cs=tinysrgb&w=300",
onSale: true,
rating: 4.2,
reviews: 8,
category: "GTX MOTORSPORTS",
},
{
id: 5,
title: "LED Headlight Bulbs H4 High Performance",
price: "$2,300",
originalPrice: "$2,999",
location: "Dammam",
image: "//images.pexels.com/photos/13065690/pexels-photo-13065690.jpeg?auto=compress&cs=tinysrgb&w=300",
onSale: true,
rating: 4.3,
reviews: 6,
category: "GTX MOTORSPORTS",
},
{
id: 6,
title: "Car Dashboard Cover Anti-UV Protection",
price: "$3,250",
originalPrice: "$4,500",
location: "Madinah",
image: "//images.pexels.com/photos/3964736/pexels-photo-3964736.jpeg?auto=compress&cs=tinysrgb&w=300",
onSale: true,
rating: 4.1,
reviews: 4,
category: "GTX MOTORSPORTS",
},
{
id: 7,
title: "Suzuki Swift Side Mirror Assembly Left",
price: "$4,800",
originalPrice: "$5,500",
location: "Sakaka",
image: "//images.pexels.com/photos/3807277/pexels-photo-3807277.jpeg?auto=compress&cs=tinysrgb&w=300",
onSale: true,
rating: 4.0,
reviews: 3,
category: "GTX MOTORSPORTS",
},
{
id: 8,
title: "Premium Car Wax Polish 500ml",
price: "$1,899",
originalPrice: "$2,199",
location: "Dammam",
image: "//images.pexels.com/photos/13065690/pexels-photo-13065690.jpeg?auto=compress&cs=tinysrgb&w=300",
onSale: true,
rating: 4.4,
reviews: 7,
category: "GTX MOTORSPORTS",
}
];

// Make data for popup
const makeData = [
// Column 1
{ name: "Audi", count: "157" },
{ name: "BAW", count: "2" },
{ name: "BYD", count: "32" },
{ name: "Chery", count: "57" },
{ name: "Chrysler", count: "1" },
{ name: "Daewoo", count: "8" },
{ name: "Deepal", count: "20" },
{ name: "FAW", count: "68" },
{ name: "Ford", count: "37" },
{ name: "Haval", count: "150" },
{ name: "Honda", count: "3638" },
{ name: "Hyundai", count: "596" },
{ name: "Isuzu", count: "42" },
{ name: "JAC", count: "22" },
{ name: "Jeep", count: "15" },
{ name: "KIA", count: "620" },
{ name: "Land Rover", count: "85" },
{ name: "Lexus", count: "142" },
{ name: "MG", count: "198" },
{ name: "Mazda", count: "121" },
{ name: "Mercedes Benz", count: "203" },
{ name: "Mitsubishi", count: "547" },
{ name: "Nissan", count: "879" },
{ name: "Peugeot", count: "25" },
{ name: "Proton", count: "59" },
{ name: "Regal Raptor", count: "1" },
{ name: "Renault", count: "12" },
{ name: "SAIPA", count: "3" },
{ name: "Skoda", count: "18" },
// Column 2
{ name: "BMW", count: "160" },
{ name: "Changan", count: "213" },
{ name: "Chevrolet", count: "31" },
{ name: "DFSK", count: "85" },
{ name: "Daihatsu", count: "981" },
{ name: "Dongfeng", count: "9" },
{ name: "Fiat", count: "3" },
{ name: "GUGO", count: "2" },
{ name: "Hino", count: "10" },
{ name: "Honri", count: "1" },
{ name: "Inverex", count: "1" },
{ name: "JAC Motors", count: "32" },
{ name: "Jinbei", count: "5" },
{ name: "Kaiyi", count: "12" },
{ name: "Lada", count: "8" },
{ name: "Lifan", count: "28" },
{ name: "MINI", count: "25" },
{ name: "MG Motors", count: "45" },
{ name: "Opel", count: "15" },
{ name: "Prince", count: "8" },
{ name: "Rolls Royce", count: "2" },
{ name: "SEAT", count: "8" },
{ name: "Sazgar", count: "15" },
{ name: "Subaru", count: "35" },
{ name: "Suzuki", count: "2333" },
{ name: "Tesla", count: "12" },
{ name: "Toyota", count: "5498" },
{ name: "Volkswagen", count: "98" },
{ name: "Volvo", count: "42" }
];

// Brand data for popup
const brandData = [
// Column 1
{ name: "Turtle", count: "61" },
{ name: "7CF", count: "32" },
{ name: "AREON", count: "53" },
{ name: "Airpro", count: "10" },
{ name: "Alfa Pak", count: "11" },
{ name: "ArmorAll", count: "16" },
{ name: "Asian", count: "31" },
{ name: "Asuki Advanced", count: "541" },
{ name: "Benaz", count: "220" },
{ name: "Bullsone", count: "64" },
{ name: "Caltex", count: "39" },
{ name: "Car Mate", count: "85" },
{ name: "Chemical Guys", count: "45" },
{ name: "Comma", count: "28" },
{ name: "Crown", count: "92" },
{ name: "DENSO", count: "942" },
{ name: "Exedy", count: "156" },
{ name: "Febi", count: "89" },
{ name: "Formula Shell", count: "35" },
{ name: "Gates", count: "78" },
{ name: "Genuine Toyota", count: "324" },
{ name: "Gloss", count: "22" },
{ name: "GTX", count: "156" },
{ name: "Hella", count: "89" },
{ name: "Hi-Q", count: "234" },
{ name: "Honeywell", count: "45" },
{ name: "IPF", count: "67" },
{ name: "K&N", count: "125" },
// Column 2
{ name: "ABRO", count: "58" },
{ name: "Addinol", count: "34" },
{ name: "Aisin", count: "40" },
{ name: "Amsoil", count: "71" },
{ name: "Aroma", count: "93" },
{ name: "Asuki", count: "705" },
{ name: "BOSCH", count: "53" },
{ name: "BluLight", count: "8" },
{ name: "Castrol", count: "156" },
{ name: "Champion", count: "67" },
{ name: "Coido", count: "89" },
{ name: "CRC", count: "45" },
{ name: "Dupli Color", count: "23" },
{ name: "Eurotek", count: "78" },
{ name: "Forch", count: "34" },
{ name: "Genuine Honda", count: "198" },
{ name: "Gold Eagle", count: "25" },
{ name: "GSP", count: "112" },
{ name: "Hankook", count: "45" },
{ name: "Holts", count: "67" },
{ name: "Idemitsu", count: "89" },
{ name: "Liqui Moly", count: "234" },
{ name: "Mannol", count: "156" },
{ name: "Maxima", count: "78" },
{ name: "Meguiar's", count: "145" },
{ name: "Mobil", count: "189" },
{ name: "NGK", count: "267" },
{ name: "Osram", count: "123" }
];

// City data for popup
const cityData = [
// Column 1
{ name: "Riyadh", count: "12000" },
{ name: "Jeddah", count: "9500" },
{ name: "Mecca", count: "4800" },
{ name: "Medina", count: "4200" },
{ name: "Dammam", count: "3700" },
{ name: "Khobar", count: "2500" },
{ name: "Dhahran", count: "1800" },
{ name: "Qatif", count: "1300" },
{ name: "Hofuf", count: "1700" },
{ name: "Al Hasa", count: "1500" },
{ name: "Abha", count: "2100" },
{ name: "Khamis Mushait", count: "2000" },
{ name: "Taif", count: "2600" },
{ name: "Jizan", count: "1200" },
{ name: "Najran", count: "1400" },
{ name: "Tabuk", count: "1900" },
{ name: "Hail", count: "1000" },
{ name: "Al Bahah", count: "800" },
{ name: "Arar", count: "600" },
{ name: "Sakaka", count: "550" },
{ name: "Al Jawf", count: "500" },
{ name: "Yanbu", count: "1100" },
{ name: "Rabigh", count: "700" },
{ name: "Al Qunfudhah", count: "650" },
{ name: "Bisha", count: "900" },
{ name: "Al Majmaah", count: "400" },
{ name: "Al Kharj", count: "1500" },
{ name: "Diriyah", count: "300" },
{ name: "Jubail", count: "2000" },

// Column 2
{ name: "Ras Tanura", count: "750" },
{ name: "Khafji", count: "500" },
{ name: "Al Lith", count: "450" },
{ name: "Al Khafji", count: "350" },
{ name: "Al Zulfi", count: "600" },
{ name: "Al Wajh", count: "300" },
{ name: "Al Ula", count: "400" },
{ name: "Baljurashi", count: "250" },
{ name: "Duba", count: "200" },
{ name: "Sharurah", count: "350" },
{ name: "Rafha", count: "270" },
{ name: "Turaif", count: "220" },
{ name: "Al Qurayyat", count: "330" },
{ name: "Al Bukayriyah", count: "280" },
{ name: "Unaizah", count: "900" },
{ name: "Al Bad", count: "150" },
{ name: "Al Dawadmi", count: "500" },
{ name: "Al Mithnab", count: "200" },
{ name: "Hotat Bani Tamim", count: "180" },
{ name: "Layla", count: "140" },
{ name: "Al Jumum", count: "190" },
{ name: "Al Qatif", count: "1200" },
{ name: "Saihat", count: "1100" },
{ name: "Tarut", count: "800" },
{ name: "Thuwal", count: "160" },
{ name: "Al Muwayh", count: "130" },
{ name: "Wadi Al Dawasir", count: "700" },
{ name: "Samitah", count: "260" },
{ name: "Farasan", count: "120" }
];

// Vehicle data
const vehicleData = {
makes: {
popular: [
{ name: "Toyota", logo: "https://logoeps.com/wp-content/uploads/2013/02/toyota-vector-logo.png" },
{ name: "Suzuki", logo: "https://logoeps.com/wp-content/uploads/2013/03/suzuki-vector-logo.png" },
{ name: "Honda", logo: "https://logoeps.com/wp-content/uploads/2013/03/honda-vector-logo.png" },
{ name: "Daihatsu", logo: "https://logoeps.com/wp-content/uploads/2013/03/daihatsu-vector-logo.png" }
],
others: [
{ name: "Adam", logo: "https://via.placeholder.com/24x24/333/fff?text=A" },
{ name: "Alfa Romeo", logo: "https://logoeps.com/wp-content/uploads/2013/03/alfa-romeo-vector-logo.png" },
{ name: "Audi", logo: "https://logoeps.com/wp-content/uploads/2013/03/audi-vector-logo.png" },
{ name: "BMW", logo: "https://logoeps.com/wp-content/uploads/2013/03/bmw-vector-logo.png" },
{ name: "Changan", logo: "https://via.placeholder.com/24x24/333/fff?text=C" },
{ name: "Chevrolet", logo: "https://logoeps.com/wp-content/uploads/2013/03/chevrolet-vector-logo.png" },
{ name: "Ford", logo: "https://logoeps.com/wp-content/uploads/2013/03/ford-vector-logo.png" },
{ name: "Hyundai", logo: "https://logoeps.com/wp-content/uploads/2013/03/hyundai-vector-logo.png" },
{ name: "KIA", logo: "https://logoeps.com/wp-content/uploads/2013/03/kia-vector-logo.png" },
{ name: "Mazda", logo: "https://logoeps.com/wp-content/uploads/2013/03/mazda-vector-logo.png" },
{ name: "Mercedes Benz", logo: "https://logoeps.com/wp-content/uploads/2013/03/mercedes-benz-vector-logo.png" },
{ name: "Mitsubishi", logo: "https://logoeps.com/wp-content/uploads/2013/03/mitsubishi-vector-logo.png" },
{ name: "Nissan", logo: "https://logoeps.com/wp-content/uploads/2013/03/nissan-vector-logo.png" }
]
},
models: {
Toyota: ["Corolla", "Yaris Sedan", "Aqua", "Fortuner", "Prius", "Camry", "Hiace", "Land Cruiser"],
Honda: ["Civic", "City", "Accord", "CR-V", "BR-V", "Jazz", "Freed", "Vezel"],
Suzuki: ["Alto", "Wagon R", "Swift", "Cultus", "Vitara", "Jimny", "Mehran", "Bolan"],
Daihatsu: ["Mira", "Move", "Tanto", "Cast", "Wake", "Hijet", "Terios"],
Nissan: ["Sunny", "Note", "X-Trail", "Juke", "Patrol", "Pathfinder"],
Adam: ["4 Runner", "86", "Allex"],
"Alfa Romeo": ["Giulia", "Stelvio", "4C"],
Audi: ["A3", "A4", "A6", "Q3", "Q5", "Q7"],
BMW: ["3 Series", "5 Series", "X1", "X3", "X5"],
Changan: ["Alsvin", "Karvaan", "M8", "M9"],
Chevrolet: ["Cruze", "Aveo", "Captiva"],
Ford: ["Focus", "Fiesta", "EcoSport", "Explorer"],
Hyundai: ["Elantra", "Tucson", "Santa Fe", "Ioniq"],
KIA: ["Picanto", "Cerato", "Sportage", "Sorento"],
Mazda: ["2", "3", "6", "CX-3", "CX-5"],
"Mercedes Benz": ["C-Class", "E-Class", "S-Class", "GLA", "GLC"],
Mitsubishi: ["Lancer", "Outlander", "Pajero"],
},
versions: {
"Toyota-Corolla": ["1.8 U Hybrid", "2.0 G Hybrid", "2.0 Z Hybrid", "A", "A Premium", "A Premium Touring Selection", "A Touring Selection", "A Touring Selection Black Edition", "E"],
"Toyota-Yaris": ["1.0 F", "1.3 G", "1.5 Z", "Cross"],
"Toyota-Aqua": ["L", "S", "G", "G Soft Leather Selection"],
"Honda-Civic": ["Oriel", "Turbo", "RS"],
"Honda-City": ["Aspire", "VTi-L", "ZX"],
"Suzuki-Alto": ["VX", "VXR", "VXL"],
"Suzuki-Swift": ["GL", "GLX", "DLX"]
}
};
// ---------- BEGIN: Persist cart helper ----------
function saveCartToLocalStorage() {
    try {
        localStorage.setItem('cartItems', JSON.stringify(cartItems || []));
        localStorage.setItem('addedToCart', JSON.stringify(Array.from(addedToCart || new Set())));
    } catch (e) {
        console.warn('Unable to save cart to localStorage:', e);
    }
}
// ---------- END: Persist cart helper ----------

// Global variables
let currentPage = 1;
let currentViewMode = "grid";
let selectedVehicle = {
year: null,
make: null,
model: null,
version: null
};

// Cart functionality
let cartItems = [];
let addedToCart = new Set();

// Selection tracking for popups
let selectedMakes = [];
let selectedBrands = [];
let selectedCities = [];

// Initialize the page
document.addEventListener("DOMContentLoaded", () => {
renderProducts();
initializeFilters();
initializeEventListeners();
initializeVehicleSelector();
initializeSelectionModals();
});

// Initialize selection modals
function initializeSelectionModals() {
// Create modal HTML for Make
// createSelectionModal('make', 'Select Make', makeData);

// Create modal HTML for Brand
// createSelectionModal('brand', 'Select Brand', brandData);

// Create modal HTML for City
// createSelectionModal('city', 'Select City', cityData);

// Add event listeners for "more choices..." links
const moreLinks = document.querySelectorAll('.pw-more-link');
moreLinks.forEach(link => {
const text = link.textContent.toLowerCase();
if (text.includes('more choices')) {
const filterSection = link.closest('.pw-filter-section');
const filterTitle = filterSection.querySelector('.pw-filter-title').textContent.toLowerCase();

if (filterTitle.includes('make')) {
link.addEventListener('click', (e) => {
e.preventDefault();
openSelectionModal('make');
});
} else if (filterTitle.includes('city')) {
link.addEventListener('click', (e) => {
e.preventDefault();
openSelectionModal('city');
});
}
}
});
}

// Create selection modal HTML
function createSelectionModal(type, title, data) {
const modalId = `${type}SelectionModal`;

// Split data into two columns
const midpoint = Math.ceil(data.length / 2);
const column1 = data.slice(0, midpoint);
const column2 = data.slice(midpoint);

const modalHTML = `
    <div class="pw-selection-modal" id="${modalId}">
      <div class="pw-selection-modal-content">
        <div class="pw-selection-modal-header">
          <h3 class="pw-selection-modal-title">${title}</h3>
          <button class="pw-selection-modal-close" onclick="closeSelectionModal('${type}')">×</button>
        </div>
        <div class="pw-selection-modal-body">
          <div class="pw-selection-column">
            <ul class="pw-selection-list">
              ${column1.map(item => `
                <li class="pw-selection-item" onclick="toggleSelection('${type}', '${item.name}', this)">
                  <input type="checkbox" class="pw-selection-checkbox" id="${type}_${item.name.replace(/\s+/g, '_')}">
                  <label for="${type}_${item.name.replace(/\s+/g, '_')}" class="pw-selection-label">${item.name}</label>
                  <span class="pw-selection-count">${item.count}</span>
                </li>
              `).join('')}
            </ul>
          </div>
          <div class="pw-selection-column">
            <ul class="pw-selection-list">
              ${column2.map(item => `
                <li class="pw-selection-item" onclick="toggleSelection('${type}', '${item.name}', this)">
                  <input type="checkbox" class="pw-selection-checkbox" id="${type}_${item.name.replace(/\s+/g, '_')}">
                  <label for="${type}_${item.name.replace(/\s+/g, '_')}" class="pw-selection-label">${item.name}</label>
                  <span class="pw-selection-count">${item.count}</span>
                </li>
              `).join('')}
            </ul>
          </div>
        </div>
        <div class="pw-selection-modal-footer">
          <button class="pw-selection-modal-btn clear" onclick="clearSelection('${type}')">Clear</button>
          <button class="pw-selection-modal-btn submit" onclick="submitSelection('${type}')">Submit</button>
        </div>
      </div>
    </div>
  `;
document.body.insertAdjacentHTML('beforeend', modalHTML);

// Add click outside to close
document.getElementById(modalId).addEventListener('click', (e) => {
if (e.target.id === modalId) {
closeSelectionModal(type);
}
});
}

// Open selection modal
function openSelectionModal(type) {
const modal = document.getElementById(`${type}SelectionModal`);
modal.classList.add('show');

// Restore previous selections
const selectedArray = type === 'make' ? selectedMakes :
type === 'brand' ? selectedBrands : selectedCities;

selectedArray.forEach(selection => {
const checkbox = document.getElementById(`${type}_${selection.replace(/\s+/g, '_')}`);
if (checkbox) {
checkbox.checked = true;
}
});
}

// Close selection modal
function closeSelectionModal(type) {
const modal = document.getElementById(`${type}SelectionModal`);
modal.classList.remove('show');
}

// Toggle selection
function toggleSelection(type, name, element) {
const checkbox = element.querySelector('.pw-selection-checkbox');
checkbox.checked = !checkbox.checked;

const selectedArray = type === 'make' ? selectedMakes :
type === 'brand' ? selectedBrands : selectedCities;

if (checkbox.checked) {
if (!selectedArray.includes(name)) {
selectedArray.push(name);
}
} else {
const index = selectedArray.indexOf(name);
if (index > -1) {
selectedArray.splice(index, 1);
}
}
}

// Clear selection
function clearSelection(type) {
const modal = document.getElementById(`${type}SelectionModal`);
const checkboxes = modal.querySelectorAll('.pw-selection-checkbox');

checkboxes.forEach(checkbox => {
checkbox.checked = false;
});

// Clear the corresponding array
if (type === 'make') selectedMakes = [];
else if (type === 'brand') selectedBrands = [];
else if (type === 'city') selectedCities = [];
}

// Submit selection
function submitSelection(type) {
const selectedArray = type === 'make' ? selectedMakes :
type === 'brand' ? selectedBrands : selectedCities;

console.log(`${type} selections:`, selectedArray);

// Apply filters here
renderProducts();

// Show success message
if (selectedArray.length > 0) {
alert(`${selectedArray.length} ${type}(s) selected: ${selectedArray.join(', ')}`);
}

closeSelectionModal(type);
}

// Create brand modal (for when brand filter is added)
function initializeBrandModal() {
// Add brand filter section if it doesn't exist
const makeFilterElement = document.querySelector('[id="content-make"]');
if (!makeFilterElement) {
console.log("Make filter element not found, skipping brand modal initialization");
return;
}
const makeFilter = makeFilterElement.closest('.pw-filter-section');
const brandFilterHTML = `
    <div class="pw-filter-section">
      <div class="pw-filter-header" onclick="toggleFilter('brand')">
        <span class="pw-filter-title">BRAND</span>
        <span class="pw-filter-arrow" id="arrow-brand">▼</span>
      </div>
      <div class="pw-filter-content pw-filter-open" id="content-brand">
        <label class="pw-checkbox-item">
          <div class="pw-checkbox-wrapper">
            <input type="checkbox" class="pw-checkbox" />
            <span class="pw-checkbox-label">Denso</span>
          </div>
          <span class="pw-checkbox-count">942</span>
        </label>
        <label class="pw-checkbox-item">
          <div class="pw-checkbox-wrapper">
            <input type="checkbox" class="pw-checkbox" />
            <span class="pw-checkbox-label">MK</span>
          </div>
          <span class="pw-checkbox-count">748</span>
        </label>
        <label class="pw-checkbox-item">
          <div class="pw-checkbox-wrapper">
            <input type="checkbox" class="pw-checkbox" />
            <span class="pw-checkbox-label">MK Japan</span>
          </div>
          <span class="pw-checkbox-count">737</span>
        </label>
        <label class="pw-checkbox-item">
          <div class="pw-checkbox-wrapper">
            <input type="checkbox" class="pw-checkbox" />
            <span class="pw-checkbox-label">Asuki</span>
          </div>
          <span class="pw-checkbox-count">703</span>
        </label>
        <label class="pw-checkbox-item">
          <div class="pw-checkbox-wrapper">
            <input type="checkbox" class="pw-checkbox" />
            <span class="pw-checkbox-label">Vic</span>
          </div>
          <span class="pw-checkbox-count">692</span>
        </label>
        <a href="#" class="pw-more-link" onclick="openSelectionModal('brand')">more choices...</a>
      </div>
    </div>
  `;

makeFilter.insertAdjacentHTML('afterend', brandFilterHTML);
}

// Initialize vehicle selector
function initializeVehicleSelector() {
const vehicleBtn = document.querySelector('.pw-vehicle-btn');
const vehicleSelector = document.querySelector('.pw-vehicle-selector');

// Check if required elements exist
if (!vehicleBtn || !vehicleSelector) {
console.log("Vehicle selector elements not found, skipping initialization");
return;
}

// Create dropdown HTML
const dropdownHTML = `
    <div class="pw-vehicle-dropdown" id="vehicleDropdown">
      <div class="pw-dropdown-header">
        <div class="pw-dropdown-title">Select a Vehicle:</div>
        <a href="#" class="pw-manage-garage">Manage Your Garage</a>
      </div>
      <div class="pw-dropdown-subtitle">Add a vehicle and check if these parts fit</div>
      <div class="pw-dropdown-divider"></div>
      <button class="pw-add-vehicle-btn" onclick="openVehicleModal()">+ Add Vehicle</button>
    </div>
  `;

vehicleSelector.insertAdjacentHTML('beforeend', dropdownHTML);

// Add hover events
vehicleBtn.addEventListener('mouseenter', showVehicleDropdown);
vehicleSelector.addEventListener('mouseleave', hideVehicleDropdown);

// Create modal HTML
const modalHTML = `
    <div class="pw-vehicle-modal" id="vehicleModal">
      <div class="pw-modal-content">
        <div class="pw-modal-header">
          <div class="pw-modal-steps">
            <div class="pw-modal-step active" data-step="year">MODEL YEAR</div>
            <div class="pw-modal-step" data-step="make">MAKE</div>
            <div class="pw-modal-step" data-step="model">MODEL</div>
            <div class="pw-modal-step" data-step="version">VERSION <span style="font-size: 10px;">(OPTIONAL)</span></div>
          </div>
          <button class="pw-modal-close" onclick="closeVehicleModal()">×</button>
        </div>
        <div class="pw-modal-body">
          <div class="pw-selection-column">
            <div class="pw-column-title">MODEL YEAR</div>
            <ul class="pw-option-list" id="yearList">
              ${generateYearOptions()}
            </ul>
          </div>
          <div class="pw-selection-column">
            <div class="pw-column-title">MAKE</div>
            <div id="makeList"></div>
          </div>
          <div class="pw-selection-column">
            <div class="pw-column-title">MODEL</div>
            <ul class="pw-option-list" id="modelList"></ul>
          </div>
          <div class="pw-selection-column">
            <div class="pw-column-title">VERSION (OPTIONAL)</div>
            <ul class="pw-option-list" id="versionList"></ul>
          </div>
        </div>
        <div class="pw-modal-footer">
          <button class="pw-done-btn" onclick="saveVehicleSelection()" disabled>Done</button>
        </div>
      </div>
    </div>
  `;

document.body.insertAdjacentHTML('beforeend', modalHTML);

// Add event listeners
initializeModalEvents();
}

// Generate year options
function generateYearOptions() {
let yearHTML = '';
for (let year = 2025; year >= 1940; year--) {
yearHTML += `<li class="pw-option-item" data-year="${year}" onclick="selectYear(${year})">${year}</li>`;
}
return yearHTML;
}

// Show vehicle dropdown
function showVehicleDropdown() {
const dropdown = document.getElementById('vehicleDropdown');
dropdown.classList.add('show');
}

// Hide vehicle dropdown
function hideVehicleDropdown() {
const dropdown = document.getElementById('vehicleDropdown');
dropdown.classList.remove('show');
}

// Open vehicle modal
function openVehicleModal() {
const modal = document.getElementById('vehicleModal');
modal.classList.add('show');
hideVehicleDropdown();
resetVehicleSelection();
}

// Close vehicle modal
function closeVehicleModal() {
const modal = document.getElementById('vehicleModal');
modal.classList.remove('show');
}

// Reset vehicle selection
function resetVehicleSelection() {
selectedVehicle = { year: null, make: null, model: null, version: null };
updateSteps();
clearSelections();
updateDoneButton();
}

// Select year
function selectYear(year) {
selectedVehicle.year = year;

// Update UI
document.querySelectorAll('#yearList .pw-option-item').forEach(item => {
item.classList.remove('selected');
});
document.querySelector(`#yearList [data-year="${year}"]`).classList.add('selected');

// Populate makes
populateMakes();
updateSteps();
updateDoneButton();
}

// Populate makes
function populateMakes() {
const makeList = document.getElementById('makeList');

let makeHTML = '';

// Popular makes
makeHTML += '<div class="pw-option-group">';
makeHTML += '<div class="pw-group-title">Popular</div>';
vehicleData.makes.popular.forEach(make => {
makeHTML += `
      <div class="pw-option-item" onclick="selectMake('${make.name}')">
        <img src="${make.logo}" alt="${make.name}" class="pw-brand-logo" onerror="this.src='https://via.placeholder.com/24x24/333/fff?text=${make.name.charAt(0)}'">
        ${make.name}
      </div>
    `;
});
makeHTML += '</div>';

// Others
makeHTML += '<div class="pw-option-group">';
makeHTML += '<div class="pw-group-title">Others</div>';
vehicleData.makes.others.forEach(make => {
makeHTML += `
      <div class="pw-option-item" onclick="selectMake('${make.name}')">
        <img src="${make.logo}" alt="${make.name}" class="pw-brand-logo" onerror="this.src='https://via.placeholder.com/24x24/333/fff?text=${make.name.charAt(0)}'">
        ${make.name}
      </div>
    `;
});
makeHTML += '</div>';

makeList.innerHTML = makeHTML;
}

// Select make
function selectMake(make) {
selectedVehicle.make = make;

// Update UI
document.querySelectorAll('#makeList .pw-option-item').forEach(item => {
item.classList.remove('selected');
});
event.target.classList.add('selected');

// Populate models
populateModels(make);
updateSteps();
updateDoneButton();
}

// Populate models
function populateModels(make) {
const modelList = document.getElementById('modelList');
const models = vehicleData.models[make] || [];

let modelHTML = '';

if (models.length > 0) {
// Popular models (first few)
if (models.length > 5) {
modelHTML += '<div class="pw-option-group">';
modelHTML += '<div class="pw-group-title">Popular</div>';
models.slice(0, 5).forEach(model => {
modelHTML += `<li class="pw-option-item" onclick="selectModel('${model}')">${model}</li>`;
});
modelHTML += '</div>';

// Others
modelHTML += '<div class="pw-option-group">';
modelHTML += '<div class="pw-group-title">Others</div>';
models.slice(5).forEach(model => {
modelHTML += `<li class="pw-option-item" onclick="selectModel('${model}')">${model}</li>`;
});
modelHTML += '</div>';
} else {
models.forEach(model => {
modelHTML += `<li class="pw-option-item" onclick="selectModel('${model}')">${model}</li>`;
});
}
}

modelList.innerHTML = modelHTML;
}

// Select model
function selectModel(model) {
selectedVehicle.model = model;

// Update UI
document.querySelectorAll('#modelList .pw-option-item').forEach(item => {
item.classList.remove('selected');
});
event.target.classList.add('selected');

// Populate versions
populateVersions(selectedVehicle.make, model);
updateSteps();
updateDoneButton();
}

// Populate versions
function populateVersions(make, model) {
const versionList = document.getElementById('versionList');
const versionKey = `${make}-${model}`;
const versions = vehicleData.versions[versionKey] || [];

let versionHTML = '';

if (versions.length > 0) {
versionHTML += '<li class="pw-option-item" onclick="selectVersion(\'All Variants\')">All Variants</li>';
versions.forEach(version => {
versionHTML += `<li class="pw-option-item" onclick="selectVersion('${version}')">${version}</li>`;
});
} else {
versionHTML += '<li class="pw-option-item" onclick="selectVersion(\'All Variants\')">All Variants</li>';
}

versionList.innerHTML = versionHTML;
}

// Select version
function selectVersion(version) {
selectedVehicle.version = version;

// Update UI
document.querySelectorAll('#versionList .pw-option-item').forEach(item => {
item.classList.remove('selected');
});
event.target.classList.add('selected');

updateSteps();
updateDoneButton();
}

// Update steps
function updateSteps() {
const steps = document.querySelectorAll('.pw-modal-step');

steps.forEach((step, index) => {
step.classList.remove('active', 'completed');

if (index === 0 && selectedVehicle.year) {
step.classList.add('completed');
} else if (index === 1 && selectedVehicle.make) {
step.classList.add('completed');
} else if (index === 2 && selectedVehicle.model) {
step.classList.add('completed');
} else if (index === 3 && selectedVehicle.version) {
step.classList.add('completed');
}
});

// Set active step
if (!selectedVehicle.year) {
steps[0].classList.add('active');
} else if (!selectedVehicle.make) {
steps[1].classList.add('active');
} else if (!selectedVehicle.model) {
steps[2].classList.add('active');
} else {
steps[3].classList.add('active');
}
}

// Update done button
function updateDoneButton() {
const doneBtn = document.querySelector('.pw-done-btn');
const canSave = selectedVehicle.year && selectedVehicle.make && selectedVehicle.model;

doneBtn.disabled = !canSave;
}

// Clear selections
function clearSelections() {
document.querySelectorAll('.pw-option-item').forEach(item => {
item.classList.remove('selected');
});

document.getElementById('makeList').innerHTML = '';
document.getElementById('modelList').innerHTML = '';
document.getElementById('versionList').innerHTML = '';
}

// Save vehicle selection
function saveVehicleSelection() {
if (selectedVehicle.year && selectedVehicle.make && selectedVehicle.model) {
const vehicleText = `${selectedVehicle.year} ${selectedVehicle.make} ${selectedVehicle.model}${selectedVehicle.version ? ' ' + selectedVehicle.version : ''}`;

// Update button text
const vehicleBtn = document.querySelector('.pw-vehicle-btn');
vehicleBtn.innerHTML = `${vehicleText} <span class="pw-vehicle-arrow"><i class="ri-arrow-down-s-line"></i></span>`;

// Close modal
closeVehicleModal();

console.log('Vehicle selected:', selectedVehicle);
alert(`Vehicle selected: ${vehicleText}`);
}
}

// Initialize modal events
function initializeModalEvents() {
// Close modal when clicking outside
document.getElementById('vehicleModal').addEventListener('click', (e) => {
if (e.target.id === 'vehicleModal') {
closeVehicleModal();
}
});

// Prevent modal close when clicking inside content
document.querySelector('.pw-modal-content').addEventListener('click', (e) => {
e.stopPropagation();
});
}

// Initialize event listeners
function initializeEventListeners() {
// Sort dropdown
const sortSelect = document.getElementById("sortSelect");
if (sortSelect) {
sortSelect.addEventListener("change", (e) => {
const sortValue = e.target.value;
console.log("Sort by:", sortValue);
// Add sorting logic here
renderProducts();
});
}

// Search functionality
const searchInputs = document.querySelectorAll('.pw-search-input');
searchInputs.forEach(input => {
input.addEventListener('keypress', (e) => {
if (e.key === 'Enter') {
handleSearch(e.target.value);
}
});
});

const searchBtns = document.querySelectorAll('.pw-search-btn');
searchBtns.forEach(btn => {
btn.addEventListener('click', (e) => {
const input = e.target.previousElementSibling;
handleSearch(input.value);
});
});


// ---------- BEGIN: Delegated click handlers for add/buy ----------
document.addEventListener('click', function(e) {
    // Add to Cart (delegated)
    const addBtn = e.target.closest('.pw-add-to-cart-button');
    if (addBtn) {
        e.preventDefault();
        const partId = parseInt(addBtn.getAttribute('data-part-id'));
        // If there's a quantity input on the page, use it; otherwise default to 1
        const quantityInput = document.getElementById('pw-quantity-input');
        const qty = quantityInput ? parseInt(quantityInput.value) : 1;
        addToCart(partId, qty);
        return;
    }

    // Buy Now (delegated)
    const buyBtn = e.target.closest('.pw-buy-now-button');
    if (buyBtn) {
        e.preventDefault();
        const partId = parseInt(buyBtn.getAttribute('data-part-id'));
        buyNow(partId);
        return;
    }
});
// ---------- END: Delegated click handlers for add/buy ----------

// Report ad buttons
const reportBtns = document.querySelectorAll('.pw-report-ad-button');
reportBtns.forEach(btn => {
btn.addEventListener('click', (e) => {
const partId = parseInt(btn.getAttribute('data-part-id'));
reportAd(partId);
});
});
}

// Handle search functionality
function handleSearch(searchTerm) {
console.log("Searching for:", searchTerm);
// Add search logic here
renderProducts();
}

// Toggle filter sections
function toggleFilter(filterId) {
const content = document.getElementById(`content-${filterId}`);
const arrow = document.getElementById(`arrow-${filterId}`);

if (content.classList.contains("pw-filter-open")) {
content.classList.remove("pw-filter-open");
arrow.textContent = "▶";
} else {
content.classList.add("pw-filter-open");
arrow.textContent = "▼";
}
}

// Set view mode
function setViewMode(mode) {
currentViewMode = mode;
const listBtn = document.getElementById("listBtn");
const gridBtn = document.getElementById("gridBtn");

if (mode === "list") {
listBtn.classList.add("pw-view-active");
gridBtn.classList.remove("pw-view-active");
} else {
gridBtn.classList.add("pw-view-active");
listBtn.classList.remove("pw-view-active");
}

renderProducts();
}

// Set page
function setPage(page) {
currentPage = page;

// Update pagination buttons
const pageButtons = document.querySelectorAll(".pw-page-btn");
pageButtons.forEach((btn) => {
btn.classList.remove("pw-page-active");
if (parseInt(btn.textContent) === page) {
btn.classList.add("pw-page-active");
}
});

renderProducts();
}

// Render stars
function renderStars(rating) {
let starsHtml = "";
const fullStars = Math.floor(rating);
const hasHalfStar = rating % 1 !== 0;

for (let i = 0; i < 5; i++) {
if (i < fullStars) {
starsHtml += '<span class="pw-star filled">★</span>';
} else if (i === fullStars && hasHalfStar) {
starsHtml += '<span class="pw-star filled">★</span>';
} else {
starsHtml += '<span class="pw-star empty">★</span>';
}
}

return starsHtml;
}

// Render products with cart functionality
function renderProducts() {
const productsGrid = document.getElementById("productsGrid");
if (!productsGrid) {
    return; // Exit if the element doesn't exist on this page
}
let productsHtml = "";

products.forEach((product) => {
const isInCart = addedToCart.has(product.id);

productsHtml += `
            <div class="pw-product-card">
                ${product.onSale ? '<div class="pw-sale-badge">SALE<br>OFF</div>' : ""}
                <img src="${product.image}" alt="${product.title}" class="pw-product-image" loading="lazy">
                <div class="pw-product-info">
                    <a href="${product.link}" target="_blank" class="pw-product-title">${product.title}</a>
                    <div class="pw-product-category">${product.category}</div>
                    ${
                      product.rating
                        ? `
                          <div class="pw-product-rating">
                            ${renderStars(product.rating)}
                            <span class="pw-rating-count">(${product.reviews})</span>
                          </div>
                        `
                        : ""
                    }
                    <div class="pw-product-location">${product.location}</div>
                    <div class="pw-product-price">
                        ${product.price}
                        ${product.originalPrice ? `<span class="pw-original-price">${product.originalPrice}</span>` : ""}
                    </div>
                    <div class="pw-product-actions">
                        ${isInCart ? 
                          `<button class="pw-btn-primary" onclick="viewCart()">View Cart</button>` :
                          `
                          <button class="pw-btn-primary" onclick="buyNow(${product.id})">Buy Now</button>
                          <button class="pw-btn-secondary" onclick="addToCart(${product.id})">Add To Cart</button>
                          `
                        }
                    </div>
                </div>
            </div>
        `;
});
productsGrid.innerHTML = productsHtml;
}

// Initialize filters (set default open states)
function initializeFilters() {
// Set default open filters
const defaultOpenFilters = [
"sale",
"shop-now",
"free-shipping",
"category",
"price-range",
"make",
"city",
"picture-availability",
];

defaultOpenFilters.forEach((filterId) => {
const content = document.getElementById(`content-${filterId}`);
const arrow = document.getElementById(`arrow-${filterId}`);
if (content && arrow) {
content.classList.add("pw-filter-open");
arrow.textContent = "▼";
}
});

// Initialize brand modal after a short delay
setTimeout(() => {
initializeBrandModal();
}, 100);
}

// Product actions
// CSRF Token utility function
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Show toast notification
function showToast(message, type = 'success') {
    // Create toast element if it doesn't exist
    let toast = document.getElementById('cart-toast');
    if (!toast) {
        toast = document.createElement('div');
        toast.id = 'cart-toast';
        toast.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 15px 20px;
            border-radius: 5px;
            color: white;
            font-weight: bold;
            z-index: 10000;
            opacity: 0;
            transition: opacity 0.3s ease;
        `;
        document.body.appendChild(toast);
    }
    
    // Set toast style based on type
    toast.style.backgroundColor = type === 'success' ? '#28a745' : '#dc3545';
    toast.textContent = message;
    toast.style.opacity = '1';
    
    // Hide toast after 3 seconds
    setTimeout(() => {
        toast.style.opacity = '0';
    }, 3000);
}

// Update cart count in DOM
function updateCartCount(count) {
    const cartCountElements = document.querySelectorAll('.cart-count, [data-cart-count]');
    cartCountElements.forEach(element => {
        element.textContent = count;
    });
}

// ---------- BEGIN: Robust buyNow ----------
function buyNow(productId) {
    console.log(`Buy Now clicked for product ID: ${productId}`);

    // Get CSRF token
    const csrfToken = getCookie('csrftoken');
    if (!csrfToken) {
        showToast('Security token missing. Please refresh the page.', 'error');
        return;
    }

    // Determine quantity:
    //  - If there's a page-level quantity input with id pw-quantity-input (detail page), use it.
    //  - Else fallback to 1.
    let quantity = 1;
    const pageQuantityInput = document.getElementById('pw-quantity-input');
    if (pageQuantityInput) {
        quantity = parseInt(pageQuantityInput.value) || 1;
    } else {
        // also check for an input inside a card that may have a data attribute (if you later add it)
        const cardQuantityInput = document.querySelector(`input[data-part-id="${productId}"]`);
        if (cardQuantityInput) {
            quantity = parseInt(cardQuantityInput.value) || 1;
        }
    }

    // Prepare request data
    const requestData = {
        part_id: productId,
        qty: quantity,
        return_url: window.location.href
    };

    // Loading UI
    const buyButton = document.querySelector(`[data-part-id="${productId}"].pw-buy-now-button`);
    const originalText = buyButton ? buyButton.innerHTML : '';
    if (buyButton) {
        buyButton.disabled = true;
        buyButton.innerHTML = 'Processing...';
    }

    fetch('/parts/buy-now/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken,
            'X-Requested-With': 'XMLHttpRequest'
        },
        body: JSON.stringify(requestData)
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(data => {
                throw new Error(data.error || 'Failed to create order');
            });
        }
        return response.json();
    })
    .then(data => {
        if (data.success && data.checkout_url) {
            showToast(data.message || 'Redirecting to checkout...', 'success');

            // Optionally add the item to client-side cart as well for consistency
            cartItems.push({ productId, qty: quantity });
            addedToCart.add(productId);
            saveCartToLocalStorage();

            // Redirect to checkout (server returns checkout_url)
            window.location.href = data.checkout_url;
        } else {
            throw new Error(data.error || 'Failed to create order');
        }
    })
    .catch(error => {
        console.error('Error creating order:', error);
        showToast(error.message || 'Failed to create order. Please try again.', 'error');
    })
    .finally(() => {
        if (buyButton) {
            buyButton.disabled = false;
            buyButton.innerHTML = originalText;
        }
    });
}
// ---------- END: Robust buyNow ----------


// ---------- BEGIN: Improved addToCart ----------
function addToCart(productId, quantity = 1, redirectAfter = false) {
    console.log(`Adding to cart: Product ID ${productId}, Quantity: ${quantity}`);

    // Get CSRF token
    const csrfToken = getCookie('csrftoken');
    if (!csrfToken) {
        showToast('Security token missing. Please refresh the page.', 'error');
        return;
    }

    // Prepare request data
    const requestData = {
        qty: quantity
    };

    // Optional: disable the button that triggered this action if available
    const triggerBtn = document.querySelector(`[data-part-id="${productId}"].pw-add-to-cart-button`);
    const originalBtnText = triggerBtn ? triggerBtn.textContent : null;
    if (triggerBtn) {
        triggerBtn.disabled = true;
        triggerBtn.textContent = 'Adding...';
    }

    fetch(`/parts/cart/add/${productId}/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken,
            'X-Requested-With': 'XMLHttpRequest'
        },
        body: JSON.stringify(requestData)
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(data => {
                throw new Error(data.error || 'Failed to add item to cart');
            });
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            showToast(data.message || 'Added to cart', 'success');

            // Update client-side cart state
            cartItems.push({ productId, qty: quantity });
            addedToCart.add(productId);

            // Save to localStorage so reloads persist
            saveCartToLocalStorage();

            // Update visible cart counters
            if (typeof data.cart_count !== 'undefined') {
                updateCartCount(data.cart_count);
            } else {
                // fallback increment if backend doesn't return count
                const currentCountEl = document.querySelector('[data-cart-count]');
                if (currentCountEl) {
                    const newCount = (parseInt(currentCountEl.textContent || '0') || 0) + 1;
                    updateCartCount(newCount);
                }
            }

            // Re-render UI where appropriate
            try { renderProducts(); } catch (e) {}

            // Redirect to cart if needed
            if (redirectAfter) {
                viewCart();
            }
        } else {
            showToast(data.error || 'Failed to add item to cart', 'error');
        }
    })
    .catch(error => {
        console.error('Error adding to cart:', error);
        showToast(error.message || 'Failed to add item to cart', 'error');
    })
    .finally(() => {
        if (triggerBtn) {
            triggerBtn.disabled = false;
            triggerBtn.textContent = originalBtnText;
        }
    });
}
// ---------- END: Improved addToCart ----------


function viewCart() {
    // Redirect to cart page
    window.location.href = '/parts/cart/';
}

// Filter functionality
document.addEventListener('change', (e) => {
if (e.target.type === 'checkbox') {
console.log(`Filter changed: ${e.target.closest('.pw-checkbox-item').textContent.trim()}`);
// Add filter logic here
renderProducts();
}
});

// Price range functionality
document.addEventListener('click', (e) => {
if (e.target.classList.contains('pw-price-btn')) {
const priceInputs = e.target.parentElement.querySelectorAll('.pw-price-input');
const fromPrice = priceInputs[0].value;
const toPrice = priceInputs[1].value;
console.log(`Price range: ${fromPrice} - ${toPrice}`);
// Add price filter logic here
renderProducts();
}
});

// Load cart items on page load
document.addEventListener('DOMContentLoaded', () => {
// Load cart from localStorage
const savedCartItems = localStorage.getItem('cartItems');
const savedAddedToCart = localStorage.getItem('addedToCart');

if (savedCartItems) {
cartItems = JSON.parse(savedCartItems);
}
if (savedAddedToCart) {
addedToCart = new Set(JSON.parse(savedAddedToCart));
}
});

// Vendor contact functionality
function contactVendor(type, contact) {
    switch(type) {
        case 'phone':
            if (contact) {
                window.location.href = `tel:${contact}`;
            } else {
                showToast('Phone number not available', 'error');
            }
            break;
        case 'email':
            if (contact) {
                window.location.href = `mailto:${contact}`;
            } else {
                showToast('Email not available', 'error');
            }
            break;
        default:
            console.log(`Contact vendor via ${type}`);
    }
}

// Legacy contactSeller function for backward compatibility
function contactSeller(type) {
    console.log(`Contact seller via ${type}`);
    showToast('Contact information not available', 'info');
}
