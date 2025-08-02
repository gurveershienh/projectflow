from models import Project, Feature, Task, Note
from base import BaseService

class ProjectService(BaseService):
    def create_project(self, data: dict):
        if not data.get('name'):
            raise ValueError("Name not found")
        
        project = Project(
            name=data['name'],
            description=data.get('description'),
            parent_userid=self.user_id
        )
        return self._create_entity(project)
    
    def get_project(self, _id: int):
        query = self.db.query(Project).filter(Project.id == _id, Project.parent_userid == self.user_id)
        return self._get_entity(query)

    def get_projects(self):
        query = self.db.query(Project).filter(Project.parent_userid == self.user_id)
        return self._get_entities(query)
    
    def update_project(self, _id: int, data: dict):
        project = self.get_project(_id)
        return self._update_entity(project, data, ['name', 'description'])

    def delete_project(self, _id: int):
        project = self.get_project(_id)
        return self._delete_entity(project)
    
class FeatureService(BaseService):
    def create_feature(self, data: dict, project_id):
        if not data.get('name'):
            raise ValueError("Name is required")
        if not data.get('project_id'):
            raise ValueError("Project id is required")
        
        feature = Feature(
            name=data['name'],
            project_id=project_id,
            description=data.get('description'),
        )
        return self._create_entity(feature)
    
    def get_feature(self, _id: int):
        query = self.db.query(Feature).join(Project).filter(Feature.id == _id, Project.parent_userid == self.user_id)
        return self._get_entity(query)
    
    def get_features(self, project_id):
        query = self.db.query(Feature).join(Project).filter(Project.id == project_id, Project.parent_userid == self.user_id)
        return self._get_entities(query)
    
    def update_feature(self, _id: int, data: dict):
        feature = self.get_feature(_id)
        return self._update_entity(feature, data, ['name', 'description'])

    def delete_feature(self, _id: int):
        feature = self.get_feature(_id)
        return self._delete_entity(feature)

class TaskService(BaseService):
    def create_task(self, data: dict, feature_id):
        if not data.get('name'):
            raise ValueError("Name is required")
        
        task = Task(
            name=data['name'],
            feature_id=feature_id,
            description=data.get('description'),
            points=data.get('points'),
            completed=data.get('completed')
        )
        return self._create_entity(task)
    
    def get_task(self, _id: int):
        query = self.db.query(Task).join(Feature).join(Project).filter(Task.id == _id, Project.parent_userid == self.user_id)
        return self._get_entity(query)
    
    def get_tasks(self, feature_id):
        query = self.db.query(Task).join(Feature).join(Project).filter(Feature.id == feature_id, Project.parent_userid == self.user_id)
        return self._get_entities(query)
    
    def update_task(self, _id: int, data: dict):
        task = self.get_task(_id)
        return self._update_entity(task, data, ['name', 'description', 'points', 'completed'])

    def delete_task(self, _id: int):
        task = self.get_task(_id)
        return self._delete_entity(task)


class NoteService(BaseService):
    def create_note(self, data: dict, task_id):
        if not data.get('content'):
            raise ValueError("Content is required")
        
        task = Note(
            task_id=task_id,
            content=data['content']
        )
        return self._create_entity(task)
    
    def get_note(self, _id: int):
        query = self.db.query(Note).join(Task).join(Feature).join(Project).filter(Note.id == _id, Project.parent_userid == self.user_id)
        return self._get_entity(query)
    
    def get_notes(self, task_id):
        query = self.db.query(Note).join(Task).join(Feature).join(Project).filter(Task.id == task_id, Project.parent_userid == self.user_id)
        return self._get_entities(query)
    
    def update_note(self, _id: int, data: dict):
        note = self.get_note(_id)
        return self._update_entity(note, data, ['content'])

    def delete_note(self, _id: int):
        note = self.get_note(_id)
        return self._delete_entity(note)