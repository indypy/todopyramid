from pyramid.httpexceptions import HTTPFound
from pyramid.response import Response
from pyramid.security import authenticated_userid
from pyramid.security import remember
from pyramid.security import forget
from pyramid.view import forbidden_view_config
from pyramid.view import notfound_view_config
from pyramid.view import view_config

from pyramid_persona.views import verify_login
from sqlalchemy.exc import DBAPIError
import transaction

from .layouts import Layouts
from .models import DBSession
from .models import Tag
from .models import TodoItem
from .models import TodoUser


class ToDoViews(Layouts):

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.user_id = authenticated_userid(request)
        self.todo_list = []
        self.user = None
        if self.user_id is not None:
            try:
                self.user = DBSession.query(TodoUser).filter(
                    TodoUser.email == self.user_id).first()
            except DBAPIError:
                # We'll add this DB error exception here to let people
                # know they need to run the script
                return Response(
                    conn_err_msg, content_type='text/plain', status_int=500)

    def pretty_date(self, item_date):
        """Shoehorn the moment.js code into the template. Based on this
        blog: http://blog.miguelgrinberg.com/
        """
        fmt_date = item_date.strftime('%Y-%m-%dT%H:%M:%S Z')
        return """
<script>
  document.write(moment("%s").calendar());
</script>""" % fmt_date

    @notfound_view_config(renderer='templates/404.pt')
    def notfound(self):
        return {}

    @forbidden_view_config(renderer='templates/signin.pt')
    def forbidden(self):
        return {}

    @view_config(route_name='logout', check_csrf=True)
    def logout(self):
        headers = forget(self.request)
        # Send the user back home, everything else is protected
        return HTTPFound('/', headers=headers)

    @view_config(route_name='login', check_csrf=True)
    def login_view(self):
        email = verify_login(self.request)
        headers = remember(self.request, email)
        # Check to see if the user exists
        if not DBSession.query(TodoUser).filter(TodoUser.email == email).all():
            # Create the skeleton user
            with transaction.manager:
                DBSession.add(TodoUser(email))
            msg = (
                "This is your first visit, we hope your stay proves to be "
                "prosperous. Before you begin, please update your profile."
            )
            self.request.session.flash(msg)
            return HTTPFound('/account', headers=headers)
        self.request.session.flash('Logged in successfully')
        return HTTPFound(self.request.POST['came_from'], headers=headers)

    @view_config(route_name='account', renderer='templates/account.pt',
                permission='view')
    def account_view(self):
        return {}

    @view_config(route_name='home', renderer='templates/home.pt')
    def home_view(self):
        try:
            count = DBSession.query(TodoItem).count()
        except DBAPIError:
            return Response(
                conn_err_msg, content_type='text/plain', status_int=500)
        return {'count': count, 'section': 'home'}

    @view_config(route_name='list', renderer='templates/todo_list.pt',
                permission='view')
    def list_view(self):
        todo_items = DBSession.query(TodoItem).order_by(
            'due_date IS NULL').all()
        count = len(todo_items)
        item_label = 'items' if count > 1 else 'item'
        return {
            'page_title': 'Todo List',
            'subtext': '%s %s remaining' % (count, item_label),
            'section': 'list',
            'items': todo_items,
        }

    @view_config(route_name='tags', renderer='templates/todo_tags.pt',
                permission='view')
    def tags_view(self):
        tags = DBSession.query(Tag).order_by('name').all()
        return {
            'section': 'tags',
            'count': len(tags),
            'tags': tags,
        }

    @view_config(route_name='tag', renderer='templates/todo_list.pt',
                 permission='view')
    def tag_view(self):
        tag_name = self.request.matchdict['tag_name']
        todo_items = DBSession.query(
            TodoItem).order_by('due_date IS NULL').filter(
            TodoItem.tags.any(Tag.name.in_([tag_name])))
        count = todo_items.count()
        item_label = 'items' if count > 1 else 'item'
        subtext = '%s %s matching <span class="label label-warning">%s</span>'
        return {
            'page_title': 'Tag List',
            'subtext':  subtext % (count, item_label, tag_name),
            'section': 'tags',
            'tag_name': tag_name,
            'items': todo_items,
        }

conn_err_msg = """\
Pyramid is having a problem using your SQL database.  The problem
might be caused by one of the following things:

1.  You may need to run the "initialize_todopyramid_db" script
    to initialize your database tables.  Check your virtual
    environment's "bin" directory for this script and try to run it.

2.  Your database server may not be running.  Check that the
    database server referred to by the "sqlalchemy.url" setting in
    your "development.ini" file is running.

After you fix the problem, please restart the Pyramid application to
try it again.
"""
