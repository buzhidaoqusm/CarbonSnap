from datetime import datetime, timezone

from app.extensions.db import db


class Project(db.Model):
    __tablename__ = "projects"

    id = db.Column(db.Integer, primary_key=True)
    creator_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    title = db.Column(db.String(256), nullable=False)
    description = db.Column(db.Text)
    cover_image_url = db.Column(db.String(512))
    points_target = db.Column(db.Integer, nullable=False)
    points_raised = db.Column(db.Integer, nullable=False, default=0)
    # fundraising | completed
    status = db.Column(db.String(16), nullable=False, default="fundraising")
    deadline_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )


class ProjectContribution(db.Model):
    __tablename__ = "project_contributions"

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    points = db.Column(db.Integer, nullable=False)
    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
