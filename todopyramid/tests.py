try:
    import unittest2 as unittest
except ImportError:
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


    def test_given_a_new_user_when_I_ask_for_user_tags_then_I_get_an_empty_list(self):
        instance = self._makeOne(u'king.arthur@example.com',
                         u'Arthur',
                         u'Pendragon')
        self.session.add(instance)
        tags = instance.user_tags
        self.assertEqual(tags, [])
        
        
    def test_given_a_new_user_when_I_ask_for_todos_Then_I_get_back_an_empty_list(self):
        user = self._makeOne(u'king.arthur@example.com',
                         u'Arthur',
                         u'Pendragon')
        self.session.add(user)
        todos = user.todos
        self.assertEqual(todos, [])    
        
    def test_given_a_user_when_I_add_a_todo_Then_I_can_access_it_from_user_todo_collection(self):
        """test user model method to delete a single todo"""
        from .models import Tag
        from .models import TodoUser
        from .models import TodoItem

        user = TodoUser(
                email=u'king.arthur@example.com',
                first_name=u'Arthur',
                last_name=u'Pendragon',
        )
        self.session.add(user)

        tags = [u'quest', u'ni', u'knight']

        todo = TodoItem(user.email,
                                 u'Find a shrubbery',   
                                 [u'quest', u'ni', u'knight']                             
                                 ) 
        self.session.add(todo)
        
        user_todo = user.todo_list.one()
        self.assertTrue(todo is user_todo)
                     
                     
    def test_given_a_user_has_a_todo_When_I_delete_it_Then_it_is_gone(self):
        """test user model method to delete a single todo"""
        from .models import Tag
        from .models import TodoUser
        from .models import TodoItem

        user = TodoUser(
                email=u'king.arthur@example.com',
                first_name=u'Arthur',
                last_name=u'Pendragon',
        )
        self.session.add(user)

        tags = [u'quest', u'ni', u'knight']

        todo = TodoItem(user.email,
                                 u'Find a shrubbery',   
                                 [u'quest', u'ni', u'knight']                             
                                 ) 
        self.session.add(todo)
        
        #after inserting we have 1 todo
        user_todos = user.todo_list.count()
        self.assertEqual(user_todos, 1) 
        
        #after delete we have zero todos 
        user.delete_todo(todo.id)
        user_todos = user.todo_list.count()     
        self.assertEqual(user_todos, 0)               

        

        
class TodoItemModelTests(ModelTests):
      
    def _getTargetClass(self):
        from .models import TodoItem
        return TodoItem
    
    def _makeOne(self, user, task, tags=None, due_date=None):
        return self._getTargetClass()(user, task, tags, due_date)
    
    def test_constructor(self):
        instance = self._makeOne(1,
                                 u'Find a shrubbery')
        #trigger model
        instance.author
        
        #make assertions
        self.assertEqual(instance.user, 1)
        self.assertEqual(instance.task, u'Find a shrubbery')
        self.assertEqual(instance.due_date, None)
        self.assertEqual(instance.tags, [])
        
    def test_given_that_I_add_a_user_and_insert_a_task_with_several_tags_I_can_access_tag_collection(self):
        """tests model backref todoitem.tags"""
        from .models import Tag
        instance = self._makeOne(1,
                                 u'Find a shrubbery',
                                 [u'quest', u'ni', u'knight'])
        self.assertEqual(instance.tags[0].name, u'quest')
        self.assertEqual(instance.tags[1].name, u'ni')
        self.assertEqual(instance.tags[2].name, u'knight')
        
    def test_tag_relationship_todos(self):
        """test model backref tag.todos""" 
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
        
        
    def test_inserting_2_todoitems_with_same_tags_when_I_ask_for_tag_todos_then_I_get_2(self):
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
        
        #tag is referenced by 2 todo items
        tag = self.session.query(Tag).filter(Tag.name == u'quest').one()                
        self.assertEqual(tag.name, u'quest')
        self.assertEqual(len(tag.todos), 2)


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

    @unittest.skip('skip because view uses self.request.user provided by config.add_request_method')
    def test_anonymous(self):
        from .views import ToDoViews
        
        request = testing.DummyRequest()
        inst = ToDoViews(request)
        response = inst.home_view()
        self.assertEqual(response['user'], None)
        self.assertEqual(response['count'], None)
        self.assertEqual(response['section'], 'home')

        
class TestTagsView(ModelTests):
    
    def test_user_tags(self):
        """user model property"""
        from .models import Tag
        from .models import TodoUser
        from .models import TodoItem

        user = TodoUser(
                email=u'king.arthur@example.com',
                first_name=u'Arthur',
                last_name=u'Pendragon',
        )
        self.session.add(user)

        tags = [u'quest', u'ni', u'knight']

        todo = TodoItem(user.email,
                                 u'Find a shrubbery',   
                                 [u'quest', u'ni', u'knight']                             
                                 )   

        self.session.add(todo)
        user_tags = user.user_tags
        for user_tag in user_tags:
            self.assertIn(user_tag.tag_name, tags, '%s should be one of these tags %s' % (user_tag, tags))

class TestTagView(ModelTests):
    
    def test_todos_by_tag(self):
        """return user todos that are tagged with given tag
        
        saved IPython session to demonstrate SQLAlchemy API 
        In [1]: from todopyramid.models import *
    
        In [2]: user = DBSession.query(TodoUser).filter_by(first_name='Sascha').one()
        
        In [3]: user.todos
        Out[3]: 
        [TodoItem(u's.gottfried@hhpberlin.de', u'find tim', [<todopyramid.models.Tag object at 0xb38eccc>, <todopyramid.models.Tag object at 0xb38edac>], None),
         TodoItem(u's.gottfried@hhpberlin.de', u'find another knight', [<todopyramid.models.Tag object at 0xb38eccc>], datetime.datetime(2014, 2, 2, 23, 0)),
         TodoItem(u's.gottfried@hhpberlin.de', u'find tim', [<todopyramid.models.Tag object at 0xb38eccc>, <todopyramid.models.Tag object at 0xb38edac>], None),
         TodoItem(u's.gottfried@hhpberlin.de', u'find sascha', [<todopyramid.models.Tag object at 0xb38edac>], None)]
        
        In [4]: tag_filter = TodoItem.tags.any(Tag.name.in_([u'berlin']))
        
        In [5]: user.todo_list.filter(tag_filter).all()                 
        Out[5]: 
        [TodoItem(u's.gottfried@hhpberlin.de', u'find tim', [<todopyramid.models.Tag object at 0xb38eccc>, <todopyramid.models.Tag object at 0xb38edac>], None),
         TodoItem(u's.gottfried@hhpberlin.de', u'find tim', [<todopyramid.models.Tag object at 0xb38eccc>, <todopyramid.models.Tag object at 0xb38edac>], None),
         TodoItem(u's.gottfried@hhpberlin.de', u'find sascha', [<todopyramid.models.Tag object at 0xb38edac>], None)]
        
        In [6]: user.todo_list.filter(tag_filter).order_by(Tag.name)
        Out[6]: <sqlalchemy.orm.query.Query at 0xb51c38c>
        
        
        In [8]: user.todo_list.filter(tag_filter).order_by(TodoItem.task).all()
        Out[8]: 
        [TodoItem(u's.gottfried@hhpberlin.de', u'find sascha', [<todopyramid.models.Tag object at 0xb38edac>], None),
         TodoItem(u's.gottfried@hhpberlin.de', u'find tim', [<todopyramid.models.Tag object at 0xb38eccc>, <todopyramid.models.Tag object at 0xb38edac>], None),
         TodoItem(u's.gottfried@hhpberlin.de', u'find tim', [<todopyramid.models.Tag object at 0xb38eccc>, <todopyramid.models.Tag object at 0xb38edac>], None)]
        
        In [9]: from sqlalchemy import asc
        
        In [10]: from sqlalchemy import desc
        
        In [11]: user.todo_list.filter(tag_filter).order_by(asc(TodoItem.task)).all()
        Out[11]: 
        [TodoItem(u's.gottfried@hhpberlin.de', u'find sascha', [<todopyramid.models.Tag object at 0xb38edac>], None),
         TodoItem(u's.gottfried@hhpberlin.de', u'find tim', [<todopyramid.models.Tag object at 0xb38eccc>, <todopyramid.models.Tag object at 0xb38edac>], None),
         TodoItem(u's.gottfried@hhpberlin.de', u'find tim', [<todopyramid.models.Tag object at 0xb38eccc>, <todopyramid.models.Tag object at 0xb38edac>], None)]
        
        In [12]: user.todo_list.filter(tag_filter).order_by(desc(TodoItem.task)).all()
        Out[12]: 
        [TodoItem(u's.gottfried@hhpberlin.de', u'find tim', [<todopyramid.models.Tag object at 0xb38eccc>, <todopyramid.models.Tag object at 0xb38edac>], None),
         TodoItem(u's.gottfried@hhpberlin.de', u'find tim', [<todopyramid.models.Tag object at 0xb38eccc>, <todopyramid.models.Tag object at 0xb38edac>], None),
         TodoItem(u's.gottfried@hhpberlin.de', u'find sascha', [<todopyramid.models.Tag object at 0xb38edac>], None)]
        
        In [13]: user.todo_list.filter(tag_filter).order_by(desc(TodoItem.due_date)).all()
        Out[13]: 
        [TodoItem(u's.gottfried@hhpberlin.de', u'find sascha', [<todopyramid.models.Tag object at 0xb38edac>], None),
         TodoItem(u's.gottfried@hhpberlin.de', u'find tim', [<todopyramid.models.Tag object at 0xb38eccc>, <todopyramid.models.Tag object at 0xb38edac>], None),
         TodoItem(u's.gottfried@hhpberlin.de', u'find tim', [<todopyramid.models.Tag object at 0xb38eccc>, <todopyramid.models.Tag object at 0xb38edac>], None)]
        
        In [14]: user.todo_list.filter(tag_filter).order_by(asc(TodoItem.due_date)).all()
        Out[14]: 
        [TodoItem(u's.gottfried@hhpberlin.de', u'find sascha', [<todopyramid.models.Tag object at 0xb38edac>], None),
         TodoItem(u's.gottfried@hhpberlin.de', u'find tim', [<todopyramid.models.Tag object at 0xb38eccc>, <todopyramid.models.Tag object at 0xb38edac>], None),
         TodoItem(u's.gottfried@hhpberlin.de', u'find tim', [<todopyramid.models.Tag object at 0xb38eccc>, <todopyramid.models.Tag object at 0xb38edac>], None)]
         
        In [19]: tag_filter = TodoItem.tags.any(name=u'knight')
        
        In [20]: user.todo_list.filter(tag_filter).order_by(asc(TodoItem.due_date)).all()
        Out[20]: 
        [TodoItem(u's.gottfried@hhpberlin.de', u'find tim', [<todopyramid.models.Tag object at 0xb38eccc>, <todopyramid.models.Tag object at 0xb38edac>], None),
         TodoItem(u's.gottfried@hhpberlin.de', u'find tim', [<todopyramid.models.Tag object at 0xb38eccc>, <todopyramid.models.Tag object at 0xb38edac>], None),
         TodoItem(u's.gottfried@hhpberlin.de', u'find another knight', [<todopyramid.models.Tag object at 0xb38eccc>], datetime.datetime(2014, 2, 2, 23, 0))]
 
        """