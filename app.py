# app.py
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime
import os
import random
import string
from werkzeug.utils import secure_filename

from models import init_app, db
from models.user import User
from models.pet_type import PetType
from models.pet import Pet
from models.adoption import Adoption
from models.review import Review

app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
init_app(app)


def get_random_numbers(string_length=3):
    return ''.join(random.choice(string.digits) for x in range(string_length))


@app.route('/')
def welcome():
    return "🐾 Welcome to the Pet Adoption Platform API!"


# ---------------- Users ----------------
@app.route('/register', methods=['POST'])
def create_user():
    username = request.form.get('username')
    email = request.form.get('email')
    password = request.form.get('password')
    role = request.form.get('role')

    if not username or not email or not password or not role:
        return jsonify({"message": "Missing required fields"}), 400

    user = User(
        username=username,
        email=email,
        password=password,
        role=role,
        created_at=datetime.now()
    )
    try:
        db.session.add(user)
        db.session.commit()
        db.session.close()
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Error creating user", "error": str(e)}), 400
    return jsonify({"message": "User created successfully."}), 201


@app.route('/get_users', methods=['GET'])
def get_users():
    users = User.query.all()
    return jsonify([{k: v for k, v in u.__dict__.items() if not k.startswith('_')} for u in users])


# ---------------- Pet Types ----------------
@app.route('/add_pet_type', methods=['POST'])
def add_pet_type():
    type_name = request.form.get('type_name')
    description = request.form.get('description')

    pet_type = PetType(
        type_name=type_name,
        description=description
    )
    try:
        db.session.add(pet_type)
        db.session.commit()
        db.session.close()
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Error creating pet type", "error": str(e)}), 400
    return jsonify({"message": "Pet type added successfully."}), 201


@app.route('/get_pet_types', methods=['GET'])
def get_pet_types():
    types = PetType.query.all()
    return jsonify([{k: v for k, v in t.__dict__.items() if not k.startswith('_')} for t in types])


# ---------------- Pets ----------------
@app.route('/add_pet', methods=['POST'])
def add_pet():
    name = request.form.get('name')
    breed = request.form.get('breed')
    age = request.form.get('age')
    gender = request.form.get('gender')
    pet_type_id = request.form.get('pet_type_id')
    description = request.form.get('description')
    created_by = request.form.get('created_by')
    file = request.files.get('image_url')

    image_url = None
    if file and file.filename != '':
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        image_url = filepath

    pet = Pet(
        name=name,
        breed=breed,
        age=age,
        gender=gender,
        pet_type_id=pet_type_id,
        description=description,
        image_url=image_url,
        created_by=created_by,
        available=True,
        created_at=datetime.now()
    )
    try:
        db.session.add(pet)
        db.session.commit()
        db.session.close()
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Error adding pet", "error": str(e)}), 400
    return jsonify({"message": "Pet added successfully."}), 201


@app.route('/get_pets', methods=['GET'])
def get_pets():
    pets = Pet.query.all()
    return jsonify([{k: v for k, v in p.__dict__.items() if not k.startswith('_')} for p in pets])


# ---------------- Adoptions ----------------
@app.route('/adopt_pet', methods=['POST'])
def adopt_pet():
    user_id = request.form.get('user_id')
    pet_id = request.form.get('pet_id')
    status = request.form.get('status')  # e.g., Pending, Approved, Rejected

    adoption = Adoption(
        user_id=user_id,
        pet_id=pet_id,
        status=status,
        adoption_date=datetime.now()
    )
    try:
        db.session.add(adoption)
        db.session.commit()
        db.session.close()
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Error processing adoption", "error": str(e)}), 400
    return jsonify({"message": "Adoption request submitted."}), 201


@app.route('/get_adoptions', methods=['GET'])
def get_adoptions():
    adoptions = Adoption.query.all()
    return jsonify([{k: v for k, v in a.__dict__.items() if not k.startswith('_')} for a in adoptions])


# ---------------- Cancel Adoption ----------------
@app.route('/cancel_adoption', methods=['POST'])
def cancel_adoption():
    adoption_id = request.form.get('adoption_id')

    if not adoption_id:
        return jsonify({"error": "adoption_id is required"}), 400

    adoption = Adoption.query.filter_by(id=adoption_id).first()
    if not adoption:
        return jsonify({"error": "Adoption not found"}), 404

    try:
        adoption.status = "Cancelled"
        db.session.commit()
        return jsonify({"message": "Adoption cancelled successfully."}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Error cancelling adoption", "error": str(e)}), 400


# ---------------- Reviews ----------------
@app.route('/add_review', methods=['POST'])
def add_review():
    user_id = request.form.get('user_id')
    pet_id = request.form.get('pet_id')
    rating = request.form.get('rating')
    comment = request.form.get('comment')

    review = Review(
        user_id=user_id,
        pet_id=pet_id,
        rating=rating,
        comment=comment,
        review_date=datetime.now()
    )
    try:
        db.session.add(review)
        db.session.commit()
        db.session.close()
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Error adding review", "error": str(e)}), 400
    return jsonify({"message": "Review submitted successfully."}), 201


@app.route('/get_reviews', methods=['GET'])
def get_reviews():
    reviews = Review.query.all()
    return jsonify([{k: v for k, v in r.__dict__.items() if not k.startswith('_')} for r in reviews])


if __name__ == '__main__':
    app.run(debug=True)
