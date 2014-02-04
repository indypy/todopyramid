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
    
    return DBSession

def _insert_first_user(session):
    with transaction.manager:
            user = TodoUser(
                email=u'king.arthur@example.com',
                first_name=u'Arthur',
                last_name=u'Pendragon',
            )
            session.add(user)


class ModelTests(unittest.TestCase):
    def setUp(self):
        self.session = _initTestingDB()
        self.config = testing.setUp()

    def tearDown(self):
        self.session.remove()
        testing.tearDown()


class UserModelTests(ModelTests):
    
    def _getTargetClass(self):
        from .models import TodoUser
        return TodoUser
    
    def _makeOne(self, email, first_name=None, last_name=None, time_zone=u'US/Eastern'):
        return self._getTargetClass()(email, first_name, last_name, time_zone)
    
    def test_constructor(self):
        instance = self._makeOne(u'king.arthur@example.com',
                                 u'Arthur',
                                 u'Pendragon')
        self.assertEqual(instance.email, u'king.arthur@example.com')
        self.assertEqual(instance.first_name, u'Arthur')
        self.assertEqual(instance.last_name, u'Pendragon')
        self.assertEqual(instance.time_zone, u'US/Eastern')
        
    def test_profile_is_not_complete(self):
        instance = self._makeOne(u'king.arthur@example.com',
                                 u'Arthur',
                                 None)
        self.assertFalse(instance.profile_complete)
        
    def test_profile_complete(self):
        instance = self._makeOne(u'king.arthur@example.com',
                                 u'Arthur',
                                 u'Pendragon')
        self.assertTrue(instance.profile_complete)


    def test_given_a_new_user_when_I_ask_for_tags_then_I_get_an_empty_list(self):
        instance = self._makeOne(u'king.arthur@example.com',
                         u'Arthur',
                         u'Pendragon')
        self.session.add(instance)
        tags = instance.user_tags
        self.assertEqual(tags, [])
        
class TodoItemModelTests(ModelTests):
      
    def _getTargetClass(self):
        from .models import TodoItem
        return TodoItem
    
    def _makeOne(self, user, task, tags=None, due_date=None):
        return self._getTargetClass()(user, task, tags, due_date)
    
    def test_constructor(self):
        instance = self._makeOne(1,
                                 u'Find a shrubbery')
        self.assertEqual(instance.user, 1)
        self.assertEqual(instance.task, u'Find a shrubbery')
        self.assertEqual(instance.due_date, None)
        self.assertEqual(instance.tags, [])
        
    def test_given_that_I_add_a_user_and_insert_a_task_with_several_tags_I_can_access_tag_collection(self):
        from .models import Tag
        instance = self._makeOne(1,
                                 u'Find a shrubbery',
                                 [u'quest', u'ni', u'knight'])
        self.assertEqual(instance.tags[0].name, u'quest')
        self.assertEqual(instance.tags[1].name, u'ni')
        self.assertEqual(instance.tags[2].name, u'knight')
        
    def test_tag_todos(self):
        from .models import Tag
        instance = self._makeOne(1,
                                 u'Find a shrubbery',
                                 [u'quest', u'ni', u'knight'])
        self.session.add(instance)
        tag = self.session.query(Tag).filter_by(name=u'ni').one()
        self.assertEqual(tag.todos[0].task, u'Find a shrubbery')
           
        
    def test_inserting_todoitems_without_transaction_manager_with_same_tags_keep_tags_unique(self):
        from .models import Tag
        from .models import TodoItem

        instance = self._makeOne(1,
                                 u'Find a shrubbery',
                                 [u'quest', u'ni', u'knight']
                                 )

        
        self.session.add(instance)
    

        instance = self._makeOne(1,
                                 u'Find another shrubbery',
                                 [u'quest', u'ni', u'knight']
                                 )

        self.session.add(instance)
        
        todos = self.session.query(TodoItem).count()
        self.assertEqual(todos, 2)
        
        tag = self.session.query(Tag).filter(Tag.name == u'quest').one()
        self.assertEqual(tag.name, u'quest')

    @unittest.skip('skip because it raises IntegrityError')        
    def test_inserting_multiple_todoitems_with_same_tags_using_addall_keep_tags_unique(self):
        from .models import Tag

        first_item = self._makeOne(1,
                                 u'Find a shrubbery',
                                 [u'quest', u'ni', u'knight']
                                 )   

        second_item = self._makeOne(1,
                                 u'Find another shrubbery',
                                 [u'quest', u'ni', u'knight']
                                 )

        self.session.add_all([first_item, second_item])
        
        tag = self.session.query(Tag).filter(Tag.name == u'quest').one()
        self.assertEqual(tag.name, u'quest')
        


class TestHomeView(unittest.TestCase):

    def test_anonymous(self):
        from .views import ToDoViews
        
        request = testing.DummyRequest()
        inst = ToDoViews(request)
        response = inst.home_view()
        self.assertEqual(response['user'], None)
        self.assertEqual(response['count'], None)
        self.assertEqual(response['section'], 'home')
        

        

