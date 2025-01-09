# IRIDA Uploader Web (IUW)

A Django-based web service for managing file uploads with dual authentication support (local and LDAP).

## Features

- Dual authentication support (Local DB and LDAP)
- User-specific upload directories
- Real-time upload status updates
- Multi-file upload support
- Automatic retry mechanism for failed uploads
- Email and in-app notifications
- Dashboard with upload history
- WebSocket support for real-time updates

## Prerequisites

- Python 3.8+
- Redis Server
- LDAP Server (optional)
- Virtual Environment (recommended)

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd IUW
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment variables:
Copy the example environment file and modify it with your settings:
```bash
cp .env.example .env
```

Edit the `.env` file with your specific configuration:

```ini
# Django Settings
DJANGO_SECRET_KEY=your-secret-key-here
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

# Email Settings
EMAIL_HOST=smtp.your-email-provider.com
EMAIL_HOST_USER=your-email@example.com
EMAIL_HOST_PASSWORD=your-email-password

# LDAP Settings (if using LDAP authentication)
LDAP_SERVER_URI=ldap://your.ldap.server
LDAP_BIND_DN=your-bind-dn
LDAP_BIND_PASSWORD=your-bind-password
LDAP_SEARCH_BASE=ou=users,dc=example,dc=com

# IRIDA Settings
IRIDA_BASE_URL=https://your.irida.server
IRIDA_CLIENT_ID=your-client-id
IRIDA_CLIENT_SECRET=your-client-secret
IRIDA_USERNAME=your-username
IRIDA_PASSWORD=your-password
```

See `.env.example` for all available configuration options.

5. Initialize the database:
```bash
python manage.py migrate
```

6. Create a superuser:
```bash
python manage.py createsuperuser
```

## Running the Application

1. Start Redis Server:
```bash
redis-server
```

2. Start Celery Worker:
```bash
celery -A IUW worker -l info
```

3. Start Django Development Server:
```bash
python manage.py runserver
```

The application will be available at `http://localhost:8000`

## Directory Structure

The upload directory structure follows the pattern:
```
{UPLOAD_ROOT}/{user_email}/
```

## Authentication

The system supports two authentication methods:
1. Local Database Authentication
2. LDAP Authentication

Users can toggle between these methods on the login page.

## API Endpoints

- `/login/` - Authentication endpoint
- `/` - Dashboard
- `/folders/` - Get user's folders
- `/upload/` - File upload endpoint
- `/upload/<id>/status/` - Get upload status
- `/notifications/` - Get user notifications
- `/notifications/<id>/read/` - Mark notification as read

## WebSocket Support

Real-time updates are available through WebSocket connection:
```
ws://localhost:8000/ws/notifications/
```

## Environment Variables

The application uses environment variables for configuration. These can be set in a `.env` file in the project root.

### Required Variables
- `DJANGO_SECRET_KEY`: Django secret key
- `IRIDA_BASE_URL`: IRIDA server URL
- `IRIDA_CLIENT_ID`: IRIDA client ID
- `IRIDA_CLIENT_SECRET`: IRIDA client secret

### Optional Variables
- `DJANGO_DEBUG`: Enable debug mode (default: True)
- `DJANGO_ALLOWED_HOSTS`: Allowed hosts (default: *)
- `EMAIL_*`: Email server configuration
- `LDAP_*`: LDAP server configuration
- `REDIS_*`: Redis server configuration
- `UPLOAD_ROOT`: Upload directory path
- `MAX_UPLOAD_SIZE`: Maximum upload file size

See `.env.example` for all available options and their default values.

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License. 