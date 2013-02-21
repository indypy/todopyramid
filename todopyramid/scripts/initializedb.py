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
        task1 = TodoItem(
            task='A joke about pythons',
            tags=[' OnE ', 'two'],
            due_date=datetime.utcnow() - timedelta(days=1),
        )
        task2 = TodoItem(
            task='The special times',
            tags=[' OnE ', ' THREe'],
            due_date=datetime.utcnow() + timedelta(hours=5),
        )
        task3 = TodoItem(
            task='No end date',
            tags=['spam', 'eggs', 'ham'],
            due_date=None,
        )
        task4 = TodoItem(
            task='Doin stuff',
            tags=[],
            due_date=datetime.utcnow() + timedelta(days=60),
        )
        DBSession.add(task1)
        DBSession.add(task2)
        DBSession.add(task3)
        DBSession.add(task4)
