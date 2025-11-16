/**
 * Vendor Form Validation System
 * Integrated with Unified Design System
 */

class VendorFormValidator {
    constructor(formSelector, options = {}) {
        this.form = typeof formSelector === 'string' ? document.querySelector(formSelector) : formSelector;
        this.options = {
            validateOnSubmit: true,
            validateOnBlur: true,
            validateOnInput: false,
            showSuccessState: true,
            showErrorMessages: true,
            scrollToFirstError: true,
            focusFirstError: true,
            customMessages: {},
            customValidators: {},
            ...options
        };
        
        this.validators = {
            required: this.validateRequired.bind(this),
            email: this.validateEmail.bind(this),
            phone: this.validatePhone.bind(this),
            url: this.validateUrl.bind(this),
            number: this.validateNumber.bind(this),
            integer: this.validateInteger.bind(this),
            min: this.validateMin.bind(this),
            max: this.validateMax.bind(this),
            minlength: this.validateMinLength.bind(this),
            maxlength: this.validateMaxLength.bind(this),
            pattern: this.validatePattern.bind(this),
            match: this.validateMatch.bind(this),
            file: this.validateFile.bind(this),
            ...this.options.customValidators
        };
        
        this.messages = {
            required: 'This field is required',
            email: 'Please enter a valid email address',
            phone: 'Please enter a valid phone number',
            url: 'Please enter a valid URL',
            number: 'Please enter a valid number',
            integer: 'Please enter a whole number',
            min: 'Value must be at least {min}',
            max: 'Value must be no more than {max}',
            minlength: 'Must be at least {minlength} characters',
            maxlength: 'Must be no more than {maxlength} characters',
            pattern: 'Please match the required format',
            match: 'Values do not match',
            file: 'Please select a valid file',
            ...this.options.customMessages
        };
        
        this.init();
    }
    
    init() {
        if (!this.form) {
            console.error('Form not found');
            return;
        }
        
        this.bindEvents();
        this.setupRealTimeValidation();
    }
    
    bindEvents() {
        if (this.options.validateOnSubmit) {
            this.form.addEventListener('submit', this.handleSubmit.bind(this));
        }
        
        if (this.options.validateOnBlur) {
            this.form.addEventListener('blur', this.handleBlur.bind(this), true);
        }
        
        if (this.options.validateOnInput) {
            this.form.addEventListener('input', this.handleInput.bind(this), true);
        }
    }
    
    setupRealTimeValidation() {
        // Add input formatting for specific fields
        this.form.querySelectorAll('[data-format]').forEach(field => {
            const format = field.getAttribute('data-format');
            field.addEventListener('input', (e) => this.formatInput(e, format));
        });
        
        // Add character counter for textareas
        this.form.querySelectorAll('textarea[data-maxlength]').forEach(textarea => {
            this.setupCharacterCounter(textarea);
        });
        
        // Add password strength indicator
        this.form.querySelectorAll('input[type="password"][data-strength]').forEach(password => {
            this.setupPasswordStrength(password);
        });
    }
    
    handleSubmit(e) {
        if (!this.validateForm()) {
            e.preventDefault();
            e.stopPropagation();
            
            if (this.options.scrollToFirstError) {
                this.scrollToFirstError();
            }
            
            if (this.options.focusFirstError) {
                this.focusFirstError();
            }
        }
    }
    
    handleBlur(e) {
        const field = e.target;
        if (this.shouldValidateField(field)) {
            this.validateField(field);
        }
    }
    
    handleInput(e) {
        const field = e.target;
        if (this.shouldValidateField(field)) {
            this.validateField(field, true);
        }
    }
    
    shouldValidateField(field) {
        return field.matches('input, textarea, select') && 
               (field.hasAttribute('required') || 
                field.hasAttribute('data-validate') ||
                field.type === 'email' ||
                field.type === 'url' ||
                field.type === 'number' ||
                field.hasAttribute('pattern') ||
                field.hasAttribute('min') ||
                field.hasAttribute('max') ||
                field.hasAttribute('minlength') ||
                field.hasAttribute('maxlength'));
    }
    
    validateForm() {
        const fields = this.form.querySelectorAll('input, textarea, select');
        let isValid = true;
        const errors = [];
        
        fields.forEach(field => {
            if (this.shouldValidateField(field)) {
                const fieldErrors = this.validateField(field, false);
                if (fieldErrors.length > 0) {
                    isValid = false;
                    errors.push({ field, errors: fieldErrors });
                }
            }
        });
        
        return isValid;
    }
    
    validateField(field, showErrors = true) {
        const errors = [];
        const value = field.value.trim();
        const rules = this.getFieldRules(field);
        
        rules.forEach(rule => {
            const validator = this.validators[rule.type];
            if (validator && !validator(value, field, rule.params)) {
                errors.push(this.getErrorMessage(rule.type, rule.params, field));
            }
        });
        
        if (showErrors) {
            this.showFieldValidation(field, errors);
        }
        
        return errors;
    }
    
    getFieldRules(field) {
        const rules = [];
        
        if (field.hasAttribute('required')) {
            rules.push({ type: 'required', params: {} });
        }
        
        if (field.type === 'email') {
            rules.push({ type: 'email', params: {} });
        }
        
        if (field.type === 'url') {
            rules.push({ type: 'url', params: {} });
        }
        
        if (field.type === 'number') {
            rules.push({ type: 'number', params: {} });
        }
        
        if (field.hasAttribute('pattern')) {
            rules.push({ 
                type: 'pattern', 
                params: { pattern: field.getAttribute('pattern') } 
            });
        }
        
        if (field.hasAttribute('min')) {
            rules.push({ 
                type: 'min', 
                params: { min: parseFloat(field.getAttribute('min')) } 
            });
        }
        
        if (field.hasAttribute('max')) {
            rules.push({ 
                type: 'max', 
                params: { max: parseFloat(field.getAttribute('max')) } 
            });
        }
        
        if (field.hasAttribute('minlength')) {
            rules.push({ 
                type: 'minlength', 
                params: { minlength: parseInt(field.getAttribute('minlength')) } 
            });
        }
        
        if (field.hasAttribute('maxlength')) {
            rules.push({ 
                type: 'maxlength', 
                params: { maxlength: parseInt(field.getAttribute('maxlength')) } 
            });
        }
        
        if (field.hasAttribute('data-match')) {
            rules.push({ 
                type: 'match', 
                params: { match: field.getAttribute('data-match') } 
            });
        }
        
        if (field.hasAttribute('data-validate')) {
            const customRules = field.getAttribute('data-validate').split(',');
            customRules.forEach(rule => {
                const [type, ...params] = rule.split(':');
                rules.push({ 
                    type: type.trim(), 
                    params: this.parseParams(params.join(':')) 
                });
            });
        }
        
        return rules;
    }
    
    // Validators
    validateRequired(value, field, params) {
        if (field.type === 'checkbox') {
            return field.checked;
        }
        if (field.type === 'radio') {
            const name = field.name;
            const radios = this.form.querySelectorAll(`input[name="${name}"]`);
            return Array.from(radios).some(radio => radio.checked);
        }
        if (field.type === 'file') {
            return field.files.length > 0;
        }
        return value.length > 0;
    }
    
    validateEmail(value, field, params) {
        if (!value) return true;
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(value);
    }
    
    validatePhone(value, field, params) {
        if (!value) return true;
        const phoneRegex = /^[\+]?[1-9][\d]{0,15}$/;
        return phoneRegex.test(value.replace(/[\s\-\(\)]/g, ''));
    }
    
    validateUrl(value, field, params) {
        if (!value) return true;
        try {
            new URL(value);
            return true;
        } catch {
            return false;
        }
    }
    
    validateNumber(value, field, params) {
        if (!value) return true;
        return !isNaN(value) && !isNaN(parseFloat(value));
    }
    
    validateInteger(value, field, params) {
        if (!value) return true;
        return /^-?\d+$/.test(value);
    }
    
    validateMin(value, field, params) {
        if (!value) return true;
        const num = parseFloat(value);
        return !isNaN(num) && num >= params.min;
    }
    
    validateMax(value, field, params) {
        if (!value) return true;
        const num = parseFloat(value);
        return !isNaN(num) && num <= params.max;
    }
    
    validateMinLength(value, field, params) {
        if (!value) return true;
        return value.length >= params.minlength;
    }
    
    validateMaxLength(value, field, params) {
        if (!value) return true;
        return value.length <= params.maxlength;
    }
    
    validatePattern(value, field, params) {
        if (!value) return true;
        const regex = new RegExp(params.pattern);
        return regex.test(value);
    }
    
    validateMatch(value, field, params) {
        if (!value) return true;
        const matchField = this.form.querySelector(params.match);
        return matchField && value === matchField.value;
    }
    
    validateFile(value, field, params) {
        if (!field.files || field.files.length === 0) return true;
        
        const file = field.files[0];
        const allowedTypes = params.types ? params.types.split(',') : [];
        const maxSize = params.maxSize ? parseInt(params.maxSize) : 0;
        
        if (allowedTypes.length > 0 && !allowedTypes.includes(file.type)) {
            return false;
        }
        
        if (maxSize > 0 && file.size > maxSize) {
            return false;
        }
        
        return true;
    }
    
    // Utility methods
    getErrorMessage(type, params, field) {
        let message = this.messages[type] || 'Invalid field';
        
        // Replace placeholders
        Object.keys(params).forEach(key => {
            message = message.replace(new RegExp(`{${key}}`, 'g'), params[key]);
        });
        
        // Add field label if available
        const label = this.getFieldLabel(field);
        if (label && !message.includes(label)) {
            message = `${label}: ${message}`;
        }
        
        return message;
    }
    
    getFieldLabel(field) {
        const label = this.form.querySelector(`label[for="${field.id}"]`);
        if (label) {
            return label.textContent.trim().replace('*', '').trim();
        }
        
        const placeholder = field.getAttribute('placeholder');
        if (placeholder) {
            return placeholder;
        }
        
        return field.name || field.type || 'Field';
    }
    
    showFieldValidation(field, errors) {
        this.clearFieldValidation(field);
        
        const formGroup = field.closest('.ym-form-group') || field.parentElement;
        
        if (errors.length === 0) {
            if (this.options.showSuccessState) {
                field.classList.add('ym-is-valid');
            }
        } else {
            field.classList.add('ym-is-invalid');
            
            if (this.options.showErrorMessages) {
                errors.forEach(error => {
                    const errorElement = document.createElement('div');
                    errorElement.className = 'ym-form-feedback ym-invalid-feedback';
                    errorElement.textContent = error;
                    formGroup.appendChild(errorElement);
                });
            }
        }
    }
    
    clearFieldValidation(field) {
        field.classList.remove('ym-is-valid', 'ym-is-invalid');
        
        const formGroup = field.closest('.ym-form-group') || field.parentElement;
        const errorElements = formGroup.querySelectorAll('.ym-invalid-feedback, .ym-valid-feedback');
        errorElements.forEach(el => el.remove());
    }
    
    scrollToFirstError() {
        const firstError = this.form.querySelector('.ym-is-invalid');
        if (firstError) {
            firstError.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    }
    
    focusFirstError() {
        const firstError = this.form.querySelector('.ym-is-invalid');
        if (firstError) {
            firstError.focus();
        }
    }
    
    // Formatting methods
    formatInput(e, format) {
        const field = e.target;
        let value = field.value;
        
        switch (format) {
            case 'phone':
                field.value = this.formatPhone(value);
                break;
            case 'currency':
                field.value = this.formatCurrency(value);
                break;
            case 'card':
                field.value = this.formatCardNumber(value);
                break;
            case 'date':
                field.value = this.formatDate(value);
                break;
        }
    }
    
    formatPhone(value) {
        const digits = value.replace(/\D/g, '');
        if (digits.length <= 3) return digits;
        if (digits.length <= 6) return `(${digits.slice(0, 3)}) ${digits.slice(3)}`;
        return `(${digits.slice(0, 3)}) ${digits.slice(3, 6)}-${digits.slice(6, 10)}`;
    }
    
    formatCurrency(value) {
        const number = parseFloat(value.replace(/[^\d.-]/g, ''));
        if (isNaN(number)) return '';
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'AED'
        }).format(number);
    }
    
    formatCardNumber(value) {
        const digits = value.replace(/\D/g, '');
        return digits.match(/.{1,4}/g)?.join(' ') || digits;
    }
    
    formatDate(value) {
        const digits = value.replace(/\D/g, '');
        if (digits.length <= 2) return digits;
        if (digits.length <= 4) return `${digits.slice(0, 2)}/${digits.slice(2)}`;
        return `${digits.slice(0, 2)}/${digits.slice(2, 4)}/${digits.slice(4, 8)}`;
    }
    
    // Character counter
    setupCharacterCounter(textarea) {
        const maxLength = parseInt(textarea.getAttribute('data-maxlength'));
        const counter = document.createElement('div');
        counter.className = 'ym-form-help';
        
        const updateCounter = () => {
            const currentLength = textarea.value.length;
            counter.textContent = `${currentLength}/${maxLength} characters`;
            
            if (currentLength > maxLength) {
                counter.style.color = 'var(--ym-color-error-600)';
            } else if (currentLength > maxLength * 0.9) {
                counter.style.color = 'var(--ym-color-warning-600)';
            } else {
                counter.style.color = 'var(--ym-color-gray-600)';
            }
        };
        
        textarea.parentNode.appendChild(counter);
        textarea.addEventListener('input', updateCounter);
        updateCounter();
    }
    
    // Password strength
    setupPasswordStrength(password) {
        const strengthBar = document.createElement('div');
        strengthBar.className = 'ym-password-strength';
        strengthBar.innerHTML = `
            <div class="ym-password-strength-bar">
                <div class="ym-password-strength-fill"></div>
            </div>
            <div class="ym-password-strength-text"></div>
        `;
        
        password.parentNode.appendChild(strengthBar);
        
        const updateStrength = () => {
            const strength = this.calculatePasswordStrength(password.value);
            const fill = strengthBar.querySelector('.ym-password-strength-fill');
            const text = strengthBar.querySelector('.ym-password-strength-text');
            
            fill.style.width = `${strength.percentage}%`;
            fill.className = `ym-password-strength-fill ym-password-strength-${strength.level}`;
            text.textContent = strength.text;
            text.className = `ym-password-strength-text ym-password-strength-${strength.level}`;
        };
        
        password.addEventListener('input', updateStrength);
        updateStrength();
    }
    
    calculatePasswordStrength(password) {
        let score = 0;
        
        if (password.length >= 8) score += 25;
        if (password.length >= 12) score += 25;
        if (/[a-z]/.test(password)) score += 15;
        if (/[A-Z]/.test(password)) score += 15;
        if (/\d/.test(password)) score += 15;
        if (/[^\w\s]/.test(password)) score += 15;
        
        if (score < 25) return { level: 'weak', text: 'Weak password', percentage: 25 };
        if (score < 50) return { level: 'fair', text: 'Fair password', percentage: 50 };
        if (score < 75) return { level: 'good', text: 'Good password', percentage: 75 };
        return { level: 'strong', text: 'Strong password', percentage: 100 };
    }
    
    // Utility methods
    parseParams(paramString) {
        if (!paramString) return {};
        
        const params = {};
        paramString.split(',').forEach(param => {
            const [key, value] = param.split('=');
            if (key && value !== undefined) {
                params[key.trim()] = isNaN(value) ? value.trim() : parseFloat(value);
            }
        });
        
        return params;
    }
    
    // Public API
    reset() {
        this.form.querySelectorAll('.ym-is-valid, .ym-is-invalid').forEach(field => {
            this.clearFieldValidation(field);
        });
    }
    
    destroy() {
        this.form.removeEventListener('submit', this.handleSubmit);
        this.form.removeEventListener('blur', this.handleBlur, true);
        this.form.removeEventListener('input', this.handleInput, true);
        this.reset();
    }
}

// CSS for form validation
const formValidationCSS = `
.ym-password-strength {
    margin-top: var(--ym-space-2);
}

.ym-password-strength-bar {
    height: 4px;
    background: var(--ym-color-gray-200);
    border-radius: var(--ym-radius-full);
    overflow: hidden;
    margin-bottom: var(--ym-space-1);
}

.ym-password-strength-fill {
    height: 100%;
    transition: width var(--ym-transition-normal), background-color var(--ym-transition-normal);
    border-radius: var(--ym-radius-full);
}

.ym-password-strength-weak {
    background: var(--ym-color-error-500);
}

.ym-password-strength-fair {
    background: var(--ym-color-warning-500);
}

.ym-password-strength-good {
    background: var(--ym-color-info-500);
}

.ym-password-strength-strong {
    background: var(--ym-color-success-500);
}

.ym-password-strength-text {
    font-size: var(--ym-text-xs);
    font-weight: var(--ym-font-medium);
    text-transform: uppercase;
    letter-spacing: 0.025em;
}

.ym-password-strength-weak {
    color: var(--ym-color-error-600);
}

.ym-password-strength-fair {
    color: var(--ym-color-warning-600);
}

.ym-password-strength-good {
    color: var(--ym-color-info-600);
}

.ym-password-strength-strong {
    color: var(--ym-color-success-600);
}
`;

// Inject CSS
if (!document.querySelector('#ym-form-validation-styles')) {
    const style = document.createElement('style');
    style.id = 'ym-form-validation-styles';
    style.textContent = formValidationCSS;
    document.head.appendChild(style);
}

// Export for use
window.VendorFormValidator = VendorFormValidator;