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
        task=u'Find a shrubbery',
        tags=[u'quest', u'ni', u'knight'],
        due_date=datetime.utcnow() + timedelta(days=60),
    )
    DBSession.add(task)
    task = TodoItem(
        user=user_id,
        task=u'Search for the holy grail',
        tags=[u'quest'],
        due_date=datetime.utcnow() - timedelta(days=1),
    )
    DBSession.add(task)
    task = TodoItem(
        user=user_id,
        task=u'Recruit Knights of the Round Table',
        tags=[u'quest', u'knight', u'discuss'],
        due_date=datetime.utcnow() + timedelta(minutes=45),
    )
    DBSession.add(task)
    task = TodoItem(
        user=user_id,
        task=u'Build a Trojan Rabbit',
        tags=[u'quest', u'rabbit'],
        due_date=datetime.utcnow() + timedelta(days=1),
    )
    DBSession.add(task)
    task = TodoItem(
        user=user_id,
        task=u'Talk to Tim the Enchanter',
        tags=[u'quest', u'discuss'],
        due_date=datetime.utcnow() + timedelta(days=90),
    )
    DBSession.add(task)
    task = TodoItem(
        user=user_id,
        task=u'Defeat the Rabbit of Caerbannog',
        tags=[u'quest', u'rabbit'],
        due_date=None,
    )
    DBSession.add(task)
    task = TodoItem(
        user=user_id,
        task=u'Cross the Bridge of Death',
        tags=[u'quest'],
        due_date=None,
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
