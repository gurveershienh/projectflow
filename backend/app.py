import secrets
from typing import Tuple
from flask import Flask, g, jsonify, request, session, Response
from db import create_database, LocalSession
from models import Project, User, Feature, Task, Note
from auth import Authenticator


app = Flask(__name__)
app.config['SECRET_KEY'] = secrets.token_hex(16)

authentication = Authenticator()

create_database()

#runs before every request to create db session
@app.before_request
def create_session():
    g.db = LocalSession()

#runs when application context is popped (e.g after request context)
@app.teardown_appcontext
def close_session(error):
    db = g.pop('db', None)
    if db is not None:
        if error:
            db.rollback()
        else:
            db.commit()
        db.close()

@app.route("/")
def home():
    return """
    <h1>Welcome to the Project Tracker</h1>
"""

@app.route("/signup", methods=['POST'])
def user_signup() -> Tuple[Response, int]:
    data = request.get_json()
    if not data['name']:
        return (
            jsonify({'error': 'Name is required'}),
            400
        )
    if not data['email']:
        return (
            jsonify({'error': 'Email is required'}),
            400
        )
    if not data['password']:
        return (
            jsonify({'error': 'Password is required'}),
            400
        )
    if not data['confirm_password']:
        return (
            jsonify({'error': 'Password confirmation is required'}),
            400
        )
    if len(data['password']) < 8:
        return (
            jsonify({'error': 'Password needs to be atleast 8 characters'}),
            400
        )       
    if data['password'] != data['confirm_password']:
        return (
            jsonify({'error': 'Passwords do not match'}),
            400
        )

    if not Authenticator.email_validation(data['email']):
        return (
            jsonify({'error': 'Invalid email address'}),
            400
        )
    
    if g.db.query(User).filter(User.email == data['email']).first() is not None:
        return (
            jsonify({'error': f"Account with {data['email']} already exists"}),
            400
        )
    secret = authentication.hash_password(data['password'])
    
    try:
        user_account = User(
            email=data['email'],
            name=data['name'],
            secret=secret
        )
        g.db.add(user_account)
        g.db.flush()
        return (
            jsonify({'message': f"User {user_account.name} signed up with {user_account.email}"}),
            201
        )
    except Exception as e:
        return (
            jsonify({'error': str(e)}),
            400
        )

@app.route('/login', methods=['POST'])
def login() -> Tuple[Response, int]:
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    if not email or not password:
        return (
            jsonify({'error': 'Email and password are required'}),
            400
        )
    user = g.db.query(User).filter(User.email == email).first()

    if not user:
        return (
            jsonify({'error': "Invalid credentials"}),
            401
        )
    
    try:
        authenticated = authentication.authenticate_password(user.secret, password)
        if not authenticated:
            return (
                jsonify({'error': "Invalid credentials"}),
                401
            )  
        else:
            session['user_id'] = user.id
            session['user_email'] = email
            return (
                jsonify({'message': f"User {user.name} logged in successfully!"}),
                200
            )
    except Exception as e:
        return (
            jsonify({"error": str(e)}),
            400
        ) 


@app.route("/health")
def health():
    return {"status": "healthy"}

@app.route("/projects", methods=['GET'])
@Authenticator.authenticate_session
def view_projects() -> Tuple[Response, int]:
    try:
        user_id = session['user_id']
        projects = g.db.query(Project).filter(Project.parent_userid == user_id).all()
        return (
            jsonify([{'id': p.id, 'name': p.name, 'desc': p.description} for p in projects]),
            200
        )
    except Exception as e:
        return (
            jsonify({"error": str(e)}),
            400
        ) 


@app.route("/projects", methods=['POST'])
@Authenticator.authenticate_session
def create_new_project() -> Tuple[Response, int]:
    data = request.get_json()

    try:
        user_id = session['user_id']
        project = Project(
            name=data['name'],
            description=data.get('description'),
            parent_userid=user_id
        )

        g.db.add(project)
        g.db.flush()
        return (
            jsonify({'id': project.id, 'parent_userid': user_id, 'name': project.name, 'description': project.description}), 
            201
            )
    except Exception as e:
        return (
            jsonify({"error": str(e)}),
            400
        )

@app.route("/projects/<int:project_id>", methods=['DELETE'])
@Authenticator.authenticate_session
def delete_project(project_id) -> Tuple[Response, int]:
    try:
        user_id=session['user_id']
        project = g.db.query(Project).filter(Project.id == project_id, Project.parent_userid == user_id).first()
        if not project:
            return (
                jsonify({"error": "project_id not found"}),
                404
            )
        project_name = project.name
        g.db.delete(project)
        g.db.flush()
        return (
            jsonify({'message': f"{project_name} deleted"}),
            200
        )
    except Exception as e:
        return (
            jsonify({"error": str(e)}),
            400
        )

@app.route("/projects/<int:project_id>/features", methods=['GET'])
@Authenticator.authenticate_session
def get_project_features(project_id) -> Tuple[Response, int]:
    try:
        project = g.db.query(Project).filter(Project.id == project_id).first()
        feature_list = [{'id':f.id, 'name':f.name, 'description':f.description} for f in project.feature_list]
        if not project:
            return (
                jsonify({"error": "project_id not found"}),
                404
            )
        return (
            jsonify({'project_id': project.id, 'project_name': project.name, 'feature_list': feature_list}),
            200
        )
    except Exception as e:
        return (
            jsonify({'error': str(e)}),
            400
        )

@app.route("/projects/<int:project_id>/features", methods=['POST'])
@Authenticator.authenticate_session
def add_feature_to_project(project_id) -> Tuple[Response, int]:
    data = request.get_json()

    try:
        feature = Feature(
            name=data['name'],
            project_id=project_id,
            description=data.get('description'),
            priority=data.get('priority'),
        )
        g.db.add(feature)
        g.db.flush()
        return (
            jsonify({'msg': f'Feature {feature.name} added to project {feature.parent_project.name}'}),
            200
        )
    except Exception as e:
        return (
            jsonify({'error': str(e)}),
            400
        )
if __name__ == "__main__":
    app.run(debug=True, port=5001)