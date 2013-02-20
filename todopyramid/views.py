from pyramid.response import Response
from pyramid.view import forbidden_view_config
from pyramid.view import notfound_view_config
from pyramid.view import view_config

from sqlalchemy.exc import DBAPIError

from .layouts import Layouts
from .models import (
    DBSession,
    MyModel,
    )


class ToDoViews(Layouts):

    def __init__(self, context, request):
        self.context = context
        self.request = request

    @notfound_view_config(renderer='templates/404.pt')
    def notfound(request):
        return {}

    @forbidden_view_config(renderer='templates/signin.pt')
    def forbidden(request):
        return {}

    @view_config(route_name='home', renderer='templates/home.pt')
    def my_view(request):
        try:
            one = DBSession.query(MyModel).filter(
                MyModel.name == 'one').first()
        except DBAPIError:
            return Response(
                conn_err_msg, content_type='text/plain', status_int=500)
        return {'one': one, 'project': 'todopyramid'}

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
