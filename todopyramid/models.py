from datetime import datetime

from pyramid.security import Allow
from pyramid.security import Authenticated

from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import Table
from sqlalchemy import Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker
from zope.sqlalchemy import ZopeTransactionExtension

from .utils import localize_datetime
from .utils import universify_datetime

DBSession = scoped_session(sessionmaker(extension=ZopeTransactionExtension()))
Base = declarative_base()




class RootFactory(object):
    """This object sets the security for our application. In this case
    we are only setting the `view` permission for all authenticated
    users.
    """
    __acl__ = [(Allow, Authenticated, 'view')]

    def __init__(self, request):
        pass

todoitemtag_table = Table(
    'todoitemtags',
    Base.metadata,
    Column('tag_name', Integer, ForeignKey('tags.name')),
    Column('todo_id', Integer, ForeignKey('todoitems.id')),
)


class TodoItem(Base):
    """This is the main model in our application. This is what powers
    the tasks in the todo list.
    """
    __tablename__ = 'todoitems'
    id = Column(Integer, primary_key=True)
    task = Column(Text, nullable=False)
    _due_date = Column('due_date', DateTime)
    user = Column(Integer, ForeignKey('users.email'))
    author = relationship('TodoUser')
    
    # # many to many TodoItem<->Tag
    tags = relationship("Tag", secondary=todoitemtag_table, backref="todos")

    def __init__(self, user, task, tags=None, due_date=None):
        self.user = user
        self.task = task
        self.due_date = due_date # date will be universified
        if tags is not None:
            self.apply_tags(tags)

    def apply_tags(self, tags):
        """This helper function merely takes a list of tags and
        creates the associated tag object. We strip off whitespace
        and lowercase the tags to keep a normalized list.
        """

        for tag_name in tags:
            tag_name = self.sanitize_tag(tag_name)
            tag = self._find_or_create_tag(tag_name)
            self.tags.append(tag)
            
    def sanitize_tag(self, tag_name):
        """tag name input validation"""
        tag = tag_name.strip().lower()
        return tag    

    def _find_or_create_tag(self, tag_name):
        """ensure tag names are unique
        
        http://stackoverflow.com/questions/2310153/inserting-data-in-many-to-many-relationship-in-sqlalchemy
        
        why we need that - prevent multiple tags  
        http://stackoverflow.com/questions/13149829/many-to-many-in-sqlalchemy-preventing-sqlalchemy-from-inserting-into-a-table-if
        """
        q = DBSession.query(Tag).filter_by(name=tag_name)
        t = q.first()
        if not(t):
            t = Tag(tag_name)
        return t

    @property
    def sorted_tags(self):
        """Return a list of sorted tags for this task.
        
        TODO: we can apply sorting using the relationship 
        """
        return sorted(self.tags, key=lambda x: x.name)

    @property
    def past_due(self):
        """Determine if this task is past its due date. Notice that we
        compare to `utcnow` since dates are stored in UTC.
        
        TODO: write tests
        """
        return self._due_date and self._due_date < datetime.utcnow()
    
    def universify_due_date(self, date):
        """convert datetime to UTC for storage"""
        if date is not None:
            self._due_date = universify_datetime(date)
        
    def localize_due_date(self):
        """create a timezone-aware object for a given datetime and timezone name
        """
        if self._due_date is not None and hasattr(self.author, 'time_zone'):
            due_dt = localize_datetime(self._due_date, self.author.time_zone)
            return due_dt
        return self._due_date
    
    due_date = property(localize_due_date, universify_due_date)
    
    def __repr__(self):
        """return representation - helps in IPython"""
        return "TodoItem(%r, %r, %r, %r)" % (self.user, self.task, self.tags, self.due_date)


class Tag(Base):
    """The Tag model is a many to many relationship to the TodoItem.
    
    http://docs.sqlalchemy.org/en/rel_0_9/orm/tutorial.html#building-a-many-to-many-relationship
    """
    __tablename__ = 'tags'

    #id = Column(Integer, primary_key=True)
    #name = Column(Text, nullable=False, unique=True)

    name = Column(Text, primary_key=True)


    def __init__(self, name):
        self.name = name
        
    def __repr__(self):
        """return representation - helps in IPython"""
        return "Tag(%r)" % (self.name)        


class TodoUser(Base):
    """When a user signs in with their persona, this model is what
    stores their account information. It has a one to many relationship
    with the `TodoItem` model to create the `todo_list`.
    """
    __tablename__ = 'users'
    email = Column(Text, primary_key=True)
    first_name = Column(Text)
    last_name = Column(Text)
    time_zone = Column(Text)
    todos = relationship(TodoItem)
    todo_list = relationship(TodoItem, lazy='dynamic')

    def __init__(self, email, first_name=None, last_name=None,
                 time_zone=u'US/Eastern'):
        self.email = email
        self.first_name = first_name
        self.last_name = last_name
        self.time_zone = time_zone

    
    def todos_by_tag(self, tag, order):
        """return user todos with given tag"""
        tag_filter = TodoItem.tags.any(name=tag)
        qry = self.todo_list.filter(tag_filter)
    
        if order:
            qry.order_by(order)
            
        return qry.all() 
    

    @property
    def user_tags(self):
        """Find all tags a user has created
        
        BUG: does not find user created tags that actually have no related todos
        
        returns KeyedTuples with key 'tag_name' 
        TODO: refactor to return collection of Tag model - consider lazy
        
        explore code samples - we also have user/author model and a many-to-many relationship between todo and tag
        http://docs.sqlalchemy.org/en/rel_0_9/orm/tutorial.html#building-a-many-to-many-relationship         
        """
        qry = self.todo_list.session.query(todoitemtag_table.columns['tag_name'])
        qry = qry.join(TodoItem).filter_by(user=self.email)
        qry = qry.group_by('tag_name')
        qry = qry.order_by('tag_name')
        return qry.all()

    def user_tags_autocomplete(self, term):
        """given a term return a unique collection (set) of user tags that start with it
        
        
        In [19]: for todo in user.todos:
            for tag in todo.tags:
                if tag.name.startswith('ber'):
           ....:             print tag.name
           ....:             
        berlin
        berlin
        berlin
        berlin
        """
        matching_tags = set()
        for todo in self.todos:
            for tag in todo.tags:
                if tag.name.startswith(term):
                    matching_tags.add(tag)
        
        return matching_tags
        
        
    @property
    def profile_complete(self):
        """A check to see if the user has completed their profile. If
        they have not, in the view code, we take them to their account
        settings.
        """
        return self.first_name and self.last_name
    
    def delete_todo(self, todo_id):
        """given a todo ID we delete it is contained in user todos 
        
        delete from a collection
        http://docs.sqlalchemy.org/en/latest/orm/session.html#deleting-from-collections
        http://stackoverflow.com/questions/10378468/deleting-an-object-from-collection-in-sqlalchemy"""
        todo_item = self.todo_list.filter(
                TodoItem.id == todo_id)

        todo_item.delete()
        
    def create_todo(self, task, tags=None, due_date=None):
        """may be we prefer using this method from authenticated views
        this way we always create a user TodoItem instead of allowing view code to modify SQLAlchemy TodoItem collection 
        """
        #check common pitfall - mutable as default argument 
        if tags==None:
            tags = []
            
        todo = TodoItem(self.email, task, tags, due_date)
        self.todos.append(todo)
        
    def edit_todo(self, todo_id, task, tags=None, due_date=None):
        todo = self.todo_list.filter_by(id=todo_id).one()
        todo.task = task
        todo.apply_tags(tags)
        todo.due_date = due_date
    
    def update_prefs(self, first_name, last_name, time_zone=u'US/Eastern'):
        """update account preferences""" 
        self.first_name = first_name
        self.last_name = last_name
        self.time_zone = time_zone
    
    
