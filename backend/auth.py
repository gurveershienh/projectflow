from functools import wraps
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from email_validator import validate_email, EmailNotValidError
from flask import session, jsonify
class Authenticator(PasswordHasher):
    def __init__(self):
        super().__init__()

    def hash_password(self, password):
        hashed = self.hash(password)
        return hashed

    def authenticate_password(self, hash, password):
        try:
            return self.verify(hash, password)
        except VerifyMismatchError:
            return False
        
    @staticmethod
    def email_validation(email):
        try:
            emailinfo = validate_email(email, check_deliverability=False)
            email =  emailinfo.normalized
            return True
        except EmailNotValidError as e:
            return False
    
    @staticmethod
    def authenticate_session(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                raise AuthenticationError("Must be logged in")
            return f(*args, **kwargs)
        return decorated_function
    
    @staticmethod
    def check_authorization(f):
        #Only run on routes with user_id as a parameter. Service level authorization is performed via joins. 
        #Might update routes to take user_id for better service performance, but for now we move.
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if kwargs.get('user_id') != session['user_id']: 
                raise AuthorizationError("Access denied")
            return f(*args, **kwargs)
        return decorated_function         

class AuthenticationError(Exception):
    pass

class AuthorizationError(Exception):
    pass