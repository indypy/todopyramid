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
        user1 = TodoUser(
            email='me@claytron.com',
            first_name='Clayton',
            last_name='Parker',
        )
        DBSession.add(user1)
        user2 = TodoUser(
            email='king.arthur@example.com',
            first_name='Arthur',
            last_name='Pendragon',
        )
        DBSession.add(user2)
        task1 = TodoItem(
            task='A joke about pythons',
            tags=[' OnE ', 'two'],
            due_date=datetime.utcnow() - timedelta(days=1),
            user='me@claytron.com',
        )
        task2 = TodoItem(
            user='me@claytron.com',
            task='The special times',
            tags=[' OnE ', ' THREe'],
            due_date=datetime.utcnow() + timedelta(hours=5),
        )
        task3 = TodoItem(
            user='me@claytron.com',
            task='No end date for claytron',
            tags=['spam', 'eggs', 'ham', 'claytron'],
            due_date=None,
        )
        task4 = TodoItem(
            user='me@claytron.com',
            task='Doin stuff',
            tags=[],
            due_date=datetime.utcnow() + timedelta(days=60),
        )
        task5 = TodoItem(
            user='king.arthur@example.com',
            task='No end date for arthur',
            tags=['spam', 'eggs', 'ham', 'arthur'],
            due_date=None,
        )
        task6 = TodoItem(
            user='king.arthur@example.com',
            task='Doin stuff for arthur',
            tags=[],
            due_date=datetime.utcnow() + timedelta(days=60),
        )
        DBSession.add(task1)
        DBSession.add(task2)
        DBSession.add(task3)
        DBSession.add(task4)
        DBSession.add(task5)
        DBSession.add(task6)
