from pyramid.config import Configurator
from sqlalchemy import engine_from_config

from .models import (
    DBSession,
    Base,
    )

from .views import get_user

def get_db_session(request):
    """return thread-local DB session"""
    return DBSession

def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    engine = engine_from_config(settings, 'sqlalchemy.')
    DBSession.configure(bind=engine)
    Base.metadata.bind = engine
    config = Configurator(
        settings=settings,
        root_factory='todopyramid.models.RootFactory',
    )
    config.add_static_view('static', 'static', cache_max_age=3600)
    
    # Misc. views
    config.add_route('home', '/')
    config.add_route('about', '/about')
    # Users
    config.add_route('account', '/account')
    # Viewing todo lists
    config.add_route('todos', '/todos')
    config.add_route('tags', '/tags')
    config.add_route('taglist', '/tags/{tag_name}')
    # AJAX
    config.add_route('todo', '/todos/{todo_id}')
    config.add_route('delete.task', '/delete.task/{todo_id}')
    config.add_route('tags.autocomplete', '/tags.autocomplete')
    
    # make DB session a request attribute
    # http://blog.safaribooksonline.com/2014/01/07/building-pyramid-applications/
    config.add_request_method(get_db_session, 'db', reify=True)
    
    # Making A User Object Available as a Request Attribute
    # http://docs.pylonsproject.org/projects/pyramid_cookbook/en/latest/auth/user_object.html
    config.add_request_method(get_user, 'user', reify=True)
    
    # scan modules for config descriptors
    config.scan()
    return config.make_wsgi_app()
