from sqlalchemy.types import Binary

class Uuid(types.TypeDecorator):
    impl = Binary

def id_column():
    import uuid
    return Column(id_column_name,UUID(),primary_key=True,default=uuid.uuid4)