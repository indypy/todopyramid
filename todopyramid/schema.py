from colander import MappingSchema
from colander import SchemaNode
from colander import String


class SettingsSchema(MappingSchema):
    first_name = SchemaNode(String())
    last_name = SchemaNode(String())
