from colander import MappingSchema
from colander import SchemaNode
from colander import String
from colander import Integer
from colander import DateTime
from colander import deferred
from deform.widget import HiddenWidget
from deform.widget import SelectWidget
from deform_bootstrap_extra.widgets import TagsWidget
from pytz import all_timezones
from pytz import timezone


class SettingsSchema(MappingSchema):
    first_name = SchemaNode(String())
    last_name = SchemaNode(String())
    time_zone = SchemaNode(
        String(),
        default=u'US/Eastern',
        widget=SelectWidget(
            values=zip(all_timezones, all_timezones),
        ),
    )


@deferred
def deferred_datetime_node(node, kw):
    tz = timezone(kw['user_tz'])
    return DateTime(default_tzinfo=tz)


class TodoSchema(MappingSchema):
    id = SchemaNode(
        Integer(),
        missing=None,
        widget=HiddenWidget(),
    )
    name = SchemaNode(String())
    tags = SchemaNode(
        String(),
        widget=TagsWidget(
            autocomplete_url='/tags.autocomplete',
        ),
        description=(
            "Enter a comma after each tag to add it. Backspace to delete."
        ),
        missing=[],
    )
    due_date = SchemaNode(
        deferred_datetime_node,
        missing=None,
    )
