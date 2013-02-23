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
from webhelpers.html.builder import HTML
from webhelpers.html.grid import ObjectGrid

from .scripts.initializedb import create_dummy_content
from .layouts import Layouts
from .models import DBSession
from .models import Tag
from .models import TodoItem
from .models import TodoUser
from .schema import SettingsSchema


class TodoGrid(ObjectGrid):
    def __init__(self, request, selected_tag, *args, **kwargs):
        self.request = request
        if 'url' not in kwargs:
            kwargs['url'] = request.current_route_url
        super(TodoGrid, self).__init__(*args, **kwargs)
        self.exclude_ordering = ['_numbered', 'tags']
        self.column_formats['due_date'] = self.due_date_td
        self.column_formats['tags'] = self.tags_td
        self.column_formats[''] = self.action_td
        self.selected_tag = selected_tag

    def generate_header_link(self, column_number, column, label_text):
        """This handles generation of link and then decides to call
        self.default_header_ordered_column_format or
        self.default_header_column_format
        based on whether current column is the one that is used for sorting.

        You need to extend Grid class and overload this method implementing
        ordering here, whole operation consists of setting self.order_column
        and self.order_dir to their CURRENT values, and generating new urls for
        state that header should set set after its clicked

        (additional kw are passed to url gen. - like for webhelpers.paginate)
        """
        GET = dict(self.request.copy().GET)  # needs dict() for py2.5 compat
        self.order_column = GET.pop("order_col", None)
        self.order_dir = GET.pop("order_dir", None)
        # determine new order
        if column == self.order_column and self.order_dir == "asc":
            new_order_dir = "desc"
        else:
            new_order_dir = "asc"
        self.additional_kw['order_col'] = column
        self.additional_kw['order_dir'] = new_order_dir
        # generate new url for example url_generator uses
        # pylons's url.current() or pyramid's current_route_url()
        new_url = self.url_generator(_query=self.additional_kw)
        # set label for header with link
        label_text = HTML.tag("a", href=new_url, c=label_text)
        return super(TodoGrid, self).generate_header_link(column_number,
                                                             column,
                                                             label_text)

    def tags_td(self, col_num, i, item):
        tag_links = []

        for tag in item.sorted_tags:
            tag_url = '%s/tags/%s' % (self.request.application_url, tag.name)
            tag_class = 'label'
            if self.selected_tag and tag.name == self.selected_tag:
                tag_class += ' label-warning'
            else:
                tag_class += ' label-info'
            anchor = HTML.tag("a", href=tag_url, c=tag.name,
                              class_=tag_class)
            tag_links.append(anchor)
        return HTML.td(*tag_links, _nl=True)

    def due_date_td(self, col_num, i, item):
        if item.due_date is None:
            return HTML.td('')
        span_class = 'badge'
        if item.past_due:
            span_class += ' badge-important'
        span = HTML.tag("span",
                        c=HTML.literal(pretty_date(item.due_date)),
                        class_=span_class)
        return HTML.td(span)

    def action_td(self, col_num, i, item):
        return HTML.td(HTML.literal("""\
        <div class="btn-group">
          <a class="btn dropdown-toggle" data-toggle="dropdown" href="#">
          Action
          <span class="caret"></span>
          </a>
          <ul class="dropdown-menu" id="%s">
            <li><a class="todo-edit" href="#">Edit</a></li>
            <li><a class="todo-complete" href="#">Complete</a></li>
          </ul>
        </div>
        """ % item.id))


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
            except (ValidationFailure,), e:
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
            )
        else:
            appstruct = {}
        return {
            'form': form.render(appstruct),
            'css_resources': css_resources,
            'js_resources': js_resources,
            'section': section_name,
        }

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

    @view_config(route_name='list', renderer='templates/todo_list.pt',
                permission='view')
    def list_view(self):
        order = self.request.GET.get('order_col', 'due_date IS NULL')
        order_dir = self.request.GET.get('order_dir', '')
        if order_dir:
            order = ' '.join([order, order_dir])
        todo_items = self.user.todo_list.order_by(order).all()
        grid = TodoGrid(
            self.request,
            None,
            todo_items,
            ['task', 'tags', 'due_date', '']
        )
        count = len(todo_items)
        item_label = 'items' if count > 1 or count == 0 else 'item'
        return {
            'page_title': 'Todo List',
            'subtext': '<span class="count">%s</span> %s remaining' % (
                count, item_label),
            'section': 'list',
            'items': todo_items,
            'grid': grid,
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
        tag_name = self.request.matchdict['tag_name']
        order = self.request.GET.get('order_col', 'due_date IS NULL')
        order_dir = self.request.GET.get('order_dir', '')
        if order_dir:
            order = ' '.join([order, order_dir])
        qry = self.user.todo_list.order_by(order)
        tag_filter = TodoItem.tags.any(Tag.name.in_([tag_name]))
        todo_items = qry.filter(tag_filter)
        count = todo_items.count()
        subtext = (
            '<span class="count">%s</span> %s matching '
            '<span class="label label-warning">%s</span>'
        )
        item_label = 'items' if count > 1 or count == 0 else 'item'
        grid = TodoGrid(
            self.request,
            tag_name,
            todo_items,
            ['task', 'tags', 'due_date', '']
        )
        return {
            'page_title': 'Tag List',
            'subtext':  subtext % (count, item_label, tag_name),
            'section': 'tags',
            'tag_name': tag_name,
            'items': todo_items,
            'grid': grid,
        }


def pretty_date(item_date):
    """Shoehorn the moment.js code into the template. Based on this
    blog: http://blog.miguelgrinberg.com/

    XXX: remove this and do it via jQuery
    """
    fmt_date = item_date.strftime('%Y-%m-%dT%H:%M:%S Z')
    return """
<script>
  document.write(moment("%s").calendar());
</script>""" % fmt_date

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
