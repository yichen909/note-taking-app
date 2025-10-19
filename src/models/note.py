from datetime import datetime

from src.models.user import db


class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    tags = db.Column(db.Text, nullable=True, default="")
    event_date = db.Column(db.Date, nullable=True)
    event_time = db.Column(db.Time, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Note {self.title}>"

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "tags": self.tags or "",
            "event_date": self.event_date.isoformat() if self.event_date else None,
            "event_time": self.event_time.strftime("%H:%M") if self.event_time else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
