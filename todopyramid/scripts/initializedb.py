from datetime import datetime
from datetime import timedelta
import os
import sys
import transaction

from sqlalchemy import engine_from_config

from pyramid.paster import (
    get_appsettings,
    setup_logging,
    )

from ..models import (
    DBSession,
    TodoItem,
    TodoUser,
    Base,
    )


def usage(argv):
    cmd = os.path.basename(argv[0])
    print('usage: %s <config_uri>\n'
          '(example: "%s development.ini")' % (cmd, cmd))
    sys.exit(1)


def create_dummy_content(user_id):
    """Create some tasks by default to show off the site
    """
    task = TodoItem(
        user=user_id,
        task=u'A joke about pythons',
        tags=[u' OnE ', u'two'],
        due_date=datetime.utcnow() - timedelta(days=1),
    )
    DBSession.add(task)
    task = TodoItem(
        user=user_id,
        task=u'The special times',
        tags=[u' OnE ', u' THREe'],
        due_date=datetime.utcnow() + timedelta(hours=5),
    )
    DBSession.add(task)
    task = TodoItem(
        user=user_id,
        task=u'No end date',
        tags=[u'spam', u'eggs', u'ham'],
        due_date=None,
    )
    DBSession.add(task)
    task = TodoItem(
        user=user_id,
        task=u'Doin stuff',
        tags=[],
        due_date=datetime.utcnow() + timedelta(days=60),
    )
    DBSession.add(task)


def main(argv=sys.argv):
    if len(argv) != 2:
        usage(argv)
    config_uri = argv[1]
    setup_logging(config_uri)
    settings = get_appsettings(config_uri)
    engine = engine_from_config(settings, 'sqlalchemy.')
    DBSession.configure(bind=engine)
    Base.metadata.create_all(engine)
    with transaction.manager:
        user = TodoUser(
            email=u'king.arthur@example.com',
            first_name=u'Arthur',
            last_name=u'Pendragon',
        )
        DBSession.add(user)
        create_dummy_content(u'king.arthur@example.com')
