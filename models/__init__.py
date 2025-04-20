from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def init_app(app):
    # Configure the DB here or in app.py
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_BINDS'] = {
        'db': "sqlite:///PetAdoption.sqlite"
    }
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///PetAdoption.sqlite'

    db.init_app(app)
    app.logger.info('Initialized models')

    with app.app_context():
        from .user import User
        from .pet_type import PetType
        from .pet import Pet
        from .adoption import Adoption
        from .review import Review

        db.create_all()
        db.session.commit()
        app.logger.debug('All tables are created')
