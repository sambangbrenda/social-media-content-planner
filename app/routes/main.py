from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models import User, Campaign, Post
import csv
from io import StringIO
from flask import make_response

main_bp = Blueprint("main", __name__)

@main_bp.route("/")
@login_required
def dashboard():
    campaigns = Campaign.query.filter_by(user_id=current_user.id).all()
    campaign_ids = [c.id for c in campaigns]

    total_posts = 0
    scheduled_posts = 0
    draft_posts = 0
    published_posts = 0
    upcoming_posts = []
    total_campaigns = len(campaigns)
    upcoming_7_days = 0
    next_scheduled_post = None

    if campaign_ids:
        total_posts = Post.query.filter(Post.campaign_id.in_(campaign_ids)).count()
        scheduled_posts = Post.query.filter(
            Post.campaign_id.in_(campaign_ids),
            Post.status == "Scheduled"
        ).count()
        draft_posts = Post.query.filter(
            Post.campaign_id.in_(campaign_ids),
            Post.status == "Draft"
        ).count()
        published_posts = Post.query.filter(
            Post.campaign_id.in_(campaign_ids),
            Post.status == "Posted"
        ).count()

        upcoming_posts = (
            Post.query.filter(Post.campaign_id.in_(campaign_ids))
            .order_by(Post.scheduled_at.asc())
            .limit(5)
            .all()
        )

        now = datetime.now()
        next_week = now + timedelta(days=7)

        upcoming_7_days = (
            Post.query.filter(
                Post.campaign_id.in_(campaign_ids),
                Post.scheduled_at.isnot(None),
                Post.scheduled_at >= now,
                Post.scheduled_at <= next_week
            ).count()
        )

        next_scheduled_post = (
            Post.query.filter(
                Post.campaign_id.in_(campaign_ids),
                Post.scheduled_at.isnot(None)
            )
            .order_by(Post.scheduled_at.asc())
            .first()
        )

    stats = {
        "total_posts": total_posts,
        "scheduled_posts": scheduled_posts,
        "draft_posts": draft_posts,
        "published_posts": published_posts,
    }

    summary = {
        "total_campaigns": total_campaigns,
        "upcoming_7_days": upcoming_7_days,
        "next_scheduled_post": (
            next_scheduled_post.scheduled_at.strftime("%Y-%m-%d %H:%M")
            if next_scheduled_post and next_scheduled_post.scheduled_at
            else "No scheduled post"
        ),
    }

    chart_data = {
        "labels": ["Draft", "Scheduled", "Posted"],
        "post_values": [draft_posts, scheduled_posts, published_posts],
    }

    return render_template(
        "dashboard.html",
        stats=stats,
        upcoming_posts=upcoming_posts,
        summary=summary,
        chart_data=chart_data,
    )

@main_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not name or not email or not password or not confirm_password:
            flash("Please fill in all fields.", "danger")
            return redirect(url_for("main.register"))

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return redirect(url_for("main.register"))

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("Email already exists.", "danger")
            return redirect(url_for("main.register"))

        user = User(name=name, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        flash("Account created successfully. Please log in.", "success")
        return redirect(url_for("main.login"))

    return render_template("register.html")

@main_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            flash("Logged in successfully.", "success")
            return redirect(url_for("main.dashboard"))

        flash("Invalid email or password.", "danger")

    return render_template("login.html")

@main_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("main.login"))

@main_bp.route("/campaigns")
@login_required
def campaigns():
    campaigns = Campaign.query.filter_by(user_id=current_user.id).order_by(Campaign.created_at.desc()).all()
    return render_template("campaigns.html", campaigns=campaigns)

@main_bp.route("/campaigns/new", methods=["GET", "POST"])
@login_required
def new_campaign():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        start_date_raw = request.form.get("start_date", "")
        end_date_raw = request.form.get("end_date", "")

        if not name:
            flash("Campaign name is required.", "danger")
            return redirect(url_for("main.new_campaign"))

        start_date = None
        end_date = None

        if start_date_raw:
            start_date = datetime.strptime(start_date_raw, "%Y-%m-%d").date()

        if end_date_raw:
            end_date = datetime.strptime(end_date_raw, "%Y-%m-%d").date()

        if start_date and end_date and end_date < start_date:
            flash("End date cannot be earlier than start date.", "danger")
            return redirect(url_for("main.new_campaign"))

        campaign = Campaign(
            user_id=current_user.id,
            name=name,
            description=description if description else None,
            start_date=start_date,
            end_date=end_date,
        )
        db.session.add(campaign)
        db.session.commit()

        flash("Campaign created successfully.", "success")
        return redirect(url_for("main.campaigns"))

    return render_template("campaign_form.html")

@main_bp.route("/campaigns/<int:campaign_id>/edit", methods=["GET", "POST"])
@login_required
def edit_campaign(campaign_id):
    campaign = Campaign.query.get_or_404(campaign_id)

    if campaign.user_id != current_user.id:
        flash("Unauthorized access.", "danger")
        return redirect(url_for("main.campaigns"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        start_date_raw = request.form.get("start_date", "")
        end_date_raw = request.form.get("end_date", "")

        if not name:
            flash("Campaign name is required.", "danger")
            return redirect(url_for("main.edit_campaign", campaign_id=campaign.id))

        start_date = None
        end_date = None

        if start_date_raw:
            start_date = datetime.strptime(start_date_raw, "%Y-%m-%d").date()

        if end_date_raw:
            end_date = datetime.strptime(end_date_raw, "%Y-%m-%d").date()

        if start_date and end_date and end_date < start_date:
            flash("End date cannot be earlier than start date.", "danger")
            return redirect(url_for("main.edit_campaign", campaign_id=campaign.id))

        campaign.name = name
        campaign.description = description if description else None
        campaign.start_date = start_date
        campaign.end_date = end_date

        db.session.commit()
        flash("Campaign updated successfully.", "success")
        return redirect(url_for("main.campaigns"))

    return render_template("edit_campaign.html", campaign=campaign)


@main_bp.route("/campaigns/<int:campaign_id>/delete", methods=["POST"])
@login_required
def delete_campaign(campaign_id):
    campaign = Campaign.query.get_or_404(campaign_id)

    if campaign.user_id != current_user.id:
        flash("Unauthorized access.", "danger")
        return redirect(url_for("main.campaigns"))

    db.session.delete(campaign)
    db.session.commit()
    flash("Campaign deleted successfully.", "info")
    return redirect(url_for("main.campaigns"))

@main_bp.route("/posts")
@login_required
def posts():
    campaigns = Campaign.query.filter_by(user_id=current_user.id).order_by(Campaign.created_at.desc()).all()

    search_term = request.args.get("q", "").strip()
    platform_filter = request.args.get("platform", "").strip()
    status_filter = request.args.get("status", "").strip()
    campaign_filter = request.args.get("campaign_id", "").strip()
    page = request.args.get("page", 1, type=int)
    per_page = 5

    query = Post.query.join(Campaign).filter(Campaign.user_id == current_user.id)

    if search_term:
        query = query.filter(
            (Post.title.ilike(f"%{search_term}%")) |
            (Post.content.ilike(f"%{search_term}%"))
        )

    if platform_filter:
        query = query.filter(Post.platform == platform_filter)

    if status_filter:
        query = query.filter(Post.status == status_filter)

    if campaign_filter:
        query = query.filter(Post.campaign_id == int(campaign_filter))

    pagination = query.order_by(Post.created_at.desc()).paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )

    posts = pagination.items

    return render_template(
        "posts.html",
        posts=posts,
        campaigns=campaigns,
        search_term=search_term,
        platform_filter=platform_filter,
        status_filter=status_filter,
        campaign_filter=campaign_filter,
        pagination=pagination,
    )

@main_bp.route("/posts/new", methods=["GET", "POST"])
@login_required
def new_post():
    campaigns = Campaign.query.filter_by(user_id=current_user.id).all()

    if request.method == "POST":
        campaign_id = request.form.get("campaign_id", "").strip()
        title = request.form.get("title", "").strip()
        content = request.form.get("content", "").strip()
        platform = request.form.get("platform", "").strip()
        scheduled_at_raw = request.form.get("scheduled_at", "")
        status = request.form.get("status", "Draft").strip()

        if not campaign_id or not title or not content or not platform:
            flash("Please fill in all required fields.", "danger")
            return redirect(url_for("main.new_post"))

        campaign = Campaign.query.filter_by(id=campaign_id, user_id=current_user.id).first()
        if not campaign:
            flash("Invalid campaign selected.", "danger")
            return redirect(url_for("main.new_post"))

        scheduled_at = None
        if scheduled_at_raw:
            scheduled_at = datetime.strptime(scheduled_at_raw, "%Y-%m-%dT%H:%M")

        post = Post(
            campaign_id=campaign.id,
            title=title,
            content=content,
            platform=platform,
            scheduled_at=scheduled_at,
            status=status,
        )
        db.session.add(post)
        db.session.commit()

        flash("Post created successfully.", "success")
        return redirect(url_for("main.posts"))

    return render_template("post_form.html", campaigns=campaigns)

@main_bp.route("/posts/<int:post_id>/edit", methods=["GET", "POST"])
@login_required
def edit_post(post_id):
    post = Post.query.get_or_404(post_id)

    # Make sure the post belongs to the current user
    if post.campaign.user_id != current_user.id:
        flash("Unauthorized access.", "danger")
        return redirect(url_for("main.posts"))

    campaigns = Campaign.query.filter_by(user_id=current_user.id).all()

    if request.method == "POST":
        campaign_id = request.form.get("campaign_id", "").strip()
        title = request.form.get("title", "").strip()
        content = request.form.get("content", "").strip()
        platform = request.form.get("platform", "").strip()
        scheduled_at_raw = request.form.get("scheduled_at", "")
        status = request.form.get("status", "Draft").strip()

        if not campaign_id or not title or not content or not platform:
            flash("Please fill in all required fields.", "danger")
            return redirect(url_for("main.edit_post", post_id=post.id))

        campaign = Campaign.query.filter_by(id=campaign_id, user_id=current_user.id).first()
        if not campaign:
            flash("Invalid campaign selected.", "danger")
            return redirect(url_for("main.edit_post", post_id=post.id))

        scheduled_at = None
        if scheduled_at_raw:
            scheduled_at = datetime.strptime(scheduled_at_raw, "%Y-%m-%dT%H:%M")

        post.campaign_id = campaign.id
        post.title = title
        post.content = content
        post.platform = platform
        post.scheduled_at = scheduled_at
        post.status = status

        db.session.commit()
        flash("Post updated successfully.", "success")
        return redirect(url_for("main.posts"))

    return render_template("edit_post.html", post=post, campaigns=campaigns)


@main_bp.route("/posts/<int:post_id>/delete", methods=["POST"])
@login_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)

    if post.campaign.user_id != current_user.id:
        flash("Unauthorized access.", "danger")
        return redirect(url_for("main.posts"))

    db.session.delete(post)
    db.session.commit()
    flash("Post deleted successfully.", "info")
    return redirect(url_for("main.posts"))

@main_bp.route("/posts/export")
@login_required
def export_posts():
    search_term = request.args.get("q", "").strip()
    platform_filter = request.args.get("platform", "").strip()
    status_filter = request.args.get("status", "").strip()
    campaign_filter = request.args.get("campaign_id", "").strip()

    query = Post.query.join(Campaign).filter(Campaign.user_id == current_user.id)

    if search_term:
        query = query.filter(
            (Post.title.ilike(f"%{search_term}%")) |
            (Post.content.ilike(f"%{search_term}%"))
        )

    if platform_filter:
        query = query.filter(Post.platform == platform_filter)

    if status_filter:
        query = query.filter(Post.status == status_filter)

    if campaign_filter:
        query = query.filter(Post.campaign_id == int(campaign_filter))

    posts = query.order_by(Post.created_at.desc()).all()

    output = StringIO()
    writer = csv.writer(output)

    writer.writerow(["Campaign", "Title", "Platform", "Status", "Scheduled At", "Created At"])

    for post in posts:
        writer.writerow([
            post.campaign.name,
            post.title,
            post.platform,
            post.status,
            post.scheduled_at.strftime("%Y-%m-%d %H:%M") if post.scheduled_at else "",
            post.created_at.strftime("%Y-%m-%d %H:%M") if post.created_at else "",
        ])

    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = "attachment; filename=posts_export.csv"
    response.headers["Content-Type"] = "text/csv"
    return response

@main_bp.route("/calendar")
@login_required
def calendar():
    campaigns = Campaign.query.filter_by(user_id=current_user.id).all()
    campaign_ids = [c.id for c in campaigns]

    start_date_raw = request.args.get("start_date", "").strip()
    end_date_raw = request.args.get("end_date", "").strip()

    start_date = None
    end_date = None

    if start_date_raw:
        start_date = datetime.strptime(start_date_raw, "%Y-%m-%d").date()

    if end_date_raw:
        end_date = datetime.strptime(end_date_raw, "%Y-%m-%d").date()

    posts_query = Post.query.join(Campaign).filter(Campaign.user_id == current_user.id)

    if campaign_ids:
        posts_query = posts_query.filter(Post.campaign_id.in_(campaign_ids))
    else:
        posts_query = posts_query.filter(False)

    if start_date:
        posts_query = posts_query.filter(Post.scheduled_at.isnot(None))
        posts_query = posts_query.filter(Post.scheduled_at >= datetime.combine(start_date, datetime.min.time()))

    if end_date:
        posts_query = posts_query.filter(Post.scheduled_at.isnot(None))
        posts_query = posts_query.filter(Post.scheduled_at <= datetime.combine(end_date, datetime.max.time()))

    posts = posts_query.order_by(Post.scheduled_at.asc()).all()

    grouped_posts = {}
    for post in posts:
        if post.scheduled_at:
            group_key = post.scheduled_at.strftime("%Y-%m-%d")
        else:
            group_key = "Unscheduled"

        grouped_posts.setdefault(group_key, []).append(post)

    return render_template(
        "calendar.html",
        grouped_posts=grouped_posts,
        start_date_raw=start_date_raw,
        end_date_raw=end_date_raw,
    )

@main_bp.route("/profile")
@login_required
def profile():
    return render_template("profile.html")

@main_bp.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    if request.method == "POST":
        theme = request.form.get("theme", "light")
        default_view = request.form.get("default_view", "dashboard")

        if theme not in ["light", "dark"]:
            theme = "light"

        session["theme"] = theme
        session["default_view"] = default_view

        flash("Settings saved successfully.", "success")
        return redirect(url_for("main.settings"))

    return render_template("settings.html")

@main_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not email or not new_password or not confirm_password:
            flash("Please fill in all fields.", "danger")
            return redirect(url_for("main.forgot_password"))

        if new_password != confirm_password:
            flash("Passwords do not match.", "danger")
            return redirect(url_for("main.forgot_password"))

        user = User.query.filter_by(email=email).first()
        if not user:
            flash("No account found with that email.", "danger")
            return redirect(url_for("main.forgot_password"))

        user.set_password(new_password)
        db.session.commit()
        flash("Password reset successfully. Please log in.", "success")
        return redirect(url_for("main.login"))

    return render_template("forgot_password.html")