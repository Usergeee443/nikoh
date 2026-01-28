from database import db
from datetime import datetime


class Favorite(db.Model):
    """Favorite model - sevimlilar"""
    __tablename__ = 'favorites'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    favorite_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    user = db.relationship('User', foreign_keys=[user_id], backref='favorites')
    favorite_user = db.relationship('User', foreign_keys=[favorite_user_id], backref='favorited_by')

    def __repr__(self):
        return f'<Favorite {self.user_id} -> {self.favorite_user_id}>'

    def to_dict(self):
        """Favoriteni dictionary ga aylantirish"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'favorite_user_id': self.favorite_user_id,
            'favorite_user': self.favorite_user.profile.to_dict() if self.favorite_user and self.favorite_user.profile else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
