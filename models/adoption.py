from . import db
from sqlalchemy import Sequence
from datetime import datetime


class Adoption(db.Model):
    __bind_key__ = 'db'
    id = db.Column(db.Integer, Sequence('Adoption_sequence'), unique=True, nullable=False, primary_key=True)
    user_id = db.Column(db.Integer)
    pet_id = db.Column(db.Integer)
    adoption_date = db.Column(db.TIMESTAMP, default=datetime.now)
    status = db.Column(db.String(50), nullable=False)
