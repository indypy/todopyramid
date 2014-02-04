import unittest
import transaction

from pyramid import testing

from .models import (
                     DBSession,
                     TodoUser,
                     Base,
                     )

def _initTestingDB():
    """setup testing DB, insert sample entry and return Session
    
    http://docs.pylonsproject.org/projects/pyramid/en/1.5-branch/quick_tutorial/databases.html
    """  
    from sqlalchemy import create_engine
    engine = create_engine('sqlite://')
    from .models import (
        Base,
        TodoUser,
        )
    DBSession.configure(bind=engine)
    Base.metadata.create_all(engine)
    with transaction.manager:
         user = TodoUser(
            email=u'king.arthur@example.com',
            first_name=u'Arthur',
            last_name=u'Pendragon',
        )
         DBSession.add(user)
    
    return DBSession


class TestHomeView(unittest.TestCase):
    def setUp(self):
        self.session = _initTestingDB()
        self.config = testing.setUp()

    def tearDown(self):
        self.session.remove()
        testing.tearDown()

    def test_it(self):
        from .views import ToDoViews
        
        request = testing.DummyRequest()
        inst = ToDoViews(request)
        response = inst.home_view()
        self.assertEqual(response['user'], None)
        self.assertEqual(response['count'], None)
        self.assertEqual(response['section'], 'home')

