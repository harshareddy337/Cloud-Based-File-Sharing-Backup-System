# Cloud File Sharing System

A secure, scalable Flask-based file sharing application with support for large media files (videos, music, documents) and multiple cloud storage backends.

## ✨ Features

### Core Features
- 🔐 **Secure Authentication**: OTP-based login with email verification
- 📁 **File Management**: Upload, download, and delete files
- 👥 **User-Specific Storage**: Each user has isolated file storage
- 🎨 **Image Previews**: Inline preview for uploaded images
- 📊 **File Tracking**: View file metadata and download counts

### Large Media Optimization
- 📹 **1GB File Support**: Upload videos, music, and large documents
- 📋 **File Metadata**: Automatic MIME type detection and storage
- ⏱️ **Media Duration**: Automatic extraction for audio/video files
- 📦 **Size Tracking**: Files are displayed with human-readable sizes
- ⚡ **Performance**: Optimized for large file transfers

### Multi-Cloud Storage
- 💾 **Local Storage**: Default, no setup required
- 🌩️ **Google Cloud Storage (GCS)**: Enterprise-grade cloud storage
- 🪣 **Amazon S3**: AWS S3 bucket integration
- ☁️ **Azure Blob Storage**: Microsoft Azure integration

## Prerequisites

- Python 3.8+
- ffprobe (optional, for media duration extraction)
  - Windows: `choco install ffmpeg`
  - macOS: `brew install ffmpeg`
  - Linux: `sudo apt-get install ffmpeg`

## Quick Start

### 1. Setup Environment

```powershell
# Create virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Database

```powershell
# Create fresh database
python create_db.py

# OR migrate existing database (preserves data)
python migrate_db.py
```

### 3. Configure Environment

```powershell
# Copy example configuration
cp .env.example .env

# Edit .env with your settings
# At minimum, set:
# - SECRET_KEY (any random string)
# - STORAGE_TYPE (local, gcs, s3, or azure)
# - SMTP settings (for email OTP)
```

### 4. Run Application

```powershell
python app.py

# App will be available at http://127.0.0.1:5000
```

## Configuration

### Environment Variables

#### Basic Settings
```env
SECRET_KEY=your-secret-key-here
STORAGE_TYPE=local
```

#### Email Configuration (for OTP)
```env
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

#### Local Storage (Default)
No additional configuration needed. Files stored in `./uploads/` directory.

#### Google Cloud Storage
```env
STORAGE_TYPE=gcs
GCS_BUCKET=your-bucket-name
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
```

#### Amazon S3
```env
STORAGE_TYPE=s3
AWS_BUCKET=your-bucket-name
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret
```

#### Azure Blob Storage
```env
STORAGE_TYPE=azure
AZURE_CONTAINER=your-container
AZURE_ACCOUNT_NAME=your-account
AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=...
```

See [.env.example](.env.example) for complete configuration options.

## Database Schema

### Users Table
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    name TEXT,
    email TEXT UNIQUE,
    password_hash TEXT,
    created_at DATETIME
)
```

### Files Table
```sql
CREATE TABLE files (
    id INTEGER PRIMARY KEY,
    stored_name TEXT,
    original_name TEXT,
    user_id INTEGER,
    uploaded_at DATETIME,
    downloads INTEGER,
    file_size INTEGER,              -- NEW: Size in bytes
    mime_type TEXT,                 -- NEW: File type (e.g., video/mp4)
    duration REAL,                  -- NEW: Duration for audio/video
    FOREIGN KEY (user_id) REFERENCES users(id)
)
```

## API Endpoints

### Authentication
- `GET /register` - Registration page
- `POST /register` - Register new user
- `GET /login` - Login page
- `POST /login` - Login (initiates OTP)
- `GET /verify` - OTP verification page
- `POST /verify` - Verify OTP
- `POST /resend_otp` - Resend OTP code
- `GET /logout` - Logout

### File Operations
- `GET /dashboard` - Main dashboard (file list + upload)
- `POST /dashboard` - Upload file
- `GET /download/<int:file_id>` - Download file by ID
- `GET /download/<filename>` - Download file by name
- `DELETE /delete/<int:file_id>` - Delete file
- `GET /preview/<int:file_id>` - Preview image

### Diagnostics
- `POST /test-smtp` - Test email configuration
- `POST /test-gcs` - Test cloud storage connection

## File Size Limits

- **Maximum File Size**: 1 GB (1,073,741,824 bytes)
- All file types accepted (videos, music, documents, images, archives, etc.)

## Troubleshooting

### Database Issues
```powershell
# Reset database (delete existing)
Remove-Item cloud.db
python create_db.py

# Or migrate existing
python migrate_db.py
```

### Storage Issues
- **Local**: Check `./uploads/` directory permissions
- **GCS**: Verify `GOOGLE_APPLICATION_CREDENTIALS` file path
- **S3**: Check AWS credentials and bucket permissions
- **Azure**: Verify connection string or storage key

### Media Duration Issues
- Install ffprobe: `choco install ffmpeg` (Windows)
- Verify file format is supported
- Duration extraction is non-blocking (upload continues even if it fails)

## Project Structure

```
cloud-file-sharing-system/
├── app.py                    # Main Flask application
├── create_db.py              # Database initialization
├── migrate_db.py             # Database migration script
├── requirements.txt          # Python dependencies
├── .env.example              # Configuration template
├── README.md                 # This file
├── FEATURES.md               # Detailed feature documentation
├── templates/
│   ├── base.html             # Base template
│   ├── login.html            # Login page
│   ├── register.html         # Registration page
│   ├── verify.html           # OTP verification page
│   ├── dashboard.html        # Main dashboard
│   └── settings.html         # Settings page
├── static/
│   └── style.css             # Stylesheet
└── uploads/                  # Local file storage (created automatically)
```

---

**Version**: 2.0 (Large Media Optimization)
**Last Updated**: February 2026

For detailed feature documentation, see [FEATURES.md](FEATURES.md)
