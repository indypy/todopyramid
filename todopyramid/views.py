from pyramid.httpexceptions import HTTPFound
from pyramid.response import Response
from pyramid.security import authenticated_userid
from pyramid.security import remember
from pyramid.security import forget
from pyramid.settings import asbool
from pyramid.view import forbidden_view_config
from pyramid.view import notfound_view_config
from pyramid.view import view_config

from deform import Form
from deform import ValidationFailure
from peppercorn import parse
from pyramid_persona.views import verify_login
from sqlalchemy.exc import DBAPIError
import transaction

from .grid import TodoGrid
from .scripts.initializedb import create_dummy_content
from .layouts import Layouts
from .models import DBSession
from .models import Tag
from .models import TodoItem
from .models import TodoUser
from .schema import SettingsSchema
from .schema import TodoSchema
from .utils import universify_datetime


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

    def form_resources(self, form):
        resources = form.get_widget_resources()
        js_resources = resources['js']
        css_resources = resources['css']
        js_links = ['deform:static/%s' % r for r in js_resources]
        css_links = ['deform:static/%s' % r for r in css_resources]
        return (css_links, js_links)

    @notfound_view_config(renderer='templates/404.pt')
    def notfound(self):
        return {}

    @forbidden_view_config(renderer='templates/signin.pt')
    def forbidden(self):
        return {'section': 'login'}

    @view_config(route_name='about', renderer='templates/about.pt')
    def about_view(self):
        return {'section': 'about'}

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
        user = DBSession.query(TodoUser).filter(
            TodoUser.email == email).first()
        if user and user.profile_complete:
            self.request.session.flash('Logged in successfully')
            return HTTPFound(self.request.POST['came_from'], headers=headers)
        elif user and not user.profile_complete:
            msg = "Before you begin, please update your profile."
            self.request.session.flash(msg, queue='info')
            return HTTPFound('/account', headers=headers)
        # Otherwise, create an account and optionally create some content
        settings = self.request.registry.settings
        generate_content = asbool(
            settings.get('todopyramid.generate_content', None)
        )
        # Create the skeleton user
        with transaction.manager:
            DBSession.add(TodoUser(email))
            if generate_content:
                create_dummy_content(email)
        msg = (
            "This is your first visit, we hope your stay proves to be "
            "prosperous. Before you begin, please update your profile."
        )
        self.request.session.flash(msg)
        return HTTPFound('/account', headers=headers)

    @view_config(route_name='account', renderer='templates/account.pt',
                permission='view')
    def account_view(self):
        section_name = 'account'
        schema = SettingsSchema()
        form = Form(schema, buttons=('submit',))
        css_resources, js_resources = self.form_resources(form)
        if 'submit' in self.request.POST:
            controls = self.request.POST.items()
            try:
                form.validate(controls)
            except ValidationFailure as e:
                msg = 'There was an error saving your settings.'
                self.request.session.flash(msg, queue='error')
                return {
                    'form': e.render(),
                    'css_resources': css_resources,
                    'js_resources': js_resources,
                    'section': section_name,
                }
            values = parse(self.request.params.items())
            # Update the user
            with transaction.manager:
                self.user.first_name = values.get('first_name', u'')
                self.user.last_name = values.get('last_name', u'')
                self.user.time_zone = values.get('time_zone', u'US/Eastern')
                DBSession.add(self.user)
            self.request.session.flash(
                'Settings updated successfully',
                queue='success',
            )
            return HTTPFound('/list')
        # Get existing values
        if self.user is not None:
            appstruct = dict(
                first_name=self.user.first_name,
                last_name=self.user.last_name,
                time_zone=self.user.time_zone,
            )
        else:
            appstruct = {}
        return {
            'form': form.render(appstruct),
            'css_resources': css_resources,
            'js_resources': js_resources,
            'section': section_name,
        }

    @view_config(renderer='json', name='tags.autocomplete', permission='view')
    def tag_autocomplete(self):
        term = self.request.params.get('term', '')
        if len(term) < 2:
            return []
        # XXX: This is global tags, need to hook into "user_tags"
        tags = DBSession.query(Tag).filter(Tag.name.startswith(term)).all()
        return [
            dict(id=tag.name, value=tag.name, label=tag.name)
            for tag in tags
        ]

    @view_config(renderer='json', name='delete.task', permission='view')
    def delete_task(self):
        """Delete a todo list item

        TODO: Add a guard here so that you can only delete your tasks
        """
        todo_id = self.request.params.get('id', None)
        if todo_id is not None:
            todo_item = DBSession.query(TodoItem).filter(
                TodoItem.id == todo_id)
            with transaction.manager:
                todo_item.delete()
        return True

    @view_config(route_name='home', renderer='templates/home.pt')
    def home_view(self):
        if self.user_id is None:
            count = None
        else:
            count = len(self.user.todo_list.all())
        return {'user': self.user, 'count': count, 'section': 'home'}

    def sort_order(self):
        order = self.request.GET.get('order_col', 'due_date')
        order_dir = self.request.GET.get('order_dir', 'asc')
        if order == 'due_date':
            # handle sorting of NULL values so they are always at the end
            order = 'CASE WHEN due_date IS NULL THEN 1 ELSE 0 END, due_date'
        if order_dir:
            order = ' '.join([order, order_dir])
        return order

    def generate_add_form(self):
        schema = TodoSchema().bind(user_tz=self.user.time_zone)
        options = """
        {success:
          function (rText, sText, xhr, form) {
            deform.processCallbacks();
            deform.focusFirstInput();
            var loc = xhr.getResponseHeader('X-Relocate');
            if (loc) {
              document.location = loc;
            };
           }
        }
        """
        return Form(
            schema,
            buttons=('submit',),
            use_ajax=True,
            ajax_options=options,
        )

    def process_add_form(self, form):
        try:
            # try to validate the submitted values
            controls = self.request.POST.items()
            captured = form.validate(controls)
            with transaction.manager:
                tags = captured.get('tags', [])
                if tags:
                    tags = tags.split(',')
                due_date = captured.get('due_date')
                if due_date is not None:
                    # Convert back to UTC for storage
                    due_date = universify_datetime(due_date)
                task_name = captured.get('name')
                task = TodoItem(
                    user=self.user_id,
                    task=task_name,
                    tags=tags,
                    due_date=due_date,
                )
                DBSession.add(task)
            msg = "New task '%s' created successfully" % task_name
            self.request.session.flash(
                msg,
                queue='success',
            )
            # Reload the page we were on
            location = self.request.url
            return Response(
                '',
                headers=[
                    ('X-Relocate', location),
                    ('Content-Type', 'text/html'),
                ]
            )
            html = form.render({})
        except ValidationFailure as e:
            # the submitted values could not be validated
            html = e.render()
        return Response(html)

    @view_config(route_name='list', renderer='templates/todo_list.pt',
                permission='view')
    def list_view(self):
        form = self.generate_add_form()
        if 'submit' in self.request.POST:
            return self.process_add_form(form)
        order = self.sort_order()
        todo_items = self.user.todo_list.order_by(order).all()
        grid = TodoGrid(
            self.request,
            None,
            self.user.time_zone,
            todo_items,
            ['task', 'tags', 'due_date', ''],
        )
        count = len(todo_items)
        item_label = 'items' if count > 1 or count == 0 else 'item'
        css_resources, js_resources = self.form_resources(form)
        return {
            'page_title': 'Todo List',
            'count': count,
            'item_label': item_label,
            'section': 'list',
            'items': todo_items,
            'grid': grid,
            'form': form.render(),
            'css_resources': css_resources,
            'js_resources': js_resources,
        }

    @view_config(route_name='tags', renderer='templates/todo_tags.pt',
                permission='view')
    def tags_view(self):
        tags = self.user.user_tags
        return {
            'section': 'tags',
            'count': len(tags),
            'tags': tags,
        }

    @view_config(route_name='tag', renderer='templates/todo_list.pt',
                 permission='view')
    def tag_view(self):
        form = self.generate_add_form()
        if 'submit' in self.request.POST:
            return self.process_add_form(form)
        order = self.sort_order()
        qry = self.user.todo_list.order_by(order)
        tag_name = self.request.matchdict['tag_name']
        tag_filter = TodoItem.tags.any(Tag.name.in_([tag_name]))
        todo_items = qry.filter(tag_filter)
        count = todo_items.count()
        item_label = 'items' if count > 1 or count == 0 else 'item'
        grid = TodoGrid(
            self.request,
            tag_name,
            self.user.time_zone,
            todo_items,
            ['task', 'tags', 'due_date', ''],
        )
        css_resources, js_resources = self.form_resources(form)
        return {
            'page_title': 'Tag List',
            'count': count,
            'item_label': item_label,
            'section': 'tags',
            'tag_name': tag_name,
            'items': todo_items,
            'grid': grid,
            'form': form.render({'tags': tag_name}),
            'css_resources': css_resources,
            'js_resources': js_resources,
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
