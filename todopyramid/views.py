from pyramid.httpexceptions import HTTPFound
from pyramid.response import Response
from pyramid.security import authenticated_userid
from pyramid.security import remember
from pyramid.security import forget
from pyramid.settings import asbool
from pyramid.view import forbidden_view_config
from pyramid.view import notfound_view_config
from pyramid.view import view_config
from pyramid.decorator import reify

from deform import Form
from deform import ValidationFailure
from peppercorn import parse
from pyramid_deform import FormView
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

    def __init__(self, request):
        """Set some common variables needed for each view.
        """
        self.request = request
        self.user_id = authenticated_userid(request)
        self.user = None
        if self.user_id is not None:
            query = DBSession.query(TodoUser)
            self.user = query.filter(TodoUser.email == self.user_id).first()

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
            count = len(self.user.todos)
        return {'user': self.user, 
                'count': count,
                'section': 'home',
        }

    @view_config(route_name='tags', renderer='templates/todo_tags.pt',
                permission='view')
    def tags_view(self):
        """This view simply shows all of the tags a user has created.
        
        TODO: use request.route_url API to generate URLs in view code
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
        return HTTPFound(self.request.route_url('home'), headers=headers)

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
            return HTTPFound(self.request.route_url('account'), headers=headers)
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
        return HTTPFound(self.request.route_url('account'), headers=headers)


class BaseView(FormView):
    """subclass view to return links to static CSS/JS resources"""   
    
    def __init__(self, request):
        super(BaseView, self).__init__(request)
        self.request = request
        self.user_id = authenticated_userid(request)
        self.user = None
        if self.user_id is not None:
            query = DBSession.query(TodoUser)
            self.user = query.filter(TodoUser.email == self.user_id).first()
    
    def __call__(self):
        """same as base class method but customizes links to JS/CSS resources  
        
        Prepares and render the form according to provided options.

        Upon receiving a ``POST`` request, this method will validate
        the request against the form instance. After validation, 
        this calls a method based upon the name of the button used for
        form submission and whether the validation succeeded or failed.
        If the button was named ``save``, then :meth:`save_success` will be
        called on successful validation or :meth:`save_failure` will
        be called upon failure. An exception to this is when no such
        ``save_failure`` method is present; in this case, the fallback
        is :meth:`failure``. 
        
        Returns a ``dict`` structure suitable for provision tog the given
        view. By default, this is the page template specified 
        """
        use_ajax = getattr(self, 'use_ajax', False)
        ajax_options = getattr(self, 'ajax_options', '{}')
        self.schema = self.schema.bind(**self.get_bind_data())
        form = self.form_class(self.schema, buttons=self.buttons,
                               use_ajax=use_ajax, ajax_options=ajax_options,
                               **dict(self.form_options))
        self.before(form)
        reqts = form.get_widget_resources()
        result = None

        for button in form.buttons:
            if button.name in self.request.POST:
                success_method = getattr(self, '%s_success' % button.name)
                try:
                    controls = self.request.POST.items()
                    validated = form.validate(controls)
                    result = success_method(validated)
                except ValidationFailure as e:
                    fail = getattr(self, '%s_failure' % button.name, None)
                    if fail is None:
                        fail = self.failure
                    result = fail(e)
                break

        if result is None:
            result = self.show(form)

        if isinstance(result, dict):
            result['js_resources'] = [self.request.static_url('deform:static/%s' % r) for r in reqts['js']]
            result['css_resources'] = [self.request.static_url('deform:static/%s' % r) for r in reqts['css']]

        return result


@view_config(route_name='account', renderer='templates/account.pt', permission='view')
class AccountEditView(BaseView, Layouts):
    """view class for account from
    
    inherits from BaseView to get customized JS/CSS resources behaviour 
    inherits from Layout to use global TodoPyramid template
    """
    schema = SettingsSchema()
    buttons = ('save', 'cancel')
    
    def save_success(self, appstruct):
        """save button handler - called after successful validation 
        
        save validated user prefs and redirect to list view""" 
        self.user.update_prefs(**appstruct)
        self.request.session.flash(
            'Settings updated successfully',
            queue='success',
        )
        return HTTPFound(self.request.route_url('home'))
    
    def save_failure(self, exc):
        """save button failure handler - called after validation failure
        
        add custom message as flash message and render form
        TODO: investigate exception"""
        msg = 'There was an error saving your settings.'
        self.request.session.flash(msg, queue='error')
    
    def cancel_success(self, appstruct):
        """cancel button handler redirects to todo list view"""        
        return HTTPFound(self.request.route_url('todos'))
    

    def appstruct(self):
        """This allows edit forms to pre-fill form values conveniently.
        
        TODO: find out how to generate appstruct from model - sort of model binding API or helper"""
        
        user = self.user
        return {'first_name': user.first_name,
                'last_name': user.last_name,
                'time_zone': user.time_zone}


@view_config(route_name="taglist", renderer='templates/todo_list.pt', permission='view')
@view_config(route_name='todos', renderer='templates/todo_list.pt', permission='view')
class TodoItemForm(BaseView, Layouts):
    """view class to renderer all user todos or todos-by-tag - use case depends on matched route
     
    responsibilities
    * render TaskForm
    * render TodoGrid
    * care about sort_order
    * edit task AJAX
    * delete task AJAX
    * feed AutoComplete Ajax Widget
    """
    schema = TodoSchema()
    buttons = ('save',)
    form_options = (('formid', 'deform'),)
    use_ajax = True
    ajax_options = """
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
    def save_success(self, appstruct):
        """save button handler
        
        handle create/edit action and redirect to page
        
        TODO: pass appstruct as **kwargs to domain method 
        """
        #TodoSchema colander schema and SQLAlchemy model TodoItem differ
        id = appstruct['id'] #hidden with colander.missing
        name = appstruct['name'] #required
        tags = appstruct['tags'].split(',')  #optional with colander.missing, multiple tags are seperated with commas 
        due_date = appstruct['due_date'] #optional with colander.missing
        
        #encapsulate with try-except
        if id:
            #edit user todo
            self.user.edit_todo(id, name, tags, due_date)
            action = 'updated'
        else:
            #create new user todo
            self.user.create_todo(name, tags, due_date)
            action = 'created'
        
        msg = "Task <b><i>%s</i></b> %s successfully" % (name, action)
        self.request.session.flash(msg, queue='success')
        
        #reload the current page
        location = self.request.url
        return Response(
            '',
            headers=[
                ('X-Relocate', location),
                ('Content-Type', 'text/html'),
            ]
        )
        
    def update_success(self):
        """target create/edit use cases with different button handlers"""
        pass

    @view_config(route_name='todo', renderer='json', permission='view', xhr=True)
    def get_task(self):
        """Get the task to fill in the edit form
        
        TODO: encapsulate datetime localization into model - done
        TODO: make datetime string configurable
        """
        todo_id = self.request.matchdict['todo_id']
        if todo_id is None:
            return False
        task = self.user.todo_list.filter_by(id=todo_id).one()
        
        due_date = task.due_date.strftime('%Y-%m-%d %H:%M:%S') if task.due_date is not None else None
        return dict(
            id=task.id,
            name=task.task,
            tags=','.join([tag.name for tag in task.sorted_tags]),
            due_date=due_date,
        )
        
        
    @view_config(renderer='json', name='delete.task', permission='view')
    def delete_task(self):
        """Delete a todo list item

        TODO: Add a guard here so that you can only delete your tasks - done
        """
        todo_id = self.request.params.get('id', None)
        if todo_id is not None:
            self.user.delete_todo(todo_id)
        return True


    @view_config(renderer='json', name='tags.autocomplete', permission='view')
    def tag_autocomplete(self):
        """Get a list of dictionaries for the given term. This gives
        the tag input the information it needs to do auto completion.
        
        TODO: improve model to support user_tags - done
        """
        term = self.request.params.get('term', '')
        if len(term) < 2:
            return []
        
        tags = self.user.user_tags_autocomplete(term)
        return [
            dict(id=tag.name, value=tag.name, label=tag.name)
            for tag in tags
        ]
        
    def get_bind_data(self):
        """deferred binding of user time zone
        
        TODO: do we still need it after refactoring timezone conversion into model ???"""
        data = super(TodoItemForm, self).get_bind_data()
        data.update({'user_tz': self.user.time_zone})
        return data
    
    def sort_order(self):
        """The list_view and tag_view both use this helper method to
        determine what the current sort parameters are.
        
        TODO: try to refactor using SQLAlchemy API or plain Python
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

    
    def show(self, form):
        """Override to inject TodoGrid and other stuff
        
        address both use cases by testing which route matched 
        """
        # Special case when the db was blown away
        if self.user_id is not None and self.user is None:
            return self.logout()

        order = self.sort_order()
        tag_name = self.request.matchdict.get('tag_name')
        if tag_name:
            #route match for todos-by-tag
            todo_items = self.user.todos_by_tag(tag_name, order)
            page_title = 'Tag List'
        else:
            #route match for todos
            todo_items = self.user.todo_list.order_by(order).all()
            page_title = 'ToDo List'    
            
        grid = TodoGrid(
            self.request,
            None,
            self.user.time_zone,
            todo_items,
            ['task', 'tags', 'due_date', ''],
        )
        
        count = len(todo_items)
        item_label = 'items' if count > 1 or count == 0 else 'item'
        
        todos = {
            'page_title': page_title,
            'count': count,
            'item_label': item_label,
            'section': 'list',
            'items': todo_items,
            'grid': grid,
        }
        

        #copied from FormView.show        
        appstruct = self.appstruct()
        if appstruct is None:
            rendered = form.render()
        else:
            rendered = form.render(appstruct)
        taskform = {
            'form': rendered,
            }
        
        
        #merge and return to renderer
        todos.update(taskform)
        return todos    
        