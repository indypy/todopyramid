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
    due_date = Column(DateTime)
    user = Column(Integer, ForeignKey('users.email'))
    
    # # many to many TodoItem<->Tag
    tags = relationship("Tag", secondary=todoitemtag_table, backref="todos")

    def __init__(self, user, task, tags=None, due_date=None):
        self.user = user
        self.task = task
        self.due_date = due_date
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
        """
        return self.due_date and self.due_date < datetime.utcnow()


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
    todo_list = relationship(TodoItem, lazy='dynamic')

    def __init__(self, email, first_name=None, last_name=None,
                 time_zone=u'US/Eastern'):
        self.email = email
        self.first_name = first_name
        self.last_name = last_name
        self.time_zone = time_zone

    @property
    def user_tags(self):
        """Find all tags a user has created
        
        TODO: This can not be answered by the model
        I could not find a concept of user created tags       
        Currently we create user-related todoitems linking to tags that could have been created by other users   
        """
        qry = self.todo_list.session.query(todoitemtag_table.columns['tag_name'])
        qry = qry.join(TodoItem).filter_by(user=self.email)
        #qry = qry.group_by('tag_name')
        return qry.all()

    @property
    def profile_complete(self):
        """A check to see if the user has completed their profile. If
        they have not, in the view code, we take them to their account
        settings.
        """
        return self.first_name and self.last_name
