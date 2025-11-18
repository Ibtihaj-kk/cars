/**
 * Modern Vendor Registration JavaScript
 * Comprehensive validation and interactivity for vendor registration forms
 */

class VendorRegistrationManager {
    constructor() {
        this.currentStep = 1;
        this.validationRules = this.initializeValidationRules();
        this.countrySpecificRules = this.initializeCountryRules();
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.initializeFormValidation();
        this.setupCountrySpecificValidation();
        this.setupAccessibilityFeatures();
        this.setupProgressiveEnhancement();
        this.restoreFormData();
    }

    initializeValidationRules() {
        return {
            // Business Details (Step 1)
            company_name: {
                required: true,
                minLength: 2,
                maxLength: 100,
                pattern: /^[a-zA-Z0-9\s\&\-\.\,\(\)]+$/,
                message: 'Please enter a valid company name (2-100 characters)'
            },
            business_type: {
                required: true,
                message: 'Please select your business type'
            },
            commercial_registration_number: {
                required: true,
                pattern: /^[A-Z0-9\-]+$/,
                minLength: 5,
                maxLength: 50,
                message: 'Please enter a valid registration number'
            },
            legal_identifier: {
                required: true,
                pattern: /^[A-Z0-9\-]+$/,
                minLength: 5,
                maxLength: 50,
                message: 'Please enter a valid legal identifier'
            },
            
            // Contact Information (Step 2)
            contact_person_name: {
                required: true,
                minLength: 2,
                maxLength: 50,
                pattern: /^[a-zA-Z\s\-\.]+$/,
                message: 'Please enter a valid contact person name'
            },
            contact_person_title: {
                required: false,
                maxLength: 50,
                message: 'Job title must be less than 50 characters'
            },
            business_phone: {
                required: true,
                validate: this.validatePhoneNumber,
                message: 'Please enter a valid business phone number'
            },
            business_email: {
                required: true,
                pattern: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
                message: 'Please enter a valid business email address'
            },
            
            // Address Fields
            street_address: {
                required: true,
                minLength: 5,
                maxLength: 200,
                message: 'Please enter a valid street address'
            },
            city: {
                required: true,
                minLength: 2,
                maxLength: 50,
                pattern: /^[a-zA-Z\s\-\.]+$/,
                message: 'Please enter a valid city name'
            },
            state_province: {
                required: true,
                minLength: 2,
                maxLength: 50,
                message: 'Please enter a valid state or province'
            },
            postal_code: {
                required: true,
                validate: this.validatePostalCode,
                message: 'Please enter a valid postal code'
            },
            country: {
                required: true,
                message: 'Please select your country'
            },
            
            // Bank Details (Step 3)
            bank_name: {
                required: true,
                minLength: 2,
                maxLength: 100,
                message: 'Please enter a valid bank name'
            },
            account_holder_name: {
                required: true,
                minLength: 2,
                maxLength: 100,
                pattern: /^[a-zA-Z\s\-\.]+$/,
                message: 'Please enter the account holder name'
            },
            account_number: {
                required: true,
                pattern: /^[0-9A-Z\-]+$/,
                minLength: 8,
                maxLength: 34,
                message: 'Please enter a valid account number'
            },
            iban: {
                required: true,
                validate: this.validateIBAN,
                message: 'Please enter a valid IBAN'
            },
            swift_bic: {
                required: true,
                pattern: /^[A-Z]{6}[A-Z0-9]{2}([A-Z0-9]{3})?$/,
                message: 'Please enter a valid SWIFT/BIC code'
            },
            
            // Additional Information (Step 4)
            expected_monthly_volume: {
                required: true,
                min: 100,
                max: 10000000,
                message: 'Please enter a valid monthly volume (100-10,000,000)'
            },
            years_in_business: {
                required: true,
                min: 0,
                max: 200,
                message: 'Please enter valid years in business'
            },
            product_categories: {
                required: true,
                message: 'Please select at least one product category'
            },
            business_references: {
                required: true,
                minLength: 20,
                maxLength: 1000,
                message: 'Please provide 2-3 business references (20-1000 characters)'
            }
        };
    }

    initializeCountryRules() {
        return {
            'PK': { // Pakistan
                phonePattern: /^\+92[0-9]{10}$/,
                postalPattern: /^[0-9]{5}$/,
                taxPattern: /^[0-9]{7}-[0-9]{1}$/,
                ibanLength: 24,
                phoneExample: '+923001234567',
                postalExample: '12345',
                taxExample: '1234567-8'
            },
            'SA': { // Saudi Arabia
                phonePattern: /^\+966[0-9]{9}$/,
                postalPattern: /^[0-9]{5}$/,
                taxPattern: /^[0-9]{15}$/,
                ibanLength: 24,
                phoneExample: '+966501234567',
                postalExample: '12345',
                taxExample: '123456789012345'
            },
            'AE': { // UAE
                phonePattern: /^\+971[0-9]{9}$/,
                postalPattern: /^[0-9]{5}$/,
                taxPattern: /^[0-9]{15}$/,
                ibanLength: 23,
                phoneExample: '+971501234567',
                postalExample: '12345',
                taxExample: '123456789012345'
            },
            'US': { // United States
                phonePattern: /^\+1[0-9]{10}$/,
                postalPattern: /^[0-9]{5}(-[0-9]{4})?$/,
                taxPattern: /^[0-9]{2}-[0-9]{7}$/,
                ibanLength: null, // US doesn't use IBAN
                phoneExample: '+12025551234',
                postalExample: '12345 or 12345-6789',
                taxExample: '12-3456789'
            },
            'GB': { // United Kingdom
                phonePattern: /^\+44[0-9]{10}$/,
                postalPattern: /^[A-Z]{1,2}[0-9][A-Z0-9]? [0-9][A-Z]{2}$/,
                taxPattern: /^[0-9]{9}$/,
                ibanLength: 22,
                phoneExample: '+447712345678',
                postalExample: 'SW1A 1AA',
                taxExample: '123456789'
            },
            'CA': { // Canada
                phonePattern: /^\+1[0-9]{10}$/,
                postalPattern: /^[A-Z][0-9][A-Z] [0-9][A-Z][0-9]$/,
                taxPattern: /^[0-9]{9}$/,
                ibanLength: null, // Canada doesn't use IBAN
                phoneExample: '+14165551234',
                postalExample: 'K1A 0A6',
                taxExample: '123456789'
            }
        };
    }

    setupEventListeners() {
        // Real-time validation
        document.addEventListener('input', (e) => {
            if (e.target.matches('.form-control-modern')) {
                this.validateField(e.target);
            }
        });

        // Country change handler
        document.addEventListener('change', (e) => {
            if (e.target.matches('#id_country')) {
                this.updateCountrySpecificFields(e.target.value);
            }
        });

        // Form submission
        document.addEventListener('submit', (e) => {
            if (e.target.matches('#vendor-registration-form')) {
                console.log('Form submission event triggered');
                e.preventDefault();
                e.stopPropagation();
                console.log('Form action:', e.target.action);
                console.log('Form method:', e.target.method);
                console.log('Current URL:', window.location.href);
                
                // Check if user is logged in (required for vendor registration)
                const userLoggedIn = document.body.classList.contains('user-authenticated') || 
                                   document.querySelector('[data-user-authenticated="true"]') !== null;
                
                if (!userLoggedIn) {
                    console.warn('User is not logged in - redirecting to login');
                    alert('Please log in to submit your vendor registration. You will be redirected to the login page.');
                    
                    // Store current form data in sessionStorage to preserve it
                    const formData = new FormData(e.target);
                    const formDataObj = {};
                    for (let [key, value] of formData.entries()) {
                        formDataObj[key] = value;
                    }
                    sessionStorage.setItem('vendor_registration_data', JSON.stringify(formDataObj));
                    sessionStorage.setItem('vendor_registration_step', '4');
                    
                    // Redirect to login page with return URL
                    const currentPath = window.location.pathname;
                    window.location.href = `/vendor/login/?next=${encodeURIComponent(currentPath)}`;
                    return false;
                }
                
                if (this.validateForm()) {
                    console.log('Form validation passed, calling submitForm');
                    this.submitForm(e.target);
                } else {
                    console.log('Form validation failed');
                }
                return false;
            }
        });}]}

        // File upload handling
        document.addEventListener('dragover', (e) => {
            if (e.target.matches('.file-upload-area-modern')) {
                e.preventDefault();
                e.target.classList.add('dragover');
            }
        });

        document.addEventListener('dragleave', (e) => {
            if (e.target.matches('.file-upload-area-modern')) {
                e.target.classList.remove('dragover');
            }
        });

        document.addEventListener('drop', (e) => {
            if (e.target.matches('.file-upload-area-modern')) {
                e.preventDefault();
                e.target.classList.remove('dragover');
                this.handleFileDrop(e, e.target);
            }
        });
    }

    initializeFormValidation() {
        const forms = document.querySelectorAll('#vendor-registration-form');
        forms.forEach(form => {
            form.setAttribute('novalidate', 'true'); // Disable native validation
            this.addValidationIndicators(form);
        });
    }

    addValidationIndicators(form) {
        const inputs = form.querySelectorAll('.form-control-modern');
        inputs.forEach(input => {
            // Add validation icons
            const wrapper = document.createElement('div');
            wrapper.className = 'validation-wrapper';
            wrapper.style.position = 'relative';
            
            input.parentNode.insertBefore(wrapper, input);
            wrapper.appendChild(input);
            
            // Add validation icon
            const icon = document.createElement('i');
            icon.className = 'validation-icon';
            icon.style.position = 'absolute';
            icon.style.right = '12px';
            icon.style.top = '50%';
            icon.style.transform = 'translateY(-50%)';
            icon.style.display = 'none';
            icon.style.pointerEvents = 'none';
            
            wrapper.appendChild(icon);
        });
    }

    validateField(field) {
        const fieldName = field.name || field.id;
        const value = field.value.trim();
        const rule = this.validationRules[fieldName];
        
        if (!rule) return true;

        let isValid = true;
        let errorMessage = '';

        // Required validation
        if (rule.required && !value) {
            isValid = false;
            errorMessage = rule.message || 'This field is required';
        }

        // Length validation
        if (value && rule.minLength && value.length < rule.minLength) {
            isValid = false;
            errorMessage = `Minimum ${rule.minLength} characters required`;
        }

        if (value && rule.maxLength && value.length > rule.maxLength) {
            isValid = false;
            errorMessage = `Maximum ${rule.maxLength} characters allowed`;
        }

        // Pattern validation
        if (value && rule.pattern && !rule.pattern.test(value)) {
            isValid = false;
            errorMessage = rule.message || 'Please enter a valid format';
        }

        // Custom validation
        if (value && rule.validate && !rule.validate(value, field)) {
            isValid = false;
            errorMessage = rule.message || 'Please enter a valid value';
        }

        // Range validation
        if (value && rule.min !== undefined && parseFloat(value) < rule.min) {
            isValid = false;
            errorMessage = `Value must be at least ${rule.min}`;
        }

        if (value && rule.max !== undefined && parseFloat(value) > rule.max) {
            isValid = false;
            errorMessage = `Value must be at most ${rule.max}`;
        }

        this.updateFieldValidationState(field, isValid, errorMessage);
        return isValid;
    }

    updateFieldValidationState(field, isValid, errorMessage) {
        const wrapper = field.closest('.validation-wrapper') || field.parentElement;
        const icon = wrapper.querySelector('.validation-icon');
        
        // Remove previous validation classes
        field.classList.remove('is-valid', 'is-invalid');
        
        // Remove previous error message
        const existingError = wrapper.querySelector('.invalid-feedback-modern');
        if (existingError) {
            existingError.remove();
        }

        if (isValid) {
            field.classList.add('is-valid');
            if (icon) {
                icon.className = 'validation-icon fas fa-check-circle';
                icon.style.color = '#28a745';
                icon.style.display = 'block';
            }
        } else {
            field.classList.add('is-invalid');
            if (icon) {
                icon.className = 'validation-icon fas fa-exclamation-circle';
                icon.style.color = '#dc3545';
                icon.style.display = 'block';
            }
            
            // Add error message
            const errorDiv = document.createElement('div');
            errorDiv.className = 'invalid-feedback-modern';
            errorDiv.textContent = errorMessage;
            wrapper.appendChild(errorDiv);
        }
    }

    validatePhoneNumber(phone, field) {
        const country = document.querySelector('#id_country')?.value || 'PK';
        const countryRule = this.countrySpecificRules[country];
        
        if (countryRule && countryRule.phonePattern) {
            return countryRule.phonePattern.test(phone.replace(/\s/g, ''));
        }
        
        // Default phone validation
        return /^\+[1-9]\d{1,14}$/.test(phone.replace(/\s/g, ''));
    }

    validatePostalCode(code, field) {
        const country = document.querySelector('#id_country')?.value || 'PK';
        const countryRule = this.countrySpecificRules[country];
        
        if (countryRule && countryRule.postalPattern) {
            return countryRule.postalPattern.test(code.replace(/\s/g, ''));
        }
        
        // Default postal code validation
        return /^[A-Z0-9\s\-]{3,10}$/.test(code.toUpperCase());
    }

    validateIBAN(iban, field) {
        const country = document.querySelector('#id_country')?.value || 'PK';
        const countryRule = this.countrySpecificRules[country];
        
        if (countryRule && countryRule.ibanLength) {
            return iban.replace(/\s/g, '').length === countryRule.ibanLength;
        }
        
        // Default IBAN validation (basic format check)
        return /^[A-Z]{2}[0-9]{2}[A-Z0-9]{4}[0-9]{7}([A-Z0-9]?){0,16}$/.test(iban.replace(/\s/g, ''));
    }

    updateCountrySpecificFields(countryCode) {
        const countryRule = this.countrySpecificRules[countryCode];
        
        if (countryRule) {
            // Update phone placeholder
            const phoneField = document.querySelector('#id_business_phone');
            if (phoneField && countryRule.phoneExample) {
                phoneField.placeholder = `e.g., ${countryRule.phoneExample}`;
            }
            
            // Update postal code placeholder
            const postalField = document.querySelector('#id_postal_code');
            if (postalField && countryRule.postalExample) {
                postalField.placeholder = `e.g., ${countryRule.postalExample}`;
            }
            
            // Update tax/VAT field placeholder
            const taxField = document.querySelector('#id_tax_vat_number');
            if (taxField && countryRule.taxExample) {
                taxField.placeholder = `e.g., ${countryRule.taxExample}`;
            }
            
            // Update IBAN field requirements
            const ibanField = document.querySelector('#id_iban');
            if (ibanField && countryRule.ibanLength) {
                ibanField.placeholder = `IBAN (${countryRule.ibanLength} characters)`;
            }
        }
    }

    validateForm() {
        const form = document.querySelector('#vendor-registration-form');
        const inputs = form.querySelectorAll('.form-control-modern[required]');
        let isValid = true;
        
        console.log('validateForm called, found', inputs.length, 'required fields');

        inputs.forEach(input => {
            console.log('Validating field:', input.name || input.id, 'value:', input.value);
            if (!this.validateField(input)) {
                console.log('Field validation failed for:', input.name || input.id);
                isValid = false;
            }
        });
        
        console.log('validateForm returning:', isValid);

        return isValid;
    }

    setupCountrySpecificValidation() {
        const countrySelect = document.querySelector('#id_country');
        if (countrySelect) {
            this.updateCountrySpecificFields(countrySelect.value);
        }
    }

    setupAccessibilityFeatures() {
        // Add ARIA attributes
        const forms = document.querySelectorAll('#vendor-registration-form');
        forms.forEach(form => {
            form.setAttribute('role', 'form');
            form.setAttribute('aria-label', 'Vendor Registration Form');
        });

        // Add live region for validation messages
        const liveRegion = document.createElement('div');
        liveRegion.setAttribute('aria-live', 'polite');
        liveRegion.setAttribute('aria-atomic', 'true');
        liveRegion.style.position = 'absolute';
        liveRegion.style.left = '-10000px';
        liveRegion.style.width = '1px';
        liveRegion.style.height = '1px';
        liveRegion.style.overflow = 'hidden';
        document.body.appendChild(liveRegion);

        this.liveRegion = liveRegion;
    }

    setupProgressiveEnhancement() {
        // Add loading states
        const submitButtons = document.querySelectorAll('button[type="submit"]');
        submitButtons.forEach(button => {
            button.addEventListener('click', () => {
                this.setLoadingState(button, true);
            });
        });
    }
    
    restoreFormData() {
        // Restore form data if returning from login
        const savedData = sessionStorage.getItem('vendor_registration_data');
        const savedStep = sessionStorage.getItem('vendor_registration_step');
        
        if (savedData && savedStep) {
            try {
                const formData = JSON.parse(savedData);
                const form = document.querySelector('#vendor-registration-form');
                
                if (form) {
                    // Restore form field values
                    Object.keys(formData).forEach(key => {
                        const field = form.querySelector(`[name="${key}"]`);
                        if (field) {
                            if (field.type === 'checkbox' || field.type === 'radio') {
                                field.checked = formData[key] === 'on' || formData[key] === 'true';
                            } else if (field.tagName === 'SELECT' && field.hasAttribute('multiple')) {
                                // Handle multiple select
                                const values = Array.isArray(formData[key]) ? formData[key] : [formData[key]];
                                Array.from(field.options).forEach(option => {
                                    option.selected = values.includes(option.value);
                                });
                            } else {
                                field.value = formData[key];
                            }
                            
                            // Trigger change event for any dependent fields
                            field.dispatchEvent(new Event('change', { bubbles: true }));
                        }
                    });
                    
                    // Clear saved data after restoration
                    sessionStorage.removeItem('vendor_registration_data');
                    sessionStorage.removeItem('vendor_registration_step');
                    
                    console.log('Form data restored from sessionStorage');
                }
            } catch (error) {
                console.error('Error restoring form data:', error);
            }
        }
    }

    setLoadingState(button, isLoading) {
        if (isLoading) {
            button.disabled = true;
            button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';
        } else {
            button.disabled = false;
            button.innerHTML = button.getAttribute('data-original-text') || 'Submit';
        }
    }

    handleFileDrop(event, dropZone) {
        const files = event.dataTransfer.files;
        this.processFiles(files, dropZone);
    }

    processFiles(files, dropZone) {
        const fileInput = dropZone.querySelector('input[type="file"]');
        if (fileInput) {
            fileInput.files = files;
            this.updateFileDisplay(dropZone, files[0]);
        }
    }

    updateFileDisplay(dropZone, file) {
        const textElement = dropZone.querySelector('.file-upload-text-modern');
        if (textElement && file) {
            textElement.textContent = `Selected: ${file.name}`;
            dropZone.classList.add('has-file');
        }
    }

    submitForm(form) {
        console.log('submitForm called with form:', form);
        
        // Additional validation before submission
        if (!this.validateForm()) {
            console.log('Form validation failed in submitForm');
            return;
        }
        
        const submitButton = form.querySelector('button[type="submit"]');
        if (!submitButton) {
            console.error('Submit button not found');
            return;
        }
        
        console.log('Setting button to processing state');
        this.setLoadingState(submitButton, true);
        
        // Add visual feedback with animation
        form.classList.add('form-submitting');
        
        console.log('Starting form submission with 500ms delay');
        
        // Submit form after a short delay for visual feedback
        setTimeout(() => {
            console.log('Attempting form submission now');
            
            // Check if this is the final step (step 4 or review page)
            const currentPath = window.location.pathname;
            const isFinalStep = currentPath.includes('step4') || currentPath.includes('review');
            
            console.log('Current path:', currentPath);
            console.log('Is final step:', isFinalStep);
            
            if (isFinalStep) {
                console.log('Detected final step, using AJAX submission');
                this.submitFinalForm(form);
            } else {
                console.log('Intermediate step, using regular form submission');
                // For intermediate steps, try to submit normally
                try {
                    form.submit();
                    console.log('Regular form.submit() called successfully');
                } catch (error) {
                    console.error('Error calling form.submit():', error);
                    // Fallback to AJAX for intermediate steps too
                    this.submitFinalForm(form);
                }
            }
        }, 500);
    }
    
    submitFinalForm(form, submitButton) {
        // Create FormData from the form
        const formData = new FormData(form);
        
        // Submit to the current step URL (step4), which should redirect to review
        const submitUrl = window.location.href; // Current step URL
        console.log('Submitting to current step URL:', submitUrl);
        console.log('Form action attribute:', form.getAttribute('action'));
        console.log('Form method:', form.getAttribute('method'));
        
        // Check user authentication status
        const userAuthenticated = form.getAttribute('data-user-authenticated') === 'true';
        console.log('User authenticated status:', userAuthenticated);
        
        if (!userAuthenticated) {
            console.log('User not authenticated, storing form data and redirecting to login');
            
            // Store form data in sessionStorage
            const formDataObject = {};
            for (let [key, value] of formData.entries()) {
                formDataObject[key] = value;
            }
            sessionStorage.setItem('vendor_registration_data', JSON.stringify(formDataObject));
            sessionStorage.setItem('vendor_registration_step', '4');
            
            // Redirect to login page with return URL
            const currentPath = window.location.pathname;
            window.location.href = `/vendor/login/?next=${encodeURIComponent(currentPath)}`;
            return;
        }
        
        console.log('Form data being submitted:', Object.fromEntries(formData.entries()));
        
        // Use fetch for AJAX submission
        fetch(submitUrl, {
            method: 'POST',
            body: formData,
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(response => {
            console.log('Submission response status:', response.status);
            console.log('Response URL:', response.url);
            
            if (response.ok) {
                // Check if the response URL is different (redirect)
                if (response.url !== submitUrl) {
                    console.log('Redirect detected to:', response.url);
                    window.location.href = response.url;
                } else {
                    // If same URL, check the response text for redirect instructions
                    return response.text().then(data => {
                        console.log('Response data:', data.substring(0, 500));
                        
                        // Look for redirect in meta refresh or JavaScript
                        const parser = new DOMParser();
                        const doc = parser.parseFromString(data, 'text/html');
                        
                        // Check for meta refresh redirect
                        const metaRefresh = doc.querySelector('meta[http-equiv="refresh"]');
                        if (metaRefresh) {
                            const content = metaRefresh.getAttribute('content');
                            const urlMatch = content?.match(/url=(.+)/i);
                            if (urlMatch) {
                                console.log('Meta refresh redirect to:', urlMatch[1]);
                                window.location.href = urlMatch[1];
                                return;
                            }
                        }
                        
                        // Check for Django messages that might indicate next step
                        const successMessage = doc.querySelector('.alert-success');
                        if (successMessage && response.url.includes('step4')) {
                            // If we're still on step4 but got success, go to review
                            console.log('Success on step4, redirecting to review');
                            window.location.href = '/vendor/register/review/';
                        } else {
                            // Default: reload the page to show any messages
                            window.location.reload();
                        }
                    });
                }
            } else {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
        })
        .catch(error => {
            console.error('Submission error:', error);
            alert('There was an error submitting your application. Please try again.');
            this.setLoadingState(submitButton, false);
            form.style.opacity = '1';
            form.style.transform = 'scale(1)';
        });
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new VendorRegistrationManager();
});

// Utility functions for internationalization
const i18n = {
    getMessage: (key, params = {}) => {
        const messages = {
            'validation.required': 'This field is required',
            'validation.minLength': 'Minimum {min} characters required',
            'validation.maxLength': 'Maximum {max} characters allowed',
            'validation.pattern': 'Please enter a valid format',
            'validation.phone': 'Please enter a valid phone number',
            'validation.email': 'Please enter a valid email address',
            'validation.postalCode': 'Please enter a valid postal code',
            'validation.iban': 'Please enter a valid IBAN',
            'form.submitting': 'Processing...',
            'form.success': 'Form submitted successfully!',
            'form.error': 'Please correct the errors and try again.'
        };
        
        let message = messages[key] || key;
        Object.keys(params).forEach(param => {
            message = message.replace(`{${param}}`, params[param]);
        });
        
        return message;
    }
};

// Export for use in other scripts
window.VendorRegistrationManager = VendorRegistrationManager;
window.VendorRegistrationI18n = i18n;