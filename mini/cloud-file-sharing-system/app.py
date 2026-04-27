import os
import uuid
import io
import random
import smtplib
import time
from datetime import datetime
from email.message import EmailMessage

from dotenv import load_dotenv
from flask import Flask, request, redirect, url_for, flash, abort, send_from_directory, render_template, session, send_file
from flask import jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import synonym
from flask_login import (
    LoginManager, UserMixin,
    login_user, login_required,
    logout_user, current_user
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import mimetypes

# Optional cloud storage imports
try:
    from google.cloud import storage
except ImportError:
    storage = None  # type: ignore[assignment]

try:
    import boto3  # type: ignore[import-not-found]
except ImportError:
    boto3 = None  # type: ignore[assignment]

try:
    from azure.storage.blob import BlobServiceClient  # type: ignore[import-not-found]
except ImportError:
    BlobServiceClient = None  # type: ignore[assignment]

# -------------------------------------------------
# App Configuration
# -------------------------------------------------
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

load_dotenv()

app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.getenv("SECRET_KEY", "change_this_for_production"),
    SQLALCHEMY_DATABASE_URI="sqlite:///" + os.path.join(BASE_DIR, "cloud.db"),
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    UPLOAD_FOLDER=UPLOAD_FOLDER,
    MAX_CONTENT_LENGTH=1 * 1024 * 1024 * 1024  # 1 GB
)

# -------------------------------------------------
# Environment Variables
# -------------------------------------------------
SMTP_SERVER   = os.getenv("SMTP_SERVER")
SMTP_PORT     = int(os.getenv("SMTP_PORT", "587")) if os.getenv("SMTP_PORT") else None
SMTP_USER     = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

# ✅ Backblaze B2 (PRIMARY storage) — reads from your .env
B2_KEY_ID   = os.getenv("B2_KEY_ID")    # applicationKeyId from Backblaze
B2_APP_KEY  = os.getenv("B2_APP_KEY")   # applicationKey from Backblaze
B2_BUCKET   = os.getenv("B2_BUCKET")    # your bucket name e.g. my-cloud-app
B2_ENDPOINT = os.getenv("B2_ENDPOINT")  # e.g. https://s3.us-east-005.backblazeb2.com

# Legacy backends (kept for compatibility)
GCS_BUCKET         = os.getenv("GCS_BUCKET")
AWS_BUCKET         = os.getenv("AWS_BUCKET")
AWS_REGION         = os.getenv("AWS_REGION", "us-east-1")
AWS_ENDPOINT_URL   = os.getenv("AWS_ENDPOINT_URL")
AZURE_CONTAINER    = os.getenv("AZURE_CONTAINER")
AZURE_ACCOUNT_NAME = os.getenv("AZURE_ACCOUNT_NAME")
STORAGE_TYPE       = os.getenv("STORAGE_TYPE", "local")

# -------------------------------------------------
# Initialize Storage Clients
# -------------------------------------------------
b2_client      = None  # Backblaze B2 (PRIMARY)
storage_client = None  # GCS legacy
s3_client      = None  # AWS S3 legacy
azure_client   = None  # Azure legacy
bucket         = None  # GCS bucket object

# --- ✅ Backblaze B2 ---
if B2_KEY_ID and B2_APP_KEY and B2_BUCKET and B2_ENDPOINT:
    try:
        if boto3:
            # Extract region from endpoint e.g. "us-east-005" from "https://s3.us-east-005.backblazeb2.com"
            region = B2_ENDPOINT.replace("https://s3.", "").replace(".backblazeb2.com", "")
            b2_client = boto3.client(
                's3',
                endpoint_url=B2_ENDPOINT,
                aws_access_key_id=B2_KEY_ID,
                aws_secret_access_key=B2_APP_KEY,
                region_name=region
            )
            app.logger.info("✅ Backblaze B2 client initialized")
        else:
            app.logger.warning("boto3 not installed — run: pip install boto3")
    except Exception as e:
        app.logger.warning(f"B2 initialization failed: {e}")

# --- Legacy GCS ---
elif STORAGE_TYPE == "gcs" and GCS_BUCKET:
    try:
        if storage:
            storage_client = storage.Client()
            bucket = storage_client.bucket(GCS_BUCKET)
    except Exception as e:
        app.logger.warning(f"GCS initialization failed: {e}")

# --- Legacy AWS S3 ---
elif STORAGE_TYPE == "s3" and AWS_BUCKET:
    try:
        if boto3:
            s3_kwargs = {'region_name': AWS_REGION}
            if AWS_ENDPOINT_URL:
                s3_kwargs['endpoint_url'] = AWS_ENDPOINT_URL
            s3_client = boto3.client('s3', **s3_kwargs)
    except Exception as e:
        app.logger.warning(f"AWS S3 initialization failed: {e}")

# --- Legacy Azure ---
elif STORAGE_TYPE == "azure" and AZURE_CONTAINER and AZURE_ACCOUNT_NAME:
    try:
        if BlobServiceClient:
            connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
            if connection_string:
                azure_client = BlobServiceClient.from_connection_string(connection_string)
            else:
                azure_client = BlobServiceClient(
                    account_url=f"https://{AZURE_ACCOUNT_NAME}.blob.core.windows.net",
                    credential=os.getenv("AZURE_STORAGE_KEY")
                )
    except Exception as e:
        app.logger.warning(f"Azure initialization failed: {e}")

ALLOWED_EXTENSIONS = None

# -------------------------------------------------
# Extensions
# -------------------------------------------------
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"

# -------------------------------------------------
# Database Models
# -------------------------------------------------
class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id            = db.Column(db.Integer, primary_key=True)
    name          = db.Column(db.String(120), nullable=False)
    email         = db.Column(db.String(200), unique=True, nullable=False, index=True)
    password      = db.Column('password', db.String(256), nullable=True)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
    files         = db.relationship("File", backref="owner", lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        try:
            self.password = self.password_hash
        except Exception:
            pass

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class File(db.Model):
    __tablename__  = 'files'
    id             = db.Column(db.Integer, primary_key=True)
    stored_name    = db.Column('filename', db.String(300), nullable=False)
    original_name  = db.Column('original_name', db.String(300), nullable=True)
    uploaded_at    = db.Column('uploaded_at', db.DateTime, default=datetime.utcnow)
    file_size      = db.Column(db.Integer, default=0)
    mime_type      = db.Column(db.String(100), default='application/octet-stream')
    duration       = db.Column(db.Float, nullable=True)
    download_count = db.Column('downloads', db.Integer, default=0)
    user_id        = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    @property
    def downloads(self):
        return getattr(self, 'download_count', 0)

    @downloads.setter
    def downloads(self, value):
        try:
            object.__setattr__(self, 'download_count', value)
        except Exception:
            pass


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# -------------------------------------------------
# Utility Functions
# -------------------------------------------------
def allowed_file(filename):
    return filename and filename != ""


def generate_unique_filename(filename):
    safe_name = secure_filename(filename)
    return f"{uuid.uuid4().hex}_{safe_name}"


def safe_remove(path, retries=5, delay=0.2):
    for i in range(retries):
        try:
            if os.path.exists(path):
                os.remove(path)
            return True
        except PermissionError:
            time.sleep(delay)
    return False


def human_readable_size(num, suffix='B'):
    if num is None:
        return 'Unknown'
    num = float(num)
    for unit in ['', 'K', 'M', 'G', 'T', 'P']:
        if abs(num) < 1024.0:
            if unit == '':
                return f"{int(num)} {suffix}"
            return f"{num:3.1f} {unit}{suffix}"
        num /= 1024.0
    return f"{num:.1f} Y{suffix}"


def get_media_duration(file_path):
    try:
        import subprocess
        result = subprocess.run(
            ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
             '-of', 'default=noprint_wrappers=1:nokey=1:noprint_wrappers=1',
             file_path],
            capture_output=True, text=True, timeout=10
        )
        if result.stdout.strip():
            return float(result.stdout.strip())
    except (subprocess.TimeoutExpired, FileNotFoundError, ValueError):
        pass
    return None


# -------------------------------------------------
# ✅ Cloud Storage Functions (B2 primary, others fallback)
# -------------------------------------------------

def upload_to_cloud(file_obj, file_name, content_type):
    """Upload to Backblaze B2. Falls back to legacy backends, then local."""

    # ── Backblaze B2 ────────────────────────────────────────────────────
    if b2_client and B2_BUCKET:
        try:
            file_obj.seek(0)
            data = file_obj.read()
            file_size = len(data)
            b2_client.put_object(
                Bucket=B2_BUCKET,
                Key=file_name,
                Body=data,
                ContentType=content_type
            )
            app.logger.info(f"✅ Uploaded to B2: {file_name} ({human_readable_size(file_size)})")
            return True, file_size
        except Exception as e:
            app.logger.warning(f"B2 upload failed, falling back to local: {e}")

    # ── Legacy GCS ───────────────────────────────────────────────────────
    if STORAGE_TYPE == "gcs" and storage_client and bucket:
        try:
            file_obj.seek(0)
            blob = bucket.blob(file_name)
            blob.upload_from_file(file_obj, content_type=content_type)
            return True, bucket.blob(file_name).size or 0
        except Exception as e:
            app.logger.warning(f"GCS upload failed: {e}")

    # ── Legacy AWS S3 ────────────────────────────────────────────────────
    elif STORAGE_TYPE == "s3" and s3_client and AWS_BUCKET:
        try:
            file_obj.seek(0)
            s3_client.upload_fileobj(file_obj, AWS_BUCKET, file_name, ExtraArgs={'ContentType': content_type})
            resp = s3_client.head_object(Bucket=AWS_BUCKET, Key=file_name)
            return True, resp['ContentLength']
        except Exception as e:
            app.logger.warning(f"S3 upload failed: {e}")

    # ── Legacy Azure ─────────────────────────────────────────────────────
    elif STORAGE_TYPE == "azure" and azure_client and AZURE_CONTAINER:
        try:
            file_obj.seek(0)
            blob_client = azure_client.get_blob_client(container=AZURE_CONTAINER, blob=file_name)
            blob_client.upload_blob(file_obj, overwrite=True)
            props = blob_client.get_blob_properties()
            return True, props.size or 0
        except Exception as e:
            app.logger.warning(f"Azure upload failed: {e}")

    return False, 0


def download_from_cloud(file_name, original_name=None):
    """Generate a presigned download URL from B2 or fallback backends."""
    disp = f'attachment; filename="{original_name or file_name}"'

    # ── Backblaze B2 ────────────────────────────────────────────────────
    if b2_client and B2_BUCKET:
        try:
            url = b2_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': B2_BUCKET, 'Key': file_name, 'ResponseContentDisposition': disp},
                ExpiresIn=3600
            )
            return redirect(url)
        except Exception as e:
            app.logger.warning(f"B2 download failed: {e}")

    # ── Legacy backends ──────────────────────────────────────────────────
    try:
        if STORAGE_TYPE == "gcs" and storage_client and bucket:
            url = bucket.blob(file_name).generate_signed_url(
                expiration=3600, version='v4', method='GET', response_disposition=disp)
            return redirect(url)
        elif STORAGE_TYPE == "s3" and s3_client and AWS_BUCKET:
            url = s3_client.generate_presigned_url(
                'get_object', Params={'Bucket': AWS_BUCKET, 'Key': file_name}, ExpiresIn=3600)
            return redirect(url)
        elif STORAGE_TYPE == "azure" and azure_client and AZURE_CONTAINER:
            return redirect(azure_client.get_blob_client(
                container=AZURE_CONTAINER, blob=file_name).url)
    except Exception as e:
        app.logger.warning(f"Legacy download failed: {e}")

    return None


def delete_from_cloud(file_name):
    """Delete from B2 or fallback backends."""

    # ── Backblaze B2 ────────────────────────────────────────────────────
    if b2_client and B2_BUCKET:
        try:
            b2_client.delete_object(Bucket=B2_BUCKET, Key=file_name)
            app.logger.info(f"Deleted from B2: {file_name}")
            return True
        except Exception as e:
            app.logger.warning(f"B2 delete failed: {e}")

    # ── Legacy backends ──────────────────────────────────────────────────
    try:
        if STORAGE_TYPE == "gcs" and storage_client and bucket:
            bucket.blob(file_name).delete()
            return True
        elif STORAGE_TYPE == "s3" and s3_client and AWS_BUCKET:
            s3_client.delete_object(Bucket=AWS_BUCKET, Key=file_name)
            return True
        elif STORAGE_TYPE == "azure" and azure_client and AZURE_CONTAINER:
            azure_client.get_blob_client(container=AZURE_CONTAINER, blob=file_name).delete_blob()
            return True
    except Exception as e:
        app.logger.warning(f"Legacy delete failed: {e}")

    return False


def send_otp_email(to_email, code):
    if not SMTP_SERVER or not SMTP_USER or not SMTP_PASSWORD:
        app.logger.warning("SMTP not fully configured; skipping OTP email")
        return False

    msg = EmailMessage()
    msg["Subject"] = "Your Cloud App OTP"
    msg["From"]    = SMTP_USER
    msg["To"]      = to_email
    msg.set_content(f"Your login code is: {code}\nIt will expire in 5 minutes.")

    try:
        if SMTP_PORT == 465:
            server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT)
        else:
            server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
            server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        app.logger.exception("Failed to send OTP email")
        return False


# -------------------------------------------------
# Routes
# -------------------------------------------------
@app.route("/")
def index():
    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")
    data = request.form
    if not all(k in data for k in ("name", "email", "password")):
        abort(400)
    if User.query.filter_by(email=data["email"]).first():
        return "Email already exists", 409
    user = User(name=data["name"], email=data["email"])
    user.set_password(data["password"])
    db.session.add(user)
    db.session.commit()
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")
    data = request.form
    user = User.query.filter_by(email=data.get("email")).first()
    if not user or not user.check_password(data.get("password", "")):
        return "Invalid credentials", 401
    code = f"{random.randint(100000, 999999)}"
    session['otp']         = code
    session['otp_expires'] = time.time() + 300
    session['otp_user_id'] = user.id
    sent = send_otp_email(user.email, code)
    if not sent:
        app.logger.warning('OTP not sent; check SMTP configuration')
    return redirect(url_for('verify'))


@app.route('/verify', methods=['GET', 'POST'])
def verify():
    if request.method == 'GET':
        user_email = None
        if 'otp_user_id' in session:
            u = User.query.get(int(session['otp_user_id']))
            if u:
                user_email = u.email

        def mask_email(e):
            if not e or '@' not in e:
                return 'your email'
            name, domain = e.split('@', 1)
            n   = name[0] + ('*' * max(1, len(name) - 2)) + (name[-1] if len(name) > 1 else '')
            d   = domain.split('.')
            d0  = d[0]
            d0m = d0[0] + ('*' * max(1, len(d0) - 2)) + (d0[-1] if len(d0) > 1 else '')
            rest = ('.' + '.'.join(d[1:])) if len(d) > 1 else ''
            return f"{n}@{d0m}{rest}"

        return render_template('verify.html', masked_email=mask_email(user_email), cooldown_seconds=30)

    code = request.form.get('otp', '').strip()
    if 'otp' not in session or 'otp_user_id' not in session:
        return 'No OTP pending. Please login again.', 400
    if time.time() > session.get('otp_expires', 0):
        session.pop('otp', None)
        session.pop('otp_user_id', None)
        session.pop('otp_expires', None)
        return 'OTP expired. Please login again.', 400
    if code != session.get('otp'):
        return 'Invalid OTP', 401
    user = User.query.get(int(session['otp_user_id']))
    if not user:
        return 'User not found', 404
    login_user(user)
    session.pop('otp', None)
    session.pop('otp_user_id', None)
    session.pop('otp_expires', None)
    return redirect(url_for('dashboard'))


@app.route('/resend_otp', methods=['POST'])
def resend_otp():
    if 'otp_user_id' not in session:
        return 'No pending OTP to resend', 400
    last     = session.get('otp_last_sent', 0)
    now      = time.time()
    cooldown = 30
    if now - last < cooldown:
        return f'Wait {int(cooldown - (now - last))}s before resending', 429
    user = User.query.get(int(session['otp_user_id']))
    if not user:
        return 'User not found', 404
    code = f"{random.randint(100000, 999999)}"
    session['otp']           = code
    session['otp_expires']   = time.time() + 300
    session['otp_last_sent'] = now
    sent = send_otp_email(user.email, code)
    if not sent:
        return 'Failed to send OTP (check SMTP config)', 500
    return 'OTP resent', 200


@app.route('/preview/<int:file_id>')
@login_required
def preview(file_id):
    f         = File.query.filter_by(id=file_id, user_id=current_user.id).first_or_404()
    orig_name = getattr(f, 'original_name', f.stored_name)
    ext       = orig_name.lower().rsplit('.', 1)[-1]
    if ext not in ('png', 'jpg', 'jpeg', 'gif'):
        abort(404)
    if b2_client and B2_BUCKET:
        try:
            url = b2_client.generate_presigned_url(
                'get_object', Params={'Bucket': B2_BUCKET, 'Key': f.stored_name}, ExpiresIn=3600)
            return redirect(url)
        except Exception:
            pass
    if STORAGE_TYPE == "gcs" and storage_client and bucket:
        try:
            url = bucket.blob(f.stored_name).generate_signed_url(expiration=3600, version='v4', method='GET')
            return redirect(url)
        except Exception:
            pass
    elif STORAGE_TYPE == "s3" and s3_client and AWS_BUCKET:
        try:
            url = s3_client.generate_presigned_url('get_object',
                Params={'Bucket': AWS_BUCKET, 'Key': f.stored_name}, ExpiresIn=3600)
            return redirect(url)
        except Exception:
            pass
    elif STORAGE_TYPE == "azure" and azure_client and AZURE_CONTAINER:
        try:
            return redirect(azure_client.get_blob_client(
                container=AZURE_CONTAINER, blob=f.stored_name).url)
        except Exception:
            pass
    return send_from_directory(app.config['UPLOAD_FOLDER'], f.stored_name)


@app.route("/dashboard", methods=["GET", "POST"])
@login_required
def dashboard():
    try:
        if request.method == "POST":
            file = request.files.get("file")
            if not file or file.filename == "":
                abort(400)
            if not allowed_file(file.filename):
                return "File type not allowed", 415

            unique_name = generate_unique_filename(file.filename)
            mime_type   = file.content_type or 'application/octet-stream'
            if not mime_type or mime_type == 'application/octet-stream':
                guessed_type, _ = mimetypes.guess_type(file.filename)
                if guessed_type:
                    mime_type = guessed_type

            file_size = 0
            temp_path = None
            cloud_success, cloud_size = upload_to_cloud(file.stream, unique_name, mime_type)

            if cloud_success:
                file_size = cloud_size
            else:
                temp_path = os.path.join(app.config["UPLOAD_FOLDER"], unique_name)
                file.seek(0)
                file.save(temp_path)
                file_size = os.path.getsize(temp_path)

            duration = None
            if mime_type.startswith(('audio/', 'video/')):
                if temp_path and os.path.exists(temp_path):
                    duration = get_media_duration(temp_path)

            record = File(
                stored_name   = unique_name,
                original_name = file.filename,
                user_id       = current_user.id,
                file_size     = file_size,
                mime_type     = mime_type,
                duration      = duration
            )
            db.session.add(record)
            db.session.commit()

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                is_image = file.filename.lower().rsplit('.', 1)[-1] in ('png', 'jpg', 'jpeg', 'gif')
                return jsonify({
                    'status': 'ok',
                    'file': {
                        'id': record.id, 'name': file.filename,
                        'is_image': is_image, 'size': file_size,
                        'size_human': human_readable_size(file_size),
                        'mime_type': mime_type, 'duration': duration
                    }
                }), 201

            return redirect(url_for("dashboard"))

        files = File.query.filter_by(user_id=current_user.id).order_by(File.uploaded_at.desc()).all()

        def file_info(f):
            name     = getattr(f, 'original_name', f.stored_name)
            is_image = name.lower().rsplit('.', 1)[-1] in ('png', 'jpg', 'jpeg', 'gif')
            size     = getattr(f, 'file_size', 0) or 0
            if size == 0:
                try:
                    path = os.path.join(app.config['UPLOAD_FOLDER'], f.stored_name)
                    if os.path.exists(path):
                        size = os.path.getsize(path)
                except Exception:
                    pass
            return {
                'id': f.id, 'name': name, 'is_image': is_image,
                'size': size, 'size_human': human_readable_size(size),
                'mime_type': getattr(f, 'mime_type', 'application/octet-stream'),
                'duration': getattr(f, 'duration', None)
            }

        info_files = [file_info(f) for f in files]

        # Calculate storage usage
        total_bytes = sum(getattr(f, "file_size", 0) or 0 for f in files)
        MAX_STORAGE_GB = 10
        MAX_STORAGE_BYTES = MAX_STORAGE_GB * 1024 * 1024 * 1024
        usage_percent = min(100, int((total_bytes / MAX_STORAGE_BYTES) * 100)) if MAX_STORAGE_BYTES > 0 else 0
        total_usage_human = human_readable_size(total_bytes)

        return render_template(
            "dashboard.html",
            name=current_user.name,
            files=info_files,
            usage_percent=usage_percent,
            total_usage=total_usage_human,
        )

    except Exception as e:
        app.logger.exception(f"Dashboard error: {e}")
        return f"Error: {str(e)}", 500


@app.route("/download/<filename>")
@login_required
def download_by_name(filename):
    file = File.query.filter(
        ((File.original_name == filename) | (File.stored_name == filename)) &
        (File.user_id == current_user.id)
    ).first_or_404()
    file.downloads = (file.downloads or 0) + 1
    db.session.commit()
    cloud_response = download_from_cloud(file.stored_name, getattr(file, 'original_name', file.stored_name))
    if cloud_response:
        return cloud_response
    return send_from_directory(app.config["UPLOAD_FOLDER"], file.stored_name,
                               as_attachment=True,
                               download_name=getattr(file, 'original_name', file.stored_name))


@app.route("/delete/<int:file_id>/<filename>")
@login_required
def delete_by_name(file_id, filename):
    file = File.query.filter_by(id=file_id, user_id=current_user.id).first_or_404()
    delete_from_cloud(file.stored_name)
    path = os.path.join(app.config["UPLOAD_FOLDER"], file.stored_name)
    if os.path.exists(path):
        safe_remove(path)
    db.session.delete(file)
    db.session.commit()
    return redirect(url_for("dashboard"))


@app.route("/download/<int:file_id>")
@login_required
def download(file_id):
    file = File.query.filter_by(id=file_id, user_id=current_user.id).first_or_404()
    file.downloads = (file.downloads or 0) + 1
    db.session.commit()
    cloud_response = download_from_cloud(file.stored_name, getattr(file, 'original_name', file.stored_name))
    if cloud_response:
        return cloud_response
    return send_from_directory(app.config["UPLOAD_FOLDER"], file.stored_name,
                               as_attachment=True,
                               download_name=getattr(file, 'original_name', file.stored_name))


@app.route("/delete/<int:file_id>", methods=["DELETE"])
@login_required
def delete(file_id):
    file = File.query.filter_by(id=file_id, user_id=current_user.id).first_or_404()
    delete_from_cloud(file.stored_name)
    path = os.path.join(app.config["UPLOAD_FOLDER"], file.stored_name)
    if os.path.exists(path):
        safe_remove(path)
    db.session.delete(file)
    db.session.commit()
    return "File deleted", 200


@app.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        password = request.form.get("password", "").strip()
        if name:
            current_user.name = name
        if password:
            current_user.set_password(password)
        db.session.commit()
        flash("Settings updated successfully!", "success")
        return redirect(url_for("settings"))

    files = File.query.filter_by(user_id=current_user.id).order_by(File.uploaded_at.desc()).all()

    def file_info(f):
        name = getattr(f, 'original_name', f.stored_name)
        is_image = name.lower().rsplit('.', 1)[-1] in ('png', 'jpg', 'jpeg', 'gif')
        size = getattr(f, 'file_size', 0) or 0
        if size == 0:
            try:
                path = os.path.join(app.config['UPLOAD_FOLDER'], f.stored_name)
                if os.path.exists(path):
                    size = os.path.getsize(path)
            except Exception:
                pass
        return {
            'id': f.id, 'name': name, 'is_image': is_image,
            'size': size, 'size_human': human_readable_size(size),
            'mime_type': getattr(f, 'mime_type', 'application/octet-stream'),
            'duration': getattr(f, 'duration', None)
        }

    info_files = [file_info(f) for f in files]

    # Calculate storage usage
    total_bytes = sum(getattr(f, 'file_size', 0) or 0 for f in files)
    limit_bytes = 10 * 1024 * 1024 * 1024  # 10 GB B2 free tier
    usage_percent = min(100, int((total_bytes / limit_bytes) * 100)) if limit_bytes > 0 else 0
    total_bytes_human = human_readable_size(total_bytes)

    return render_template(
        "settings.html",
        name=current_user.name,
        email=current_user.email,
        files=info_files,
        usage_percent=usage_percent,
        total_bytes_human=total_bytes_human
    )


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return "Logged out successfully", 200


@app.route('/test-smtp', methods=['POST'])
def test_smtp():
    to = request.form.get('to') or SMTP_USER
    if not to:
        return jsonify({'ok': False, 'error': 'No recipient'}), 400
    msg = EmailMessage()
    msg['Subject'] = 'Cloud App SMTP test'
    msg['From']    = SMTP_USER or to
    msg['To']      = to
    msg.set_content('This is a test email from Cloud App.')
    try:
        if not all([SMTP_SERVER, SMTP_USER, SMTP_PASSWORD, SMTP_PORT]):
            return jsonify({'ok': False, 'error': 'SMTP not fully configured'}), 400
        if SMTP_PORT == 465:
            server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, timeout=15)
        else:
            server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=15)
            server.ehlo()
            server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
        return jsonify({'ok': True, 'message': f'Test email sent to {to}'}), 200
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@app.route('/test-b2', methods=['POST'])
def test_b2():
    """Test Backblaze B2 connection."""
    if not b2_client or not B2_BUCKET:
        return jsonify({'ok': False, 'error': 'B2 not configured. Check B2_KEY_ID, B2_APP_KEY, B2_BUCKET, B2_ENDPOINT in .env'}), 400
    test_key = f"test_{int(time.time())}.txt"
    try:
        b2_client.put_object(Bucket=B2_BUCKET, Key=test_key, Body=b'B2 test OK')
        b2_client.delete_object(Bucket=B2_BUCKET, Key=test_key)
        return jsonify({'ok': True, 'message': '✅ Backblaze B2 is working!', 'bucket': B2_BUCKET}), 200
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


# Alias so old /test-gcs links still work
@app.route('/test-gcs', methods=['POST'])
def test_gcs():
    return test_b2()


# -------------------------------------------------
# App Runner
# -------------------------------------------------
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=5000, debug=False)
