# IRIDA Uploader Web (IUW)

A Django-based web service for managing file uploads with dual authentication support (local and LDAP).

## Features

- Dual authentication support (Local DB and LDAP)
- User-specific upload directories
- Multi-file upload support
- Automatic retry mechanism for failed uploads
- Email and in-app notifications
- Dashboard with upload history
- Celery-based background task processing
- Docker containerization support
- PostgreSQL database support
- Redis for caching and message broker

## Prerequisites

- Docker and Docker Compose (recommended)
- Python 3.8+ (for local development)
- PostgreSQL
- Redis Server
- LDAP Server (optional)

## Deployment Options

### Using Docker (Recommended)

1. Clone the repository:
```bash
git clone <repository-url>
cd IUW
```

2. Configure environment variables:
```bash
cp .env.example .env
```

3. Edit the `.env` file with your specific configuration

4. Start the services using Docker Compose:
```bash
docker compose up -d
```

This will start:
- Web application (Gunicorn)
- Celery worker
- Celery beat scheduler
- Redis
- PostgreSQL database

### Local Development Setup

1. Clone the repository and create virtual environment:
```bash
git clone <repository-url>
cd IUW
python -m venv venv
source venv/bin/activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment variables:
```bash
cp .env.example .env
```

4. Initialize the database:
```bash
python manage.py migrate
python manage.py createsuperuser
```

5. Start the development services:
```bash
# Start Redis
redis-server

# Start Celery Worker
celery -A IUW worker -l info

# Start Celery Beat (optional)
celery -A IUW beat -l info

# Start Django Development Server
python manage.py runserver
```

## Configuration

### Required Environment Variables

```ini
# Django Settings
DJANGO_SECRET_KEY=your-secret-key
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,irida-domain

# Database Settings
DATABASE_URL=postgresql://user:password@localhost:5432/dbname

# Redis Settings
REDIS_HOST=127.0.0.1
REDIS_PORT=6379
CELERY_BROKER_URL=redis://127.0.0.1:6379/0

# IRIDA Settings
IRIDA_BASE_URL=http://your-irida-server/irida
IRIDA_API_URL=http://your-irida-server/irida/api
IRIDA_CLIENT_ID=your-client-id
IRIDA_CLIENT_SECRET=your-client-secret
```

### Optional Settings

```ini
# LDAP Configuration
USE_LDAP=True
LDAP_SERVER_URI=ldap://your.ldap.server
LDAP_BIND_DN=your-bind-dn
LDAP_BIND_PASSWORD_B64=base64-encoded-password
LDAP_SEARCH_BASE=your-search-base

# Email Configuration
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=your-smtp-server
EMAIL_PORT=25
DEFAULT_FROM_EMAIL=no-reply@example.com

# File Upload Settings
UPLOAD_ROOT=/path/to/upload/directory
MAX_UPLOAD_SIZE=5242880000  # 5GB in bytes
```

## API Endpoints

- `/api/auth/` - Authentication endpoints
- `/api/uploads/` - File upload management
- `/api/notifications/` - Notification management
- `/ws/status/` - WebSocket endpoint for real-time updates


## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## Author

- [@thanhleviet](https://github.com/thanhleviet)

## License

This project is licensed under the MIT License. 