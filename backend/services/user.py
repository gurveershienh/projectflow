from models import User
from auth import Authenticator
from base import BaseService

class UserService(BaseService):
    authenticator = Authenticator()
    '''
    UserService SHOULD NOT be instanstiated directly. Use classmethod constructors based on context.
    '''
    @classmethod
    def for_public(cls, db_session):
        return cls(db_session, user_id=None)
    
    @classmethod
    def for_user(cls, db_session, user_id):
        return cls(db_session, user_id)
    
    def create_user(self, data):

        if not data.get('name'):
            raise ValueError('Name is required')
        if not data.get('email'):
            raise ValueError('Email is required')
        if not data.get('password'):
            raise ValueError('Password is required')
        if not data.get('confirm_password'):
            raise ValueError('Password confirmation is required')
        
        self.check_email(data['email']) 
        self.check_password(data['password'], data['confirm_password'])

        secret = self.authenticator.hash_password(data['password'])

        user = User(
            email=data['email'],
            name=data['name'],
            secret=secret
        )

        return self._create_entity(user)
    
    def get_user(self, _id=None, email=None) -> User:
        if not email and not _id:
            raise ValueError("Identifier required")
        if not email:
            query = self.db.query(User).filter(User.id == _id)
            return self._get_entity(query)
        else:
            query = self.db.query(User).filter(User.email == email)
            return self._get_entity(query)
        
    def get_users(self):
        query = self.db.query(User)
        return self._get_entities(query)
    
    def change_user_email(self, _id, data):
        if not data.get('email'):
            raise ValueError('Email is required')
        self.check_email(data['email'])

        user = self.get_user(_id=_id)
        self._update_entity(user, data, ["email"])
    
    def change_user_password(self, _id, data):
        if not data.get('password'):
            raise ValueError('Password is required')
        if not data.get('confirm_password'):
            raise ValueError('Password confirmation is required')

        self.check_password(data['password'], data['confirm_password'])
        secret = self.authenticator.hash_password(data['password'])
        user = self.get_user(_id=_id)
        return self._update_entity(user, {"secret": secret}, ['secret'])
        
    def check_email(self, email):
        if not Authenticator.email_validation(email):
            raise ValueError('Invalid email')
        elif self.db.query(User).filter(User.email == email).first() is not None:
            raise ValueError(f'User with email {email} already exists')
        else:
            return
    
    def check_password(self, password, confirm_password):
        if len(password) < 8:
            raise ValueError('Password must be atleast 8 characters')
        elif password != confirm_password:
            raise ValueError("Passwords don't match")
        else:
            return
    
    def login_user(self, data):
        if not data.get('email'):
            raise ValueError('Email is required')
        if not data.get('password'):
            raise ValueError('Password is required')
        
        user = self.get_user(email=data['email'])
        authenticated = self.authenticator.authenticate_password(user.secret, data['password'])
        
        if not authenticated:
            raise ValueError("Invalid credentials")
        
        return user

    def logout_user(self, session):
        session.clear()
        return