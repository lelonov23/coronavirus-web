from flask_login import UserMixin
import sqlalchemy
from sqlalchemy import orm
from .db_session import SqlAlchemyBase
from werkzeug.security import generate_password_hash, check_password_hash


class Patient(SqlAlchemyBase, UserMixin):
    __tablename__ = 'patients'

    id = sqlalchemy.Column(sqlalchemy.Integer,
                           primary_key=True, autoincrement=True)
    name = sqlalchemy.Column(sqlalchemy.String, index=True, nullable=True)
    surname = sqlalchemy.Column(sqlalchemy.String, index=True, nullable=True)
    midname = sqlalchemy.Column(sqlalchemy.String, index=True, nullable=True)
    age = sqlalchemy.Column(sqlalchemy.Integer, index=True, nullable=True)
    condition = sqlalchemy.Column(sqlalchemy.String, index=True, nullable=True)
    email = sqlalchemy.Column(sqlalchemy.String,
                              index=True, unique=True, nullable=True)
    hashed_password = sqlalchemy.Column(sqlalchemy.String, nullable=True)

    def set_password(self, password):
        self.hashed_password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.hashed_password, password)