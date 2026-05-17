from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(120), nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(160), unique=True, nullable=False, index=True)

    password_hash = db.Column(db.String(255), nullable=False)

    role = db.Column(db.String(30), nullable=False, default="member")
    status = db.Column(db.String(30), nullable=False, default="pending")

    bio = db.Column(db.Text, nullable=True)
    city = db.Column(db.String(100), nullable=True)
    specialty = db.Column(db.String(120), nullable=True)

    avatar = db.Column(db.String(255), nullable=True)
    cover_image = db.Column(db.String(255), nullable=True)

    instagram_url = db.Column(db.String(255), nullable=True)
    whatsapp = db.Column(db.String(50), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    posts = db.relationship(
        "Post",
        backref="author",
        lazy=True,
        cascade="all, delete-orphan"
    )

    likes = db.relationship(
        "Like",
        backref="user",
        lazy=True,
        cascade="all, delete-orphan"
    )

    comments = db.relationship(
        "Comment",
        backref="user",
        lazy=True,
        cascade="all, delete-orphan"
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return self.role == "admin"

    @property
    def is_trainer(self):
        return self.role == "trainer"

    @property
    def is_member(self):
        return self.role == "member"

    @property
    def is_approved(self):
        return self.status == "approved"

    @property
    def is_pending(self):
        return self.status == "pending"

    @property
    def is_blocked(self):
        return self.status == "blocked"

    def __repr__(self):
        return f"<User {self.username}>"


class Post(db.Model):
    __tablename__ = "posts"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)

    content = db.Column(db.Text, nullable=False)
    image_filename = db.Column(db.String(255), nullable=True)

    is_pinned = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    likes = db.relationship(
        "Like",
        backref="post",
        lazy=True,
        cascade="all, delete-orphan"
    )

    comments = db.relationship(
        "Comment",
        backref="post",
        lazy=True,
        cascade="all, delete-orphan",
        order_by="Comment.created_at.asc()"
    )

    @property
    def likes_count(self):
        return len(self.likes)

    @property
    def comments_count(self):
        return len(self.comments)

    def is_liked_by(self, user_id):
        return any(like.user_id == user_id for like in self.likes)

    def __repr__(self):
        return f"<Post {self.id} by User {self.user_id}>"


class Like(db.Model):
    __tablename__ = "likes"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    post_id = db.Column(db.Integer, db.ForeignKey("posts.id"), nullable=False, index=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        db.UniqueConstraint("user_id", "post_id", name="unique_user_post_like"),
    )

    def __repr__(self):
        return f"<Like user={self.user_id} post={self.post_id}>"


class Comment(db.Model):
    __tablename__ = "comments"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    post_id = db.Column(db.Integer, db.ForeignKey("posts.id"), nullable=False, index=True)

    content = db.Column(db.Text, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<Comment {self.id} post={self.post_id}>"