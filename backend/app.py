import secrets
from typing import Tuple
from flask import Flask, g, jsonify, request, session, Response
from db import create_database, LocalSession
from models import Project, User, Feature, Task, Note
from sqlalchemy.orm import selectinload
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
    if not data.get('name'):
        return (
            jsonify({'error': 'Name is required'}),
            400
        )
    if not data.get('email'):
        return (
            jsonify({'error': 'Email is required'}),
            400
        )
    if not data.get('password'):
        return (
            jsonify({'error': 'Password is required'}),
            400
        )
    if not data.get('confirm_password'):
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

@app.route('/logout', methods=['POST'])
@Authenticator.authenticate_session
def logout() -> Tuple[Response, int]:
    try:
        session.clear()
        return (
            jsonify({'message': 'Successfully logged out'}),
            200
        )
    except Exception as e:
        return (
            jsonify({'error': str(e)}),
            400
        )
    
@app.route("/user/dashboard", methods=['GET'])
@Authenticator.authenticate_session
def load_user_dashboard() -> Tuple[Response, int]:
    try:
        user_id = session['user_id']
        #eager load user dashboard data
        projects = g.db.query(Project).options(
        selectinload(Project.feature_list)
        .selectinload(Feature.task_list)
        .selectinload(Task.work_notes)
    ).filter(Project.parent_userid == user_id).all()
        
        dashboard_data = []
        for project in projects:
            feature_list = []
            project_dict = dict(id=project.id, name=project.name, description=project.description, progress=project.progress)
            
            for feature in project.feature_list:
                task_list = []
                feature_dict = dict(id=feature.id, name=feature.name, description=feature.description, progress=feature.progress)
                
                for task in feature.task_list:
                    note_list = []
                    task_dict = dict(id=task.id, name=task.name, points=task.points, completed=task.completed)
                    
                    for note in task.work_notes:
                        note_dict = dict(id=note.id, content=note.content, created_at=note.created_at)
                        note_list.append(note_dict)
                    
                    task_dict['notes'] = note_list
                    task_list.append(task_dict)

                feature_dict['tasks'] = task_list
                feature_list.append(feature_dict)

            project_dict['features'] = feature_list
            dashboard_data.append(project_dict)

        return (    
            jsonify({"projects": dashboard_data}),
            200
        )
    except Exception as e:
        return (
            jsonify({"error": str(e)}),
            400
        ) 

@app.route("/projects", methods=['POST'])
@Authenticator.authenticate_session
def add_project() -> Tuple[Response, int]:
    data = request.get_json()
    user_id= session['user_id']
    if data.get('name') is None:
        return (
            jsonify({'error': 'name is required'}),
            400
        )
    try:
        project = Project(
            name=data['name'],
            description=data.get('description'),
            parent_userid=user_id
        )

        g.db.add(project)
        g.db.flush()
        return (
            jsonify({'project': {'id': project.id, 'parent_userid': user_id, 'name': project.name, 'description': project.description}}), 
            201
            )
    except Exception as e:
        return (
            jsonify({"error": str(e)}),
            400
        )

@app.route("/projects/<int:project_id>", methods=['GET','PATCH','DELETE'])
@Authenticator.authenticate_session
def handle_project(project_id) -> Tuple[Response, int]:
    user_id=session['user_id']
    try:
        project = g.db.query(Project).filter(Project.id == project_id, Project.parent_userid == user_id).first()
        if not project:
            return (
                jsonify({"error": "project_id not found"}),
                404
            )
        if request.method == 'DELETE':

            project_name = project.name
            g.db.delete(project)
            g.db.flush()
            return (
                jsonify({'msg': f"{project_name} deleted"}),
                200
            )
        
        elif request.method == 'PATCH':
            data = request.get_json()
            project.name = data.get('name') if data.get('name') is not None else project.name
            project.description = data.get('description') if data.get('description') is not None else project.description
            g.db.flush()
            return (
                jsonify({"project": {"id": project.id, "name": project.name, "description": project.description}}),
                200
            )
        elif request.method == 'GET':
            return (
                jsonify({"project": {"id": project.id, "name": project.name, "description": project.description}}),
                200
            )
        else:
            return (
                jsonify({"error": "invalid http method"}),
                400
            )
        
    except Exception as e:
        return (
            jsonify({"error": str(e)}),
            400
        )

@app.route("/projects/<int:project_id>/features", methods=['POST'])
@Authenticator.authenticate_session
def add_feature(project_id) -> Tuple[Response, int]:
    data = request.get_json()
    user_id = session['user_id']
    
    if data.get('name') is None:
        return (
            jsonify({'error': 'name is required'}),
            400
        )
    
    project = g.db.query(Project).filter(Project.parent_userid ==  user_id, Project.id == project_id).first()
    if not project:
        return (
            jsonify({"error": "project not found"}),
            404
        )
    
    try:
        feature = Feature(
            name=data['name'],
            project_id=project_id,
            description=data.get('description'),
        )
        g.db.add(feature)
        g.db.flush()
        return (
            jsonify({'feature': {'id':feature.id, 'project_id': feature.project_id, 'name': feature.name, 'description': feature.description}}),
            201
        )
    except Exception as e:
        return (
            jsonify({'error': str(e)}),
            400
        )

@app.route("/features/<int:feature_id>", methods=['GET','DELETE', 'PATCH'])
@Authenticator.authenticate_session
def handle_feature(feature_id) -> Tuple[Response, int]:
    user_id = session['user_id']
    try:
        feature = g.db.query(Feature).join(Project).filter(Feature.id == feature_id, Project.parent_userid == user_id).first()
        
        if not feature:
            return (
                jsonify({'error': 'feature not found'}),
                404
            )
        
        if request.method == 'DELETE':
            g.db.delete(feature)
            g.db.flush()

            return (
                jsonify({'message': 'feature deleted'}),
                200
            )
        
        elif request.method == 'PATCH':
            data = request.get_json()
            feature.name = data['name'] if data.get('name') is not None else feature.name
            feature.description = data['description'] if data.get('description') is not None else feature.description
            g.db.flush()
            return (
                jsonify({'feature': {'id':feature.id, 'project_id': feature.project_id, 'name': feature.name, 'description': feature.description}}),
                200
            )
        elif request.method == 'GET':
            return (
                jsonify({'feature': {'id':feature.id, 'project_id': feature.project_id, 'name': feature.name, 'description': feature.description}}),
                200
            )
        else:
            return (
                jsonify({"error": "invalid http method"}),
                400
            )
    except Exception as e:
        return (
            jsonify({'error': str(e)}),
            400
        )

@app.route("/features/<int:feature_id>/tasks", methods=['POST'])
@Authenticator.authenticate_session
def add_task(feature_id) -> Tuple[Response, int]:
    data = request.get_json()
    user_id = session['user_id']
    
    if data.get('name') is None:
        return (
            jsonify({'error': 'name is required'}),
            400
        )
    
    feature = g.db.query(Feature).join(Project).filter(Feature.id == feature_id, Project.parent_userid == user_id).first()
    if not feature:
        return (
            jsonify({"error": "feature not found"}),
            404
        )

    try:
        task = Task(
            name=data['name'],
            feature_id=feature_id,
            description=data.get('description'),
            points=data.get('points')
        )

        g.db.add(task)
        g.db.flush()
        return (
            jsonify({'task': {'id':task.id, 'feature_id': task.feature_id, 'name': task.name, 'description': task.description}}),
            201
        )
    except Exception as e:
        return (
            jsonify({'err': str(e)}),
            400
        )

@app.route("/tasks/<int:task_id>", methods=['GET', 'DELETE', 'PATCH'])
@Authenticator.authenticate_session
def handle_task(task_id) -> Tuple[Response, int]:
    user_id = session['user_id']
    try:
        task = g.db.query(Task).join(Feature).join(Project).filter(Task.id == task_id, Project.parent_userid == user_id).first()

        if not task:
            return (
                jsonify({"error": "task not found"}),
                404
            )
        
        if request.method == 'DELETE':
            g.db.delete(task)
            g.db.flush()
            return (
                jsonify({"message": "task deleted"}),
                200
            )
        elif request.method == 'PATCH':
            data = request.get_json()
            task.name = data['name'] if data.get('name') is not None else task.name
            task.description = data['description'] if data.get('description') is not None else task.description
            task.points = data['points'] if data.get('points') is not None else task.points
            task.completed = data['completed'] if data.get('completed') is not None else task.completed

            g.db.flush()

            return (
                jsonify({'task': {'id':task.id, 'feature_id': task.feature_id, 'name': task.name, 'description': task.description}}),
                200
            )
        elif request.method == 'GET':
            return (
                jsonify({'task': {'id':task.id, 'feature_id': task.feature_id, 'name': task.name, 'description': task.description}}),
                200
            )
        else:
            return (
                jsonify({"error": "invalid http method"}),
                400
            )
    except Exception as e:
        return (
            jsonify({'err': str(e)}),
            400
        )
    
@app.route("/tasks/<int:task_id>/notes", methods=['POST'])
@Authenticator.authenticate_session
def add_note(task_id) -> Tuple[Response, int]:
    data = request.get_json()
    user_id = session['user_id']
    if not data.get('content'):
        return (
            jsonify({'error': 'Content is required'}), 
            400
        )

    task = g.db.query(Task).join(Feature).join(Project).filter(Task.id == task_id, Project.parent_userid == user_id).first()
    
    if not task:
        return (
            jsonify({'error': 'task not found'}),
            404
        )
    
    try:
        note = Note(
            task_id=task_id,
            content=data["content"]
        )

        g.db.add(note)
        g.db.flush()
        return (
            jsonify({"note": {"id": note.id, "task_id": task_id, "content": note.content}}),
            201
        )
    
    except Exception as e:
        return (
            jsonify({"error": str(e)}),
            400
        )
    
@app.route("/notes/<int:note_id>", methods=['GET','PATCH', 'DELETE'])
@Authenticator.authenticate_session
def handle_note(note_id) -> Tuple[Response, int]:
    user_id = session['user_id']
    try:
        note = g.db.query(Note).join(Task).join(Feature).join(Project).filter(Note.id == note_id, Project.parent_userid == user_id).first()

        if not note:
            return (
                jsonify({"error": "note not found"}),
                404
            )
        
        if request.method == 'DELETE':
            g.db.delete(note)
            g.db.flush()
            return (
                jsonify({"message": "note deleted"}),
                200
            )
        elif request.method == 'PATCH':
            data = request.get_json()
            note.content = data['content'] if data.get('content') is not None else note.content
            g.db.flush()
            return (
                jsonify({"note": {"id": note.id, "task_id": note.task_id, "content": note.content}}),
                200
            )
        elif request.method == 'GET':
            return (
                jsonify({"note": {"id": note.id, "task_id": note.task_id, "content": note.content}}),
                200
            )   
        else:
            return (
                jsonify({"error": "invalid http method"}),
                400
            )
    except Exception as e:
        return (
            jsonify({'err': str(e)}),
            400
        )
   
if __name__ == "__main__":
    app.run(debug=True, port=5001)