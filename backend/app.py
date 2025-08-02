import logging
import secrets
from typing import Tuple
from flask import Flask, g, jsonify, request, session, Response
from db import create_database, LocalSession
from models import Project, User, Feature, Task, Note
from auth import Authenticator, AuthenticationError, AuthorizationError
from services.user import UserService
from services.project import ProjectService, FeatureService, TaskService, NoteService

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

@app.errorhandler(ValueError)
def handle_value_error(e):
    return (
        jsonify({"error": str(e)}),
        400
    )
@app.errorhandler(AuthenticationError)
def handle_authentication_error(e):
    return (
        jsonify({"error": str(e)}),
        401
    )
@app.errorhandler(AuthorizationError)
def handle_authorization_error(e):
    return (
        jsonify({"error": str(e)}),
        403
    )

@app.errorhandler(Exception)
def handle_general_error(e):
    logging.error(f"Unexpected error in {request.endpoint}: {str(e)}", exc_info=True)
    return (
        jsonify({"error": str(e)}),
        500
    )
@app.route("/")
def home():
    return """
    <h1>Welcome to the Project Tracker</h1>
"""

@app.route("/signup", methods=['POST'])
def user_signup() -> Tuple[Response, int]:
    data = request.get_json()
    user_service = UserService.for_public(g.db)
    user = user_service.create_user(data)
    response_data = {"name": user.name, "email": user.email}
    return (
        jsonify({"user created": response_data}),
        201
    )
@app.route("/login", methods=['POST'])
def user_login() -> Tuple[Response, int]:
    data = request.get_json()
    user_service = UserService.for_public(g.db)
    user = user_service.login_user(data)
    session['user_id'] = user.id
    session['user_email'] = user.email
    response_data = {"name": user.name, "email": user.email}
    return (
        jsonify({"user logged in": response_data}),
        200
    )

@app.route("/users/<int:user_id>/change_password", methods=['PATCH'])
@Authenticator.authenticate_session
@Authenticator.check_authorization
def change_user_password(user_id) -> Tuple[Response, int]:
    data = request.get_json()
    user_service = UserService.for_user(g.db, user_id)
    user_service.change_user_password(user_id, data)
    return (
        jsonify({"Password changed successfully"}),
        204
    )

@app.route("/users/<int:user_id>/change_email", methods=['PATCH'])
@Authenticator.authenticate_session
@Authenticator.check_authorization
def change_user_email(user_id) -> Tuple[Response, int]:
    data = request.get_json()
    user_service = UserService.for_user(g.db, user_id)
    user_service.change_user_email(user_id, data)
    return (
        jsonify({"Email changed successfully"}),
        204
    )

@app.route("/projects", methods=['POST', 'GET'])
@Authenticator.authenticate_session
def handle_projects_route():
    project_service = ProjectService(g.db, session['user_id'])

    if request.method == 'GET':
        projects = project_service.get_projects()
        response_data = [
            {'id': p.id, 'name': p.name, 'description': p.description, 'created_at': p.created_at} 
            for p in projects
            ]
        return (
            jsonify({"projects": response_data}),
            200
        )
    
    elif request.method == 'POST':
        data = request.get_json()
        p = project_service.create_project(data)
        response_data = {'id': p.id, 'name': p.name, 'description': p.description, 'created_at': p.created_at}
        return (
            jsonify({"new_project": response_data}),
            201
        )
    
    else:
        return jsonify({"error": "Method not allowed"}), 405 #only adding to make typechecker happy :/

@app.route("/projects/<int:project_id>", methods=['GET', 'PATCH', 'DELETE'])
@Authenticator.authenticate_session
def handle_project_route(project_id):
    project_service = ProjectService(g.db, session['user_id'])

    if request.method == 'GET':
        p =  project_service.get_project(project_id)
        response_data = {'id': p.id, 'name': p.name, 'description': p.description, 'created_at': p.created_at}
        return (
            jsonify({"project": response_data}),
            200
        )
    elif request.method == 'PATCH':
        data = request.get_json()
        p = project_service.update_project(project_id, data)
        response_data = {'id': p.id, 'name': p.name, 'description': p.description, 'created_at': p.created_at, 'updated_at': p.updated_at}
        return (
            jsonify({"project": response_data}),
            200
        )
    elif request.method == 'DELETE':
        project_service.delete_project(project_id)
        return (
            jsonify({"project_deleted": project_id}),
            200
        )
    
    else:
        return jsonify({"error": "Method not allowed"}), 405 #only adding to make typechecker happy :/
    
@app.route("/projects/<int:project_id/features", methods=['GET', 'POST'])
@Authenticator.authenticate_session
def handle_features_route(project_id):
    feature_service = FeatureService(g.db, session['user_id'])

    if request.method == 'GET':
        features = feature_service.get_features(project_id)
        response_data = [
            {"id": f.id, "name": f.name, "description": f.description, "created_at": f.created_at}
            for f in features
        ]
        return (
            jsonify({'features':response_data}),
            200
        )
    elif request.method == 'POST':
        data = request.get_json()
        f = feature_service.create_feature(data, project_id)
        response_data = {"id": f.id, "name": f.name, "description": f.description, "created_at": f.created_at}
        return (
            jsonify({'feature':response_data}),
            201
        )
    
    else:
        return jsonify({"error": "Method not allowed"}), 405 
@app.route("/features/<int:feature_id", methods=['GET', 'PATCH', 'DELETE'])
@Authenticator.authenticate_session
def handle_feature_route(feature_id):
    feature_service = FeatureService(g.db, session['user_id'])

    if request.method == 'GET':
        f = feature_service.get_feature(feature_id)
        response_data = {"id": f.id, "name": f.name, "description": f.description, "created_at": f.created_at}
        return (
            jsonify({'feature':response_data}),
            200
        )
    elif request.method == 'PATCH':
        data = request.get_json()
        f = feature_service.update_feature(feature_id,data)
        response_data = {"id": f.id, "name": f.name, "description": f.description, "created_at": f.created_at, "updated_at": f.updated_at}
        return (
            jsonify({"feature": response_data}),
            200
        )
    elif request.method == 'DELETE':
        feature_service.delete_feature(feature_id)
        return (
            jsonify({"feature_deleted": feature_id}),
            200
        )
    else:
        return jsonify({"error": "Method not allowed"}), 405
    
@app.route("/features/<int:feature_id/tasks", methods=['GET', 'POST'])
@Authenticator.authenticate_session
def handle_tasks_route(feature_id):
    task_service = TaskService(g.db, session['user_id'])

    if request.method == 'GET':
        tasks = task_service.get_tasks(feature_id)
        response_data = [
            {'id': t.id, 'name': t.name, 'description': t.description, 'points': t.points, 'completed': t.completed, 'created_at': t.created_at}
            for t in tasks
        ]
        return (
            jsonify({'tasks': response_data}),
            200
        )
    elif request.method == 'POST':
        data = request.get_json()
        t = task_service.create_task(data, feature_id)
        response_data = {'id': t.id, 'name': t.name, 'description': t.description, 'points': t.points, 'completed': t.completed, 'created_at': t.created_at}
        return (
            jsonify({'task':response_data}),
            201
        )
    
    else:
        return jsonify({"error": "Method not allowed"}), 405 

@app.route("/tasks/<int:task_id>", methods=['GET', 'PATCH', 'DELETE'])
@Authenticator.authenticate_session
def handle_task_route(task_id):
    task_service = TaskService(g.db, session['user_id'])

    if request.method == 'GET':
        t = task_service.get_task(task_id)
        response_data = {'id': t.id, 'name': t.name, 'description': t.description, 'points': t.points, 'completed': t.completed, 'created_at': t.created_at}
        return (
            jsonify({'task': response_data}),
            200
        )
    elif request.method == 'PATCH':
        data = request.get_json()
        t = task_service.update_task(task_id, data)
        response_data = {'id': t.id, 'name': t.name, 'description': t.description, 'points': t.points, 'completed': t.completed, 'created_at': t.created_at, 'updated_at': t.updated_at}
        return (
            jsonify({'task': response_data}),
            200
        )
    elif request.method == 'DELETE':
        task_service.delete_task(task_id)
        return (
            jsonify({"task_deleted": task_id}),
            200
        )
    else:
        return jsonify({"error": "Method not allowed"}), 405

@app.route("/tasks/<int:task_id>/notes", methods=['GET', 'POST'])
@Authenticator.authenticate_session
def handle_notes_route(task_id):
    note_service = NoteService(g.db, session['user_id'])

    if request.method == 'GET':
        notes = note_service.get_notes(task_id)
        response_data = [
            {'id': n.id, 'content': n.content, 'created_at': n.created_at}
            for n in notes
        ]
        return (
            jsonify({'notes': response_data}),
            200
        )
    elif request.method == 'POST':
        data = request.get_json()
        n = note_service.create_note(data, task_id)
        response_data = {'id': n.id, 'content': n.content, 'created_at': n.created_at}
        return (
            jsonify({'note': response_data}),
            201
        )
    else:
        return jsonify({"error": "Method not allowed"}), 405

@app.route("/notes/<int:note_id>", methods=['GET', 'PATCH', 'DELETE'])
@Authenticator.authenticate_session
def handle_note_route(note_id):
    note_service = NoteService(g.db, session['user_id'])

    if request.method == 'GET':
        n = note_service.get_note(note_id)
        response_data = {'id': n.id, 'content': n.content, 'created_at': n.created_at}
        return (
            jsonify({'note': response_data}),
            200
        )
    elif request.method == 'PATCH':
        data = request.get_json()
        n = note_service.update_note(note_id, data)
        response_data = {'id': n.id, 'content': n.content, 'created_at': n.created_at}
        return (
            jsonify({'note': response_data}),
            200
        )
    elif request.method == 'DELETE':
        note_service.delete_note(note_id)
        return (
            jsonify({"note_deleted": note_id}),
            200
        )
    else:
        return jsonify({"error": "Method not allowed"}), 405
    
if __name__ == "__main__":
    app.run(debug=True, port=5001)