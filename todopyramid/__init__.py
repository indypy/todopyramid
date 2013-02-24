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
    config.include('pyramid_persona')
    config.include('deform_bootstrap_extra')
    config.add_static_view('static', 'static', cache_max_age=3600)
    # Adding the static resources from Deform
    config.add_static_view(
        'deform_static', 'deform:static', cache_max_age=3600
    )
    config.add_static_view(
        'deform_bootstrap_static', 'deform_bootstrap:static',
        cache_max_age=3600
    )
    config.add_static_view(
        'deform_bootstrap_extra_static', 'deform_bootstrap_extra:static',
        cache_max_age=3600
    )
    # Misc. views
    config.add_route('home', '/')
    config.add_route('about', '/about')
    # Users
    config.add_route('account', '/account')
    # Viewing todo lists
    config.add_route('list', '/list')
    config.add_route('tags', '/tags')
    config.add_route('tag', '/tags/{tag_name}')
    config.scan()
    return config.make_wsgi_app()
