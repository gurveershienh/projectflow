from sqlalchemy.orm import Query, Session

class BaseService:
    def __init__(self, db_session: Session, user_id):
        self.db = db_session
        self.user_id = user_id
    
    def _get_entity(self, query: Query):
        entity = query.first()
        if not entity:
            raise ValueError("Entity not found")
        return entity
        
    def _get_entities(self, query: Query):
        entities = query.all()
        return entities
        
    def _create_entity(self, instance):
        self.db.add(instance)
        self.db.flush()
        return instance

    def _delete_entity(self, instance):  
        self.db.delete(instance)
        self.db.flush()
        return
        
    def _update_entity(self, instance, data: dict, allowed_fields: list):
        for field in allowed_fields:
            if data.get(field) is not None:
                setattr(instance, field, data[field])
        return instance