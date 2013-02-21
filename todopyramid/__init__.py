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
    config = Configurator(settings=settings)
    config.include('pyramid_persona')
    config.add_static_view('static', 'static', cache_max_age=3600)
    # Adding the static resources from Deform
    config.add_static_view(
        'deform_static', 'deform:static', cache_max_age=3600
    )
    config.add_static_view(
        'deform_bootstrap_static', 'deform_bootstrap:static',
        cache_max_age=3600
    )
    config.add_route('home', '/')
    config.add_route('list', '/list')
    config.scan()
    return config.make_wsgi_app()
