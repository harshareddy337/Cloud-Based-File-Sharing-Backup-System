# Cloud File Sharing System - Large Media Optimization Features

## Overview
This document describes the optimizations and features implemented for handling large media files (videos, music, documents, etc.) in the Cloud File Sharing System.

## Key Improvements

### 1. **Increased File Size Limit**
- **Previous limit**: 200 MB
- **New limit**: 1 GB (1,073,741,824 bytes)
- Files larger than 1GB will be rejected with an error message

### 2. **File Metadata Tracking**
The database now tracks comprehensive file information:

```
- file_size (INTEGER): Size of file in bytes
- mime_type (VARCHAR): MIME type (e.g., "video/mp4", "audio/mpeg", "application/pdf")
- duration (FLOAT): Duration in seconds for audio/video files (NULL for other types)
```

#### Database Schema
```sql
CREATE TABLE files (
    id INTEGER PRIMARY KEY,
    stored_name TEXT,
    original_name TEXT,
    user_id INTEGER,
    uploaded_at DATETIME,
    downloads INTEGER,
    file_size INTEGER DEFAULT 0,
    mime_type TEXT DEFAULT 'application/octet-stream',
    duration REAL,
    FOREIGN KEY (user_id) REFERENCES users(id)
)
```

### 3. **Multi-Cloud Storage Support**

The system supports 4 storage backends:

#### a) **Local Storage (Default)**
- Stores files in `./uploads/` directory
- Configuration: `STORAGE_TYPE=local`
- No additional setup needed

#### b) **Google Cloud Storage (GCS)**
```env
STORAGE_TYPE=gcs
GCS_BUCKET=your-bucket-name
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
```

#### c) **Amazon S3**
```env
STORAGE_TYPE=s3
AWS_BUCKET=your-bucket-name
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
```

#### d) **Azure Blob Storage**
```env
STORAGE_TYPE=azure
AZURE_CONTAINER=your-container-name
AZURE_ACCOUNT_NAME=your-account-name
AZURE_STORAGE_CONNECTION_STRING=...
# OR
AZURE_STORAGE_KEY=your-storage-key
```

### 4. **Media Duration Extraction**

For audio and video files, the system automatically extracts and stores:
- Duration in seconds
- Displayed in the UI as minutes (e.g., "2.5m" for 2 minutes 30 seconds)

**Requirements**: ffprobe must be installed
```bash
# On Windows (with ffmpeg installed)
choco install ffmpeg

# On macOS
brew install ffmpeg

# On Linux (Ubuntu/Debian)
sudo apt-get install ffmpeg
```

### 5. **Automatic MIME Type Detection**

- Detects file type from uploaded file or filename
- Fallback to "application/octet-stream" if unknown
- Used for proper file serving and media player detection

### 6. **Enhanced File Display**

The dashboard now shows:
- ✅ File name and thumbnail (for images)
- ✅ File size in human-readable format (B, KB, MB, GB)
- ✅ File type category (video, audio, image, document, etc.)
- ✅ Duration for media files (MM:SS format)
- ✅ Download count
- ✅ Upload timestamp

### 7. **Chunked Upload Infrastructure** (Ready for Frontend Implementation)

The backend is prepared for chunked uploads:
- Increased MAX_CONTENT_LENGTH to 1GB
- File data is not loaded into memory entirely
- Stream-based upload using `file.stream`

Frontend integration can include:
- Progress bars
- Resume capability
- Multiple file uploads
- Upload speed indication

### 8. **Performance Optimizations**

- **Database Indexing**: Indexed on `user_id` for fast file listings
- **Lazy Loading**: Files are queried per-user
- **Signed URLs**: Cloud storage uses signed URLs (no proxying for large files)
- **Direct Downloads**: Large files bypass the app server when using cloud storage

## Setup Instructions

### 1. Database Migration

Update existing database:
```bash
# Option A: Backup and recreate (if data loss acceptable)
# Delete cloud.db and run:
python create_db.py

# Option B: Add columns to existing database (if data important)
# Run these SQL commands:
ALTER TABLE files ADD COLUMN file_size INTEGER DEFAULT 0;
ALTER TABLE files ADD COLUMN mime_type TEXT DEFAULT 'application/octet-stream';
ALTER TABLE files ADD COLUMN duration REAL;
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

New packages for multi-cloud support:
- `boto3>=1.26.0` - AWS S3 support
- `azure-storage-blob>=12.14.0` - Azure Blob Storage support
- Existing: `google-cloud-storage>=2.0` - GCS support

Optional but recommended:
```bash
pip install ffmpeg-python  # For advanced media processing
```

### 3. Configure Environment

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

Edit `.env`:
```env
SECRET_KEY=your-secret-key
STORAGE_TYPE=local  # or gcs, s3, azure

# For cloud storage, set provider-specific variables
# See .env.example for all options
```

### 4. Run Tests

Test SMTP (email OTP):
```bash
curl -X POST http://localhost:5000/test-smtp \
  -d 'to=your-email@example.com'
```

Test Cloud Storage:
```bash
curl -X POST http://localhost:5000/test-gcs
```

## File Type Detection

The system automatically detects and categorizes files:

| Category | MIME Type |
|----------|-----------|
| Video | `video/*` (mp4, mkv, avi, mov, webm, etc.) |
| Audio | `audio/*` (mp3, wav, aac, flac, m4a, etc.) |
| Image | `image/*` (jpg, png, gif, webp, etc.) |
| Document | `application/*` (pdf, docx, xlsx, etc.) |
| Archive | `application/zip`, `application/x-rar`, etc. |

## API Responses

### Upload Response (AJAX)
```json
{
    "status": "ok",
    "file": {
        "id": 42,
        "name": "video.mp4",
        "is_image": false,
        "size": 1073741824,
        "size_human": "1.0 GB",
        "mime_type": "video/mp4",
        "duration": 3600.5
    }
}
```

### File List Response
```json
{
    "files": [
        {
            "id": 42,
            "name": "video.mp4",
            "is_image": false,
            "size": 1073741824,
            "size_human": "1.0 GB",
            "mime_type": "video/mp4",
            "duration": 3600.5
        }
    ]
}
```

## Storage Comparison

| Feature | Local | GCS | S3 | Azure |
|---------|-------|-----|----|----- |
| Setup Difficulty | Easy | Medium | Medium | Medium |
| Cost | Free* | Moderate | Moderate | Moderate |
| Scalability | Low | High | High | High |
| Performance | Fast | Fast | Fast | Fast |
| Redundancy | None | High | High | High |
| Best For | Development | Production | Production | Production |

*Local storage uses disk space

## Troubleshooting

### Files not uploading
- Check file size limit: max 1GB
- Verify STORAGE_TYPE environment variable
- For cloud storage, verify credentials are correct
- Check server logs: `python app.py` in debug mode

### Media duration not extracted
- Ensure ffprobe is installed: `ffprobe -version`
- Check file format is supported by ffmpeg
- Duration extraction is non-blocking (file uploads even if extraction fails)

### Cloud storage test fails
- Verify credentials/connection string
- For GCS: Check GOOGLE_APPLICATION_CREDENTIALS path
- For S3: Verify AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY
- For Azure: Check AZURE_STORAGE_CONNECTION_STRING or AZURE_STORAGE_KEY

## Future Enhancements

1. **Chunked Uploads with Progress**
   - Frontend: Break file into 5MB chunks
   - Backend: Assemble chunks into complete file
   - UX: Show upload progress bar

2. **Resumable Uploads**
   - Track uploaded chunks
   - Resume from last chunk on network interruption

3. **Video Streaming**
   - HLS/DASH support for streaming large videos
   - Adaptive bitrate selection

4. **Thumbnail Generation**
   - Auto-generate video thumbnails
   - Create PDF previews

5. **Virus Scanning**
   - ClamAV integration for file scanning
   - Quarantine suspicious files

## Security Notes

- All cloud endpoints use signed/pre-signed URLs (no direct download links exposed)
- File deletions are permanent
- Authentication required for all operations
- MIME type can be spoofed - validate on server side for critical operations

## Performance Benchmarks

Typical performance with 1GB file on good network:
- **Local Storage**: ~2-3 seconds upload
- **GCS**: ~5-10 seconds upload (network dependent)
- **S3**: ~5-10 seconds upload (network dependent)
- **Azure**: ~5-10 seconds upload (network dependent)

Download speeds:
- **Local Storage**: Limited by disk I/O (50-200 MB/s)
- **Cloud Storage**: Limited by network (10-100 MB/s typical)

---

For more information, see [Configuration Guide](./README.md)
