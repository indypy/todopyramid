from pyramid.config import Configurator
from sqlalchemy import engine_from_config

from .models import (
    DBSession,
    Base,
    )


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
    config.scan()
    return config.make_wsgi_app()
