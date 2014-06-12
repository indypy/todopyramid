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

from ..utils import localize_datetime

def usage(argv):
    cmd = os.path.basename(argv[0])
    print('usage: %s <config_uri>\n'
          '(example: "%s development.ini")' % (cmd, cmd))
    sys.exit(1)


def create_dummy_user():
    """create our dummy user
    
    we handle transaction not here - design decision
    """

    user = TodoUser(
        email=u'king.arthur@example.com',
        first_name=u'Arthur',
        last_name=u'Pendragon',
    )
    DBSession.add(user)  
    user_id = user.email 
    return user_id

def create_dummy_content(user_id):
    """Create some tasks for this user with by default to show off the site 
    
    either called during application startup or during content creation while a new user registers
    we do not handle transaction here - design decision  
    
    TODO: bulk adding of new content
    """   
        
    user = DBSession.query(TodoUser).filter(TodoUser.email == user_id).first()
    time_zone = user.time_zone 
         
    #this user creates several todo items with localized times
    task = TodoItem(
        user=user_id,
        task=u'Find a shrubbery',
        tags=[u'quest', u'ni', u'knight'],
        due_date=localize_datetime((datetime.utcnow() + timedelta(days=60)), time_zone),
    )
    DBSession.add(task)
    task = TodoItem(
        user=user_id,
        task=u'Search for the holy grail',
        tags=[u'quest'],
        due_date=localize_datetime((datetime.utcnow() + timedelta(days=1)), time_zone),
    )
    DBSession.add(task)
    task = TodoItem(
        user=user_id,
        task=u'Recruit Knights of the Round Table',
        tags=[u'quest', u'knight', u'discuss'],
        due_date=localize_datetime((datetime.utcnow() + timedelta(minutes=45)), time_zone),
    )
    DBSession.add(task)
    task = TodoItem(
        user=user_id,
        task=u'Build a Trojan Rabbit',
        tags=[u'quest', u'rabbit'],
        due_date=localize_datetime((datetime.utcnow() + timedelta(days=1)), time_zone),
    )
    DBSession.add(task)
    task = TodoItem(
        user=user_id,
        task=u'Talk to Tim the Enchanter',
        tags=[u'quest', u'discuss'],
        due_date=localize_datetime((datetime.utcnow() + timedelta(days=90)), time_zone),
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
        user_id = create_dummy_user()
        create_dummy_content(user_id)

        
