import unittest
import transaction

from pyramid import testing

class TestTodoItem(unittest.TestCase):
    def setUp(self):
        self.config = testing.setUp()

    def tearDown(self):
        testing.tearDown()

    def test_create_todo(self):
        from .models import TodoItem
        model = TodoItem(user='bob', task='go do stuff')
        self.assertEqual(model.user, 'bob')
        self.assertEqual(model.task, 'go do stuff')

    def test_edit_todo(self):
        from .models import TodoItem
        model = TodoItem(user='bob', task='go do stuff')
        model.task = 'time for a beverage'
        self.assertEqual(model.user, 'bob')
        self.assertEqual(model.task, 'time for a beverage')

