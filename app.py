import os
import uuid
from functools import wraps

from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import (
    LoginManager,
    login_user,
    logout_user,
    login_required,
    current_user,
)
from werkzeug.exceptions import RequestEntityTooLarge

from config import Config
from models import db, User, Post, Like, Comment


app = Flask(__name__)
app.config.from_object(Config)

app.config["UPLOAD_FOLDER_POSTS"] = os.path.join(
    app.root_path,
    "static",
    "uploads",
    "posts"
)

app.config["UPLOAD_FOLDER_AVATARS"] = os.path.join(
    app.root_path,
    "static",
    "uploads",
    "avatars"
)

app.config["UPLOAD_FOLDER_COVERS"] = os.path.join(
    app.root_path,
    "static",
    "uploads",
    "covers"
)

app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024

ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"
login_manager.login_message = "من فضلك سجّل الدخول أولًا للوصول لهذه الصفحة."
login_manager.login_message_category = "warning"


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def allowed_image(filename):
    if "." not in filename:
        return False

    extension = filename.rsplit(".", 1)[1].lower()
    return extension in ALLOWED_IMAGE_EXTENSIONS


def save_post_image(file):
    if not file or file.filename == "":
        return None

    if "." not in file.filename:
        return None

    if not allowed_image(file.filename):
        return None

    extension = file.filename.rsplit(".", 1)[1].lower()
    unique_filename = f"{uuid.uuid4().hex}.{extension}"

    os.makedirs(app.config["UPLOAD_FOLDER_POSTS"], exist_ok=True)

    file_path = os.path.join(app.config["UPLOAD_FOLDER_POSTS"], unique_filename)
    file.save(file_path)

    return unique_filename


def delete_post_image(filename):
    if not filename:
        return

    file_path = os.path.join(app.config["UPLOAD_FOLDER_POSTS"], filename)

    if os.path.exists(file_path):
        os.remove(file_path)


def save_user_image(file, folder_key):
    if not file or file.filename == "":
        return None

    if "." not in file.filename:
        return None

    if not allowed_image(file.filename):
        return None

    extension = file.filename.rsplit(".", 1)[1].lower()
    unique_filename = f"{uuid.uuid4().hex}.{extension}"

    folder_path = app.config[folder_key]
    os.makedirs(folder_path, exist_ok=True)

    file_path = os.path.join(folder_path, unique_filename)
    file.save(file_path)

    return unique_filename


def delete_user_image(filename, folder_key):
    if not filename:
        return

    file_path = os.path.join(app.config[folder_key], filename)

    if os.path.exists(file_path):
        os.remove(file_path)


def approved_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("login"))

        if current_user.is_blocked:
            logout_user()
            flash("تم إيقاف هذا الحساب. يرجى التواصل مع إدارة الأكاديمية.", "danger")
            return redirect(url_for("login"))

        if current_user.is_pending:
            return redirect(url_for("pending"))

        return view_func(*args, **kwargs)

    return wrapper


def admin_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("login"))

        if not current_user.is_admin:
            flash("ليس لديك صلاحية للوصول لهذه الصفحة.", "danger")
            return redirect(url_for("feed"))

        return view_func(*args, **kwargs)

    return wrapper


def create_default_admin():
    admin_email = os.getenv("DEFAULT_ADMIN_EMAIL", "admin@baytalmosawer.local")
    admin_username = os.getenv("DEFAULT_ADMIN_USERNAME", "admin")
    admin_password = os.getenv("DEFAULT_ADMIN_PASSWORD", "Admin@12345")
    admin_name = os.getenv("DEFAULT_ADMIN_NAME", "مدير النظام")

    existing_admin = User.query.filter_by(role="admin").first()

    if existing_admin:
        return

    admin = User(
        name=admin_name,
        username=admin_username,
        email=admin_email,
        role="admin",
        status="approved",
        city="جدة",
        specialty="إدارة المجتمع",
        bio="الحساب الإداري الرئيسي لمجتمع بيت المصور.",
    )
    admin.set_password(admin_password)

    db.session.add(admin)
    db.session.commit()

    print("=" * 70)
    print("Default admin account created successfully")
    print(f"Email: {admin_email}")
    print(f"Password: {admin_password}")
    print("=" * 70)


def admin_count():
    return User.query.filter_by(role="admin").count()


def get_user_or_404(user_id):
    return User.query.get_or_404(user_id)


def prevent_last_admin_action(user):
    if user.role == "admin" and admin_count() <= 1:
        return True

    return False


with app.app_context():
    os.makedirs(app.config["UPLOAD_FOLDER_POSTS"], exist_ok=True)
    os.makedirs(app.config["UPLOAD_FOLDER_AVATARS"], exist_ok=True)
    os.makedirs(app.config["UPLOAD_FOLDER_COVERS"], exist_ok=True)

    db.create_all()
    create_default_admin()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/health")
def health():
    return {
        "status": "ok",
        "message": "Bayt Almosawer Community is running",
        "database": "connected",
    }


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("feed"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        username = request.form.get("username", "").strip().lower()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()
        confirm_password = request.form.get("confirm_password", "").strip()
        city = request.form.get("city", "").strip()
        specialty = request.form.get("specialty", "").strip()

        if not name or not username or not email or not password:
            flash("من فضلك أكمل جميع الحقول المطلوبة.", "danger")
            return render_template("register.html")

        if len(username) < 3:
            flash("اسم المستخدم يجب ألا يقل عن 3 أحرف.", "danger")
            return render_template("register.html")

        if len(password) < 6:
            flash("كلمة المرور يجب ألا تقل عن 6 أحرف.", "danger")
            return render_template("register.html")

        if password != confirm_password:
            flash("كلمة المرور وتأكيد كلمة المرور غير متطابقين.", "danger")
            return render_template("register.html")

        username_exists = User.query.filter_by(username=username).first()
        if username_exists:
            flash("اسم المستخدم مستخدم بالفعل. اختر اسمًا آخر.", "danger")
            return render_template("register.html")

        email_exists = User.query.filter_by(email=email).first()
        if email_exists:
            flash("البريد الإلكتروني مستخدم بالفعل.", "danger")
            return render_template("register.html")

        user = User(
            name=name,
            username=username,
            email=email,
            role="member",
            status="pending",
            city=city,
            specialty=specialty,
        )
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        flash("تم إنشاء الحساب بنجاح. حسابك الآن بانتظار موافقة الإدارة.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("feed"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()

        if not email or not password:
            flash("من فضلك أدخل البريد الإلكتروني وكلمة المرور.", "danger")
            return render_template("login.html")

        user = User.query.filter_by(email=email).first()

        if not user or not user.check_password(password):
            flash("بيانات الدخول غير صحيحة.", "danger")
            return render_template("login.html")

        if user.is_blocked:
            flash("هذا الحساب موقوف. يرجى التواصل مع إدارة الأكاديمية.", "danger")
            return render_template("login.html")

        login_user(user)

        if user.is_pending:
            return redirect(url_for("pending"))

        if user.is_admin:
            return redirect(url_for("admin_dashboard"))

        return redirect(url_for("feed"))

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("تم تسجيل الخروج بنجاح.", "success")
    return redirect(url_for("index"))


@app.route("/pending")
@login_required
def pending():
    if current_user.is_approved:
        return redirect(url_for("feed"))

    if current_user.is_blocked:
        logout_user()
        flash("تم إيقاف هذا الحساب.", "danger")
        return redirect(url_for("login"))

    return render_template("pending.html")


@app.route("/feed")
@login_required
@approved_required
def feed():
    posts = Post.query.order_by(Post.is_pinned.desc(), Post.created_at.desc()).all()

    liked_post_ids = {
        like.post_id for like in Like.query.filter_by(user_id=current_user.id).all()
    }

    return render_template(
        "feed.html",
        posts=posts,
        liked_post_ids=liked_post_ids,
    )


@app.route("/posts/new", methods=["GET", "POST"])
@login_required
@approved_required
def new_post():
    if request.method == "POST":
        content = request.form.get("content", "").strip()
        image = request.files.get("image")

        if not content:
            flash("اكتب نص المنشور أولًا.", "danger")
            return render_template("new_post.html")

        image_filename = None

        if image and image.filename:
            if not allowed_image(image.filename):
                flash("صيغة الصورة غير مدعومة. الصيغ المسموحة: PNG, JPG, JPEG, GIF, WEBP", "danger")
                return render_template("new_post.html")

            image_filename = save_post_image(image)

            if not image_filename:
                flash("حدث خطأ أثناء رفع الصورة. حاول مرة أخرى.", "danger")
                return render_template("new_post.html")

        post = Post(
            user_id=current_user.id,
            content=content,
            image_filename=image_filename,
        )

        db.session.add(post)
        db.session.commit()

        flash("تم نشر المنشور بنجاح.", "success")
        return redirect(url_for("feed"))

    return render_template("new_post.html")


@app.route("/posts/<int:post_id>")
@login_required
@approved_required
def post_detail(post_id):
    post = Post.query.get_or_404(post_id)

    liked_post_ids = {
        like.post_id for like in Like.query.filter_by(user_id=current_user.id).all()
    }

    return render_template(
        "post_detail.html",
        post=post,
        liked_post_ids=liked_post_ids,
    )


@app.route("/posts/<int:post_id>/delete", methods=["POST"])
@login_required
@approved_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)

    if post.user_id != current_user.id and not current_user.is_admin:
        flash("ليس لديك صلاحية لحذف هذا المنشور.", "danger")
        return redirect(url_for("feed"))

    delete_post_image(post.image_filename)

    db.session.delete(post)
    db.session.commit()

    flash("تم حذف المنشور بنجاح.", "success")
    return redirect(url_for("feed"))


@app.route("/posts/<int:post_id>/like", methods=["POST"])
@login_required
@approved_required
def toggle_like(post_id):
    post = Post.query.get_or_404(post_id)

    existing_like = Like.query.filter_by(
        user_id=current_user.id,
        post_id=post.id,
    ).first()

    if existing_like:
        db.session.delete(existing_like)
        db.session.commit()
        flash("تم إلغاء الإعجاب.", "info")
    else:
        new_like = Like(
            user_id=current_user.id,
            post_id=post.id,
        )
        db.session.add(new_like)
        db.session.commit()
        flash("تم تسجيل الإعجاب.", "success")

    next_url = request.form.get("next") or url_for("feed")
    return redirect(next_url)


@app.route("/posts/<int:post_id>/comments", methods=["POST"])
@login_required
@approved_required
def add_comment(post_id):
    post = Post.query.get_or_404(post_id)
    content = request.form.get("content", "").strip()

    if not content:
        flash("لا يمكن إضافة تعليق فارغ.", "danger")
        return redirect(url_for("post_detail", post_id=post.id))

    if len(content) > 1000:
        flash("التعليق طويل جدًا. الحد الأقصى 1000 حرف.", "danger")
        return redirect(url_for("post_detail", post_id=post.id))

    comment = Comment(
        user_id=current_user.id,
        post_id=post.id,
        content=content,
    )

    db.session.add(comment)
    db.session.commit()

    flash("تم إضافة التعليق بنجاح.", "success")
    return redirect(url_for("post_detail", post_id=post.id))


@app.route("/profile/<username>")
@login_required
@approved_required
def profile(username):
    user = User.query.filter_by(username=username).first_or_404()

    if user.is_blocked:
        flash("هذا الحساب غير متاح حاليًا.", "danger")
        return redirect(url_for("feed"))

    user_posts = Post.query.filter_by(user_id=user.id).order_by(Post.created_at.desc()).all()

    total_posts = len(user_posts)
    total_likes = sum(post.likes_count for post in user_posts)
    total_comments = sum(post.comments_count for post in user_posts)

    liked_post_ids = {
        like.post_id for like in Like.query.filter_by(user_id=current_user.id).all()
    }

    return render_template(
        "profile.html",
        user=user,
        user_posts=user_posts,
        total_posts=total_posts,
        total_likes=total_likes,
        total_comments=total_comments,
        liked_post_ids=liked_post_ids,
    )


@app.route("/settings/profile", methods=["GET", "POST"])
@login_required
@approved_required
def profile_settings():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        city = request.form.get("city", "").strip()
        specialty = request.form.get("specialty", "").strip()
        bio = request.form.get("bio", "").strip()
        instagram_url = request.form.get("instagram_url", "").strip()
        whatsapp = request.form.get("whatsapp", "").strip()

        avatar_file = request.files.get("avatar")
        cover_file = request.files.get("cover_image")

        if not name:
            flash("الاسم لا يمكن أن يكون فارغًا.", "danger")
            return render_template("profile_settings.html")

        if len(bio) > 700:
            flash("النبذة طويلة جدًا. الحد الأقصى 700 حرف.", "danger")
            return render_template("profile_settings.html")

        if avatar_file and avatar_file.filename:
            if not allowed_image(avatar_file.filename):
                flash("صيغة الصورة الشخصية غير مدعومة. الصيغ المسموحة: PNG, JPG, JPEG, GIF, WEBP", "danger")
                return render_template("profile_settings.html")

            new_avatar = save_user_image(avatar_file, "UPLOAD_FOLDER_AVATARS")

            if not new_avatar:
                flash("حدث خطأ أثناء رفع الصورة الشخصية.", "danger")
                return render_template("profile_settings.html")

            delete_user_image(current_user.avatar, "UPLOAD_FOLDER_AVATARS")
            current_user.avatar = new_avatar

        if cover_file and cover_file.filename:
            if not allowed_image(cover_file.filename):
                flash("صيغة صورة الغلاف غير مدعومة. الصيغ المسموحة: PNG, JPG, JPEG, GIF, WEBP", "danger")
                return render_template("profile_settings.html")

            new_cover = save_user_image(cover_file, "UPLOAD_FOLDER_COVERS")

            if not new_cover:
                flash("حدث خطأ أثناء رفع صورة الغلاف.", "danger")
                return render_template("profile_settings.html")

            delete_user_image(current_user.cover_image, "UPLOAD_FOLDER_COVERS")
            current_user.cover_image = new_cover

        current_user.name = name
        current_user.city = city
        current_user.specialty = specialty
        current_user.bio = bio
        current_user.instagram_url = instagram_url
        current_user.whatsapp = whatsapp

        db.session.commit()

        flash("تم تحديث الملف الشخصي بنجاح.", "success")
        return redirect(url_for("profile", username=current_user.username))

    return render_template("profile_settings.html")


@app.route("/comments/<int:comment_id>/delete", methods=["POST"])
@login_required
@approved_required
def delete_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    post = comment.post

    can_delete = (
        comment.user_id == current_user.id
        or post.user_id == current_user.id
        or current_user.is_admin
    )

    if not can_delete:
        flash("ليس لديك صلاحية لحذف هذا التعليق.", "danger")
        return redirect(url_for("post_detail", post_id=post.id))

    db.session.delete(comment)
    db.session.commit()

    flash("تم حذف التعليق بنجاح.", "success")
    return redirect(url_for("post_detail", post_id=post.id))


@app.route("/admin")
@login_required
@admin_required
def admin_dashboard():
    total_users = User.query.count()
    pending_users = User.query.filter_by(status="pending").count()
    approved_users = User.query.filter_by(status="approved").count()
    blocked_users = User.query.filter_by(status="blocked").count()

    latest_users = User.query.order_by(User.created_at.desc()).limit(8).all()

    return render_template(
        "admin/dashboard.html",
        total_users=total_users,
        pending_users=pending_users,
        approved_users=approved_users,
        blocked_users=blocked_users,
        latest_users=latest_users,
    )


@app.route("/admin/users")
@login_required
@admin_required
def admin_users():
    status_filter = request.args.get("status", "all").strip()
    role_filter = request.args.get("role", "all").strip()
    search_query = request.args.get("q", "").strip()

    users_query = User.query

    if status_filter in ["pending", "approved", "blocked"]:
        users_query = users_query.filter_by(status=status_filter)

    if role_filter in ["admin", "trainer", "member"]:
        users_query = users_query.filter_by(role=role_filter)

    if search_query:
        like_pattern = f"%{search_query}%"
        users_query = users_query.filter(
            db.or_(
                User.name.ilike(like_pattern),
                User.username.ilike(like_pattern),
                User.email.ilike(like_pattern),
                User.city.ilike(like_pattern),
                User.specialty.ilike(like_pattern),
            )
        )

    users = users_query.order_by(User.created_at.desc()).all()

    stats = {
        "total": User.query.count(),
        "pending": User.query.filter_by(status="pending").count(),
        "approved": User.query.filter_by(status="approved").count(),
        "blocked": User.query.filter_by(status="blocked").count(),
        "admins": User.query.filter_by(role="admin").count(),
        "trainers": User.query.filter_by(role="trainer").count(),
        "members": User.query.filter_by(role="member").count(),
    }

    return render_template(
        "admin/users.html",
        users=users,
        stats=stats,
        status_filter=status_filter,
        role_filter=role_filter,
        search_query=search_query,
    )


@app.route("/admin/users/<int:user_id>/approve", methods=["POST"])
@login_required
@admin_required
def admin_approve_user(user_id):
    user = get_user_or_404(user_id)

    if user.status == "approved":
        flash("هذا الحساب مقبول بالفعل.", "info")
        return redirect(url_for("admin_users"))

    user.status = "approved"
    db.session.commit()

    flash(f"تم قبول حساب {user.name} بنجاح.", "success")
    return redirect(url_for("admin_users"))


@app.route("/admin/users/<int:user_id>/block", methods=["POST"])
@login_required
@admin_required
def admin_block_user(user_id):
    user = get_user_or_404(user_id)

    if user.id == current_user.id:
        flash("لا يمكنك إيقاف حسابك الحالي.", "danger")
        return redirect(url_for("admin_users"))

    if prevent_last_admin_action(user):
        flash("لا يمكن إيقاف آخر حساب Admin في النظام.", "danger")
        return redirect(url_for("admin_users"))

    user.status = "blocked"
    db.session.commit()

    flash(f"تم إيقاف حساب {user.name}.", "warning")
    return redirect(url_for("admin_users"))


@app.route("/admin/users/<int:user_id>/reactivate", methods=["POST"])
@login_required
@admin_required
def admin_reactivate_user(user_id):
    user = get_user_or_404(user_id)

    user.status = "approved"
    db.session.commit()

    flash(f"تم إعادة تفعيل حساب {user.name}.", "success")
    return redirect(url_for("admin_users"))


@app.route("/admin/users/<int:user_id>/make-trainer", methods=["POST"])
@login_required
@admin_required
def admin_make_trainer(user_id):
    user = get_user_or_404(user_id)

    if user.role == "admin":
        flash("لا يمكن تحويل حساب Admin إلى مدرب من هذا الزر.", "danger")
        return redirect(url_for("admin_users"))

    user.role = "trainer"
    user.status = "approved"
    db.session.commit()

    flash(f"تم تحويل {user.name} إلى مدرب.", "success")
    return redirect(url_for("admin_users"))


@app.route("/admin/users/<int:user_id>/make-member", methods=["POST"])
@login_required
@admin_required
def admin_make_member(user_id):
    user = get_user_or_404(user_id)

    if user.id == current_user.id:
        flash("لا يمكنك تغيير دور حسابك الحالي من هنا.", "danger")
        return redirect(url_for("admin_users"))

    if prevent_last_admin_action(user):
        flash("لا يمكن تحويل آخر حساب Admin إلى عضو.", "danger")
        return redirect(url_for("admin_users"))

    user.role = "member"
    db.session.commit()

    flash(f"تم تحويل {user.name} إلى عضو.", "success")
    return redirect(url_for("admin_users"))


@app.route("/admin/users/<int:user_id>/make-admin", methods=["POST"])
@login_required
@admin_required
def admin_make_admin(user_id):
    user = get_user_or_404(user_id)

    user.role = "admin"
    user.status = "approved"
    db.session.commit()

    flash(f"تم ترقية {user.name} إلى Admin.", "success")
    return redirect(url_for("admin_users"))


# ============================================================
# Temporary Maintenance Route
# Use once to reset/update the production admin account.
# Disable it by removing RESET_ADMIN_TOKEN from Railway Variables.
# ============================================================

@app.route("/maintenance/reset-admin-password")
def reset_admin_password():
    reset_token = request.args.get("token", "").strip()
    expected_token = os.getenv("RESET_ADMIN_TOKEN", "").strip()

    if not expected_token or reset_token != expected_token:
        return {
            "status": "forbidden",
            "message": "Invalid or missing reset token."
        }, 403

    admin_name = os.getenv("DEFAULT_ADMIN_NAME", "مدير النظام").strip()
    admin_username = os.getenv("DEFAULT_ADMIN_USERNAME", "admin").strip().lower()
    admin_email = os.getenv("DEFAULT_ADMIN_EMAIL", "admin@baytalmosawer.local").strip().lower()
    admin_password = os.getenv("DEFAULT_ADMIN_PASSWORD", "").strip()

    if not admin_password:
        return {
            "status": "error",
            "message": "DEFAULT_ADMIN_PASSWORD is missing."
        }, 400

    admin_user = User.query.filter_by(role="admin").first()

    if not admin_user:
        admin_user = User(
            name=admin_name,
            username=admin_username,
            email=admin_email,
            role="admin",
            status="approved",
            city="جدة",
            specialty="إدارة المجتمع",
            bio="الحساب الإداري الرئيسي لمجتمع بيت المصور.",
        )
        db.session.add(admin_user)

    existing_username = User.query.filter(
        User.username == admin_username,
        User.id != admin_user.id
    ).first()

    if existing_username:
        return {
            "status": "error",
            "message": "DEFAULT_ADMIN_USERNAME is already used by another account."
        }, 400

    existing_email = User.query.filter(
        User.email == admin_email,
        User.id != admin_user.id
    ).first()

    if existing_email:
        return {
            "status": "error",
            "message": "DEFAULT_ADMIN_EMAIL is already used by another account."
        }, 400

    admin_user.name = admin_name
    admin_user.username = admin_username
    admin_user.email = admin_email
    admin_user.role = "admin"
    admin_user.status = "approved"
    admin_user.set_password(admin_password)

    db.session.commit()

    return {
        "status": "success",
        "message": "Admin account has been updated successfully.",
        "email": admin_user.email,
        "username": admin_user.username
    }


@app.errorhandler(404)
def page_not_found(error):
    return render_template("errors/404.html"), 404


@app.errorhandler(413)
@app.errorhandler(RequestEntityTooLarge)
def file_too_large(error):
    return render_template("errors/413.html"), 413


@app.errorhandler(500)
def internal_server_error(error):
    db.session.rollback()
    return render_template("errors/500.html"), 500


if __name__ == "__main__":
    app.run(debug=True)