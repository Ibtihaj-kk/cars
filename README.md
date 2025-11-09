# Cars Portal - Vehicle Marketplace Platform

A comprehensive Django-based backend and frontend for a vehicle marketplace platform, featuring advanced search, user management, listings, inquiries, reviews, and subscription management.

## 🚀 Features

### Core Features
- **User Management**: Registration, authentication, profiles, and role-based access control
- **Vehicle Listings**: Create, manage, and search vehicle listings with advanced filtering
- **Parts Marketplace**: Auto parts inventory management with bulk upload and API integration
- **Search & Filtering**: Dynamic search with filters by brand, model, price, location, and specifications
- **Shopping Cart**: Session-based and user-based cart functionality for parts ordering
- **Order Management**: Complete order processing system with status tracking
- **Inquiries System**: Direct messaging between buyers and sellers
- **Reviews & Ratings**: User reviews for vehicles, dealers, and sellers
- **Subscription Management**: Premium listing features and payment integration
- **Admin Panel**: Comprehensive admin interface with analytics and moderation tools
- **Content Management**: Dynamic content management for pages and announcements

### Technical Features
- **RESTful API**: Comprehensive API with OpenAPI/Swagger documentation
- **Authentication**: JWT-based authentication with 2FA support
- **Image Processing**: Automatic image optimization and WebP conversion
- **Cloud Storage**: Support for AWS S3 and Cloudinary
- **Rate Limiting**: API rate limiting and security measures
- **Caching**: Redis-based caching for improved performance
- **Background Tasks**: Celery integration for async processing
- **Monitoring**: Sentry integration for error tracking

## 🏗️ Project Structure

```
carsportal/
├── admin_panel/          # Custom admin interface and analytics
├── content/              # CMS functionality and dynamic content
├── core/                 # Shared utilities, permissions, and mixins
├── inquiries/            # User inquiries and messaging system
├── listings/             # Vehicle listings and search functionality
├── notifications/        # User notifications system
├── parts/                # Auto parts marketplace with cart and orders
├── reviews/              # Reviews and ratings system
├── subscriptions/        # Payment and subscription management
├── users/                # User management and authentication
├── vehicles/             # Vehicle data models and specifications
├── static/               # Frontend assets (CSS, JS, images)
├── templates/            # HTML templates
├── carsportal_project/   # Django project settings
└── requirements.txt      # Python dependencies
```

## 🛠️ Setup Instructions

### Prerequisites

- **Python**: 3.9+ (recommended: 3.11)
- **Database**: PostgreSQL 13+ (recommended) or MySQL 8.0+
- **Redis**: 6.0+ (for caching and Celery)
- **Node.js**: 16+ (for frontend asset compilation, optional)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd carsportal
   ```

2. **Create and activate virtual environment**
   ```bash
   python -m venv venv
   
   # On Windows
   venv\Scripts\activate
   
   # On macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Configuration**
   
   Create a `.env` file in the project root:
   ```env
   # Django Settings
   SECRET_KEY=your-secret-key-here
   DEBUG=True
   ALLOWED_HOSTS=localhost,127.0.0.1
   
   # Database Configuration
   DATABASE_URL=postgresql://username:password@localhost:5432/carsportal_db
   
   # Redis Configuration
   REDIS_URL=redis://localhost:6379/0
   
   # Email Configuration
   EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
   EMAIL_HOST=smtp.gmail.com
   EMAIL_PORT=587
   EMAIL_USE_TLS=True
   EMAIL_HOST_USER=your-email@gmail.com
   EMAIL_HOST_PASSWORD=your-app-password
   
   # Cloud Storage (Optional)
   AWS_ACCESS_KEY_ID=your-aws-access-key
   AWS_SECRET_ACCESS_KEY=your-aws-secret-key
   AWS_STORAGE_BUCKET_NAME=your-bucket-name
   AWS_S3_REGION_NAME=us-east-1
   
   # Cloudinary (Alternative to AWS)
   CLOUDINARY_CLOUD_NAME=your-cloud-name
   CLOUDINARY_API_KEY=your-api-key
   CLOUDINARY_API_SECRET=your-api-secret
   
   # Security
   CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
   
   # Sentry (Production)
   SENTRY_DSN=your-sentry-dsn
   ```

5. **Database Setup**
   ```bash
   # Create database (PostgreSQL example)
   createdb carsportal_db
   
   # Run migrations
   python manage.py migrate
   
   # Create superuser
   python manage.py createsuperuser
   
   # Load sample data (optional)
   python manage.py create_test_data
   ```

6. **Static Files**
   ```bash
   python manage.py collectstatic
   ```

7. **Run Development Server**
   ```bash
   python manage.py runserver
   ```

   The application will be available at `http://127.0.0.1:8000/`

### Background Tasks (Optional)

For production or full feature testing, start Celery workers:

```bash
# Start Celery worker
celery -A carsportal_project worker -l info

# Start Celery beat (for scheduled tasks)
celery -A carsportal_project beat -l info
```

## 📚 API Documentation

### Interactive Documentation
- **Swagger UI**: `http://127.0.0.1:8000/api/docs/`
- **ReDoc**: `http://127.0.0.1:8000/api/redoc/`

### Key API Endpoints

#### Authentication
- `POST /api/auth/register/` - User registration
- `POST /api/auth/login/` - User login
- `POST /api/auth/refresh/` - Token refresh
- `POST /api/auth/logout/` - User logout

#### Listings
- `GET /api/listings/` - List all vehicle listings
- `POST /api/listings/` - Create new listing
- `GET /api/listings/{id}/` - Get listing details
- `PUT /api/listings/{id}/` - Update listing
- `DELETE /api/listings/{id}/` - Delete listing

#### Parts & Orders
- `GET /api/parts/` - List all auto parts
- `POST /api/parts/` - Create new part
- `GET /api/parts/{id}/` - Get part details
- `POST /api/parts/cart/add/{id}/` - Add part to cart
- `GET /api/parts/cart/` - View cart contents
- `POST /api/parts/orders/` - Create new order
- `GET /api/parts/orders/` - List user orders

#### Vehicles
- `GET /api/vehicles/brands/` - List vehicle brands
- `GET /api/vehicles/models/` - List vehicle models
- `GET /api/vehicles/categories/` - List vehicle categories

#### Search & Filtering
- `GET /api/listings/?search=query` - Search listings
- `GET /api/listings/?brand=1&model=2` - Filter by brand/model
- `GET /api/listings/?price_min=10000&price_max=50000` - Price range filter

## 🎨 Frontend

The frontend is built with vanilla JavaScript and includes:

- **Responsive Design**: Mobile-first responsive layout
- **Dynamic Filtering**: Real-time search and filtering
- **Image Galleries**: Interactive image carousels
- **Form Validation**: Client-side form validation
- **AJAX Integration**: Seamless API integration

### Frontend Structure
```
static/
├── css/                  # Stylesheets
│   ├── styles.css       # Main styles
│   ├── navbar.css       # Navigation styles
│   └── ...
├── js/                   # JavaScript files
│   ├── script.js        # Main functionality
│   ├── dynamic-filters.js # Search and filtering
│   └── ...
└── images/              # Static images and logos
```

## 🚀 Deployment

### Production Settings

1. **Environment Variables**
   ```env
   DEBUG=False
   ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
   DATABASE_URL=postgresql://user:pass@host:5432/dbname
   REDIS_URL=redis://redis-host:6379/0
   ```

2. **Static Files**
   ```bash
   python manage.py collectstatic --noinput
   ```

3. **Database Migration**
   ```bash
   python manage.py migrate
   ```

### Docker Deployment

```dockerfile
# Dockerfile example
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
RUN python manage.py collectstatic --noinput

EXPOSE 8000
CMD ["gunicorn", "carsportal_project.wsgi:application", "--bind", "0.0.0.0:8000"]
```

### Nginx Configuration

```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location /static/ {
        alias /path/to/staticfiles/;
    }

    location /media/ {
        alias /path/to/media/;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 🧪 Testing

Run the test suite:

```bash
# Run all tests
python manage.py test

# Run specific app tests
python manage.py test listings

# Run with coverage
coverage run --source='.' manage.py test
coverage report
```

## 📊 Management Commands

The project includes several custom management commands:

```bash
# Create test data
python manage.py create_test_data

# Expire old listings
python manage.py expire_listings

# Optimize images
python manage.py optimize_images

# Moderate reviews
python manage.py moderate_reviews
```

## 🔧 Configuration

### Key Settings

- **CORS**: Configure allowed origins in `settings.py`
- **Rate Limiting**: Adjust rate limits in individual views
- **Image Processing**: Configure image sizes and formats
- **Email**: Set up email backend for notifications
- **Caching**: Configure Redis caching strategy

### Security Features

- JWT token authentication
- Rate limiting on API endpoints
- CORS protection
- SQL injection prevention
- XSS protection
- CSRF protection

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

For support and questions:

- Create an issue in the repository
- Check the API documentation at `/api/docs/`
- Review the Django admin panel at `/admin/`

## 🔄 Version History

- **v1.0.0** - Initial release with core functionality
- **v1.1.0** - Added advanced search and filtering
- **v1.2.0** - Enhanced admin panel and analytics
- **v1.3.0** - Added subscription management
- **v1.4.0** - Improved frontend and mobile responsiveness
- **v1.5.0** - Added auto parts marketplace with cart and order management
- **v1.5.1** - Fixed authentication issues and improved test coverage

---

**Cars Portal** - Connecting buyers and sellers in the automotive marketplace.