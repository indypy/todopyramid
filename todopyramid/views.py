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
from .utils import localize_datetime
from .utils import universify_datetime


class ToDoViews(Layouts):
    """This class has all the views for our application. The Layouts
    base class has the master template set up.
    """

    def __init__(self, context, request):
        """Set some common variables needed for each view.
        """
        self.context = context
        self.request = request
        self.user_id = authenticated_userid(request)
        self.todo_list = []
        self.user = None
        if self.user_id is not None:
            query = DBSession.query(TodoUser)
            self.user = query.filter(TodoUser.email == self.user_id).first()

    def form_resources(self, form):
        """Get a list of css and javascript resources for a given form.
        These are then used to place the resources in the global layout.
        """
        resources = form.get_widget_resources()
        js_resources = resources['js']
        css_resources = resources['css']
        js_links = ['deform:static/%s' % r for r in js_resources]
        css_links = ['deform:static/%s' % r for r in css_resources]
        return (css_links, js_links)

    def sort_order(self):
        """The list_view and tag_view both use this helper method to
        determine what the current sort parameters are.
        """
        order = self.request.GET.get('order_col', 'due_date')
        order_dir = self.request.GET.get('order_dir', 'asc')
        if order == 'due_date':
            # handle sorting of NULL values so they are always at the end
            order = 'CASE WHEN due_date IS NULL THEN 1 ELSE 0 END, due_date'
        if order == 'task':
            # Sort ignoring case
            order += ' COLLATE NOCASE'
        if order_dir:
            order = ' '.join([order, order_dir])
        return order

    def generate_task_form(self, formid="deform"):
        """This helper code generates the form that will be used to add
        and edit the tasks based on the schema of the form.
        """
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
            formid=formid,
            use_ajax=True,
            ajax_options=options,
        )

    def process_task_form(self, form):
        """This helper code processes the task from that we have
        generated from Colander and Deform.

        This handles both the initial creation and subsequent edits for
        a task.
        """
        try:
            # try to validate the submitted values
            controls = self.request.POST.items()
            captured = form.validate(controls)
            action = 'created'
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
                task_id = captured.get('id')
                if task_id is not None:
                    action = 'updated'
                    task.id = task_id
                DBSession.merge(task)
            msg = "Task <b><i>%s</i></b> %s successfully" % (task_name, action)
            self.request.session.flash(msg, queue='success')
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

    @view_config(route_name='about', renderer='templates/about.pt')
    def about_view(self):
        """This is just a static page with info about the site.
        """
        return {'section': 'about'}

    @notfound_view_config(renderer='templates/404.pt')
    def notfound(self):
        """This special view just renders a custom 404 page. We do this
        so that the 404 page fits nicely into our global layout.
        """
        return {}

    @forbidden_view_config(renderer='templates/signin.pt')
    def forbidden(self):
        """This special view renders a login page when a user requests
        a page that they don't have permission to see. In the same way
        that the notfound view is set up, this will fit nicely into our
        global layout.
        """
        return {'section': 'login'}

    @view_config(route_name='logout', check_csrf=True)
    def logout(self):
        """This is an override of the logout view that comes from the
        persona plugin. The only change here is that the user is always
        re-directed back to the home page when logging out. This is so
        that they don't see a `forbidden` page right after logging out.
        """
        headers = forget(self.request)
        # Send the user back home, everything else is protected
        return HTTPFound('/', headers=headers)

    @view_config(route_name='login', check_csrf=True)
    def login_view(self):
        """This is an override of the login view that comes from the
        persona plugin. The basics of verify_login and remembering the
        user in a cookie are still present.

        Here we check to see if the user has been created in the
        database, then create the user. If they are an existing user,
        we just take them to the page they were trying to access.
        """
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
        """This is the settings form for the user. The first time a
        user logs in, they are taken here so we can get their first and
        last name.
        """
        # Special case when the db was blown away
        if self.user_id is not None and self.user is None:
            return self.logout()
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
        """Get a list of dictionaries for the given term. This gives
        the tag input the information it needs to do auto completion.
        """
        term = self.request.params.get('term', '')
        if len(term) < 2:
            return []
        # XXX: This is global tags, need to hook into "user_tags"
        tags = DBSession.query(Tag).filter(Tag.name.startswith(term)).all()
        return [
            dict(id=tag.name, value=tag.name, label=tag.name)
            for tag in tags
        ]

    @view_config(renderer='json', name='edit.task', permission='view')
    def edit_task(self):
        """Get the values to fill in the edit form
        """
        todo_id = self.request.params.get('id', None)
        if todo_id is None:
            return False
        task = DBSession.query(TodoItem).filter(
            TodoItem.id == todo_id).first()
        due_date = None
        # If there is a due date, localize the time
        if task.due_date is not None:
            due_dt = localize_datetime(task.due_date, self.user.time_zone)
            due_date = due_dt.strftime('%Y-%m-%d %H:%M:%S')
        return dict(
            id=task.id,
            name=task.task,
            tags=','.join([tag.name for tag in task.sorted_tags]),
            due_date=due_date,
        )

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
        """This is the first page the user will see when coming to the
        application. If they are anonymous, the count is None and the
        template shows some enticing welcome text.

        If the user is logged in, then this gets a count of the user's
        tasks, and shows that number on the home page with a link to
        the `list_view`.
        """
        # Special case when the db was blown away
        if self.user_id is not None and self.user is None:
            return self.logout()
        if self.user_id is None:
            count = None
        else:
            count = len(self.user.todo_list.all())
        return {'user': self.user, 'count': count, 'section': 'home'}

    @view_config(route_name='list', renderer='templates/todo_list.pt',
                permission='view')
    def list_view(self):
        """This is the main functional page of our application. It
        shows a listing of the tasks that the currently logged in user
        has created.
        """
        # Special case when the db was blown away
        if self.user_id is not None and self.user is None:
            return self.logout()
        form = self.generate_task_form()
        if 'submit' in self.request.POST:
            return self.process_task_form(form)
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
        """This view simply shows all of the tags a user has created.
        """
        # Special case when the db was blown away
        if self.user_id is not None and self.user is None:
            return self.logout()
        tags = self.user.user_tags
        return {
            'section': 'tags',
            'count': len(tags),
            'tags': tags,
        }

    @view_config(route_name='tag', renderer='templates/todo_list.pt',
                 permission='view')
    def tag_view(self):
        """Very similar to the list_view, this view just filters the
        list of tags down to the tag selected in the url based on the
        tag route replacement marker that ends up in the `matchdict`.
        """
        # Special case when the db was blown away
        if self.user_id is not None and self.user is None:
            return self.logout()
        form = self.generate_task_form()
        if 'submit' in self.request.POST:
            return self.process_task_form(form)
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
