from . import db
from sqlalchemy import Sequence
from datetime import datetime

class Pet(db.Model):
    __bind_key__ = 'db'
    id = db.Column(db.Integer, Sequence('Pet_sequence'), unique=True, nullable=False, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    breed = db.Column(db.String(100))
    age = db.Column(db.Integer)
    gender = db.Column(db.String(20))
    pet_type_id = db.Column(db.Integer)
    description = db.Column(db.String(255))
    image_url = db.Column(db.String(255))
    available = db.Column(db.Boolean, default=True)
    created_by = db.Column(db.Integer)
    created_at = db.Column(db.TIMESTAMP, default=datetime.now)