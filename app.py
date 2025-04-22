# app.py
from flask import render_template, redirect, request, session, url_for, Flask, jsonify
from flask import send_from_directory
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
app.config['SESSION_COOKIE_SAMESITE'] = 'Strict'
app.config['SESSION_COOKIE_PATH'] = '/'
app.config['SESSION_KEY_PREFIX'] = 'helloo'
app.config['SESSION_COOKIE_NAME'] = 'Bookstorevsession'
app.secret_key = "Kc5c3zTk'-3<&BdL:P92O{_(:-NkY+K"

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
init_app(app)


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    error = None

    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        role = request.form.get('role')

        if password != confirm_password:
            error = "Passwords do not match"
        elif User.query.filter_by(email=email).first():
            error = "User with this email already exists"
        else:
            new_user = User(
                username=username,
                email=email,
                password=password,  # No hashing per your setup
                role=role,
                created_at=datetime.now()
            )
            db.session.add(new_user)
            db.session.commit()
            return redirect('/login')

    return render_template('register.html', error=error)


@app.route('/login', methods=['GET', 'POST'])
def login():
    from models.user import User

    error = None

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email, password=password).first()

        if user:
            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role

            if user.role == 'admin':
                return redirect('/admin/dashboard')
            else:
                return redirect('/user/dashboard')
        else:
            error = "Invalid email or password"

    return render_template('login.html', error=error)


@app.route('/user/dashboard')
def user_dashboard():
    if 'user_id' not in session or session.get('role') != 'adopter':
        return redirect('/login')
    return render_template('user/dashboard.html')


@app.route('/get_pets')
def get_pets():
    from models.pet import Pet
    from models.pet_type import PetType  # assumed

    pets = Pet.query.filter_by(available=True).all()
    result = []

    for pet in pets:
        pet_type = PetType.query.get(pet.pet_type_id)
        result.append({
            'id': pet.id,
            'name': pet.name,
            'breed': pet.breed,
            'age': pet.age,
            'gender': pet.gender,
            'type': pet_type.type_name if pet_type else "Unknown",
            'image_url': pet.image_url or "static/images/default_pet.png"
        })

    return jsonify(result)


@app.route('/pet_details/<int:pet_id>')
def pet_details(pet_id):
    from models.pet import Pet
    from models.pet_type import PetType
    from models.review import Review
    from models.user import User
    from models.adoption import Adoption

    if 'user_id' not in session:
        return redirect('/login')

    pet = Pet.query.get_or_404(pet_id)
    pet_type = PetType.query.get(pet.pet_type_id)

    # Load reviews
    review_data = db.session.query(Review, User.username) \
        .join(User, Review.user_id == User.id) \
        .filter(Review.pet_id == pet.id).all()

    reviews = [{
        'username': username,
        'rating': review.rating,
        'comment': review.comment
    } for review, username in review_data]

    # Check if user is allowed to leave review
    can_review = False
    if session.get('role') == 'adopter':
        user_id = session['user_id']
        approved = Adoption.query.filter_by(user_id=user_id, pet_id=pet.id, status='Approved').first()
        if approved:
            can_review = True

    return render_template(
        'user/pet_details.html',
        pet=pet,
        pet_type=pet_type,
        reviews=reviews,
        is_admin=(session.get('role') == 'admin'),
        can_review=can_review
    )


@app.route('/apply_adoption', methods=['POST'])
def apply_adoption():
    from models.adoption import Adoption
    from models.pet import Pet

    if 'user_id' not in session or session.get('role') != 'adopter':
        return redirect('/login')

    user_id = session['user_id']
    pet_id = request.form.get('pet_id')

    # Check if already applied for this pet
    existing = Adoption.query.filter_by(user_id=user_id, pet_id=pet_id).first()
    if existing:
        return "You have already applied for this pet.", 400

    # Mark pet as unavailable
    pet = Pet.query.get(pet_id)
    if pet and pet.available:
        pet.available = False
        application = Adoption(
            user_id=user_id,
            pet_id=pet_id,
            status='Pending'  # Status should match your flow
        )
        db.session.add(application)
        db.session.commit()
        return redirect('/my_applications')

    return "Pet is not available for adoption.", 400


@app.route('/my_applications')
def my_applications():
    from models.adoption import Adoption
    from models.pet import Pet

    if 'user_id' not in session or session.get('role') != 'adopter':
        return redirect('/login')

    user_id = session['user_id']
    applications = Adoption.query.filter_by(user_id=user_id).order_by(Adoption.adoption_date.desc()).all()

    result = []
    for app in applications:
        pet = Pet.query.get(app.pet_id)
        if pet:
            result.append({
                'id': app.id,
                'pet_id': pet.id,
                'pet_name': pet.name,
                'pet_breed': pet.breed,
                'image_url': pet.image_url,
                'status': app.status,
                'adoption_date': app.adoption_date.strftime('%Y-%m-%d')
            })

    return render_template('user/my_applications.html', applications=result)


@app.route('/submit_review', methods=['POST'])
def submit_review():
    from models.review import Review
    from models.adoption import Adoption

    if 'user_id' not in session or session.get('role') != 'adopter':
        return redirect('/login')

    user_id = session['user_id']
    pet_id = request.form.get('pet_id')
    rating = int(request.form.get('rating'))
    comment = request.form.get('comment')

    # Confirm adoption was approved
    adoption = Adoption.query.filter_by(user_id=user_id, pet_id=pet_id, status='Approved').first()
    if not adoption:
        return "You can only review pets you have adopted.", 403

    review = Review(
        user_id=user_id,
        pet_id=pet_id,
        rating=rating,
        comment=comment
    )
    db.session.add(review)
    db.session.commit()

    return redirect(f'/pet_details/{pet_id}')


@app.route('/admin/dashboard')
def admin_dashboard():
    from models.pet import Pet
    from models.user import User
    from models.adoption import Adoption
    from models.pet_type import PetType

    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect('/login')

    pets = Pet.query.all()
    users = User.query.all()
    adoptions = Adoption.query.all()
    pet_types = PetType.query.all()

    # Adoption status summary
    adoption_summary = {
        'Pending': 0,
        'Approved': 0,
        'Rejected': 0
    }
    for a in adoptions:
        status = a.status.strip().capitalize()
        if status in adoption_summary:
            adoption_summary[status] += 1

    # Pet type distribution
    type_data = {}
    for t in pet_types:
        count = Pet.query.filter_by(pet_type_id=t.id).count()
        type_data[t.type_name] = count

    return render_template(
        'admin/dashboard.html',
        total_pets=len(pets),
        total_users=len(users),
        total_adoptions=len(adoptions),
        adoption_summary=adoption_summary,
        type_data=type_data
    )


@app.route('/admin/pets')
def admin_pets():
    from models.pet import Pet
    from models.pet_type import PetType

    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect('/login')

    pets = Pet.query.all()
    pet_list = []

    for p in pets:
        pet_type = PetType.query.get(p.pet_type_id)
        pet_list.append({
            'id': p.id,
            'name': p.name,
            'breed': p.breed,
            'image_url': p.image_url,
            'type': pet_type.type_name if pet_type else "Unknown",
            'available': p.available
        })

    return render_template('admin/pets.html', pets=pet_list)


@app.route('/admin/add_pet', methods=['GET', 'POST'])
def add_pet():
    from models.pet import Pet
    from models.pet_type import PetType
    from werkzeug.utils import secure_filename
    import os
    from datetime import datetime

    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect('/login')

    if request.method == 'POST':
        name = request.form.get('name')
        breed = request.form.get('breed')
        age = request.form.get('age')
        gender = request.form.get('gender')
        description = request.form.get('description')
        pet_type_id = request.form.get('pet_type_id')
        image_file = request.files.get('image')

        image_url = ''
        if image_file and image_file.filename:
            filename = secure_filename(image_file.filename)
            image_path = os.path.join('uploads', filename)
            image_file.save(image_path)
            image_url = image_path

        pet = Pet(
            name=name,
            breed=breed,
            age=int(age),
            gender=gender,
            description=description,
            pet_type_id=pet_type_id,
            image_url=image_url,
            available=True,
            created_by=session['user_id'],
            created_at=datetime.now()
        )

        db.session.add(pet)
        db.session.commit()
        return redirect('/admin/pets')

    pet_types = PetType.query.all()
    return render_template('admin/add_pet.html', pet_types=pet_types)


@app.route('/admin/delete_pet', methods=['POST'])
def delete_pet():
    from models.pet import Pet

    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect('/login')

    pet_id = request.form.get('pet_id')
    pet = Pet.query.get(pet_id)

    if pet:
        db.session.delete(pet)
        db.session.commit()

    return redirect('/admin/pets')


@app.route('/admin/adoptions')
def admin_adoptions():
    from models.adoption import Adoption
    from models.user import User
    from models.pet import Pet

    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect('/login')

    apps = Adoption.query.order_by(Adoption.adoption_date.desc()).all()
    adoption_list = []

    for app in apps:
        user = User.query.get(app.user_id)
        pet = Pet.query.get(app.pet_id)
        if user and pet:
            adoption_list.append({
                'id': app.id,
                'status': app.status,
                'date': app.adoption_date.strftime('%Y-%m-%d'),
                'user_name': user.username,
                'user_email': user.email,
                'pet_name': pet.name,
                'pet_id': pet.id
            })

    return render_template('admin/adoptions.html', adoptions=adoption_list)


@app.route('/admin/approve_adoption', methods=['POST'])
def approve_adoption():
    from models.adoption import Adoption
    from models.pet import Pet

    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect('/login')

    adoption_id = request.form.get('adoption_id')
    adoption = Adoption.query.get(adoption_id)

    if adoption and adoption.status.lower() == 'pending':
        adoption.status = 'Approved'
        # Also mark the pet as unavailable
        pet = Pet.query.get(adoption.pet_id)
        if pet:
            pet.available = False
        db.session.commit()

    return redirect('/admin/adoptions')


@app.route('/admin/reject_adoption', methods=['POST'])
def reject_adoption():
    from models.adoption import Adoption
    from models.pet import Pet

    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect('/login')

    adoption_id = request.form.get('adoption_id')
    adoption = Adoption.query.get(adoption_id)

    if adoption and adoption.status.lower() == 'pending':
        adoption.status = 'Rejected'

        # Optionally make pet available again
        pet = Pet.query.get(adoption.pet_id)
        if pet:
            pet.available = True

        db.session.commit()

    return redirect('/admin/adoptions')


@app.route('/admin/users')
def admin_users():
    from models.user import User

    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect('/login')

    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin/users.html', users=users)


@app.route('/admin/delete_user', methods=['POST'])
def delete_user():
    from models.user import User

    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect('/login')

    user_id = request.form.get('user_id')

    if str(user_id) != str(session['user_id']):
        user = User.query.get(user_id)
        if user:
            db.session.delete(user)
            db.session.commit()

    return redirect('/admin/users')


@app.route('/admin/pet_types', methods=['GET', 'POST'])
def admin_pet_types():
    from models.pet_type import PetType

    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect('/login')

    error_message = None

    if request.method == 'POST':
        type_name = request.form.get('type_name')
        description = request.form.get('description')

        # Prevent duplicate type names
        if PetType.query.filter_by(type_name=type_name.strip()).first():
            error_message = f"Type '{type_name}' already exists."
        else:
            new_type = PetType(type_name=type_name.strip(), description=description.strip())
            db.session.add(new_type)
            db.session.commit()
            return redirect('/admin/pet_types')

    types = PetType.query.order_by(PetType.id.desc()).all()
    return render_template('admin/pet_types.html', pet_types=types, error_message=error_message)


@app.route('/admin/delete_pet_type', methods=['POST'])
def delete_pet_type():
    from models.pet_type import PetType

    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect('/login')

    pet_type_id = request.form.get('pet_type_id')
    pet_type = PetType.query.get(pet_type_id)

    if pet_type:
        db.session.delete(pet_type)
        db.session.commit()

    return redirect('/admin/pet_types')


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')


if __name__ == '__main__':
    app.run(debug=True)
