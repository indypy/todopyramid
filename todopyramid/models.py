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

todoitemtag_table = Table(
    'todoitemtag',
    Base.metadata,
    Column('tag_id', Integer, ForeignKey('tags.name')),
    Column('todo_id', Integer, ForeignKey('todoitems.id')),
)


class RootFactory(object):
    __acl__ = [(Allow, Authenticated, 'view')]

    def __init__(self, request):
        pass


class Tag(Base):
    __tablename__ = 'tags'
    name = Column(Text, primary_key=True)
    todoitem_id = Column(Integer, ForeignKey('todoitems.id'))

    def __init__(self, name):
        self.name = name


class TodoItem(Base):
    __tablename__ = 'todoitems'
    id = Column(Integer, primary_key=True)
    task = Column(Text, nullable=False)
    due_date = Column(DateTime)
    tags = relationship(Tag, secondary=todoitemtag_table)
    user = Column(Integer, ForeignKey('users.email'), nullable=False)

    def __init__(self, user, task, tags=None, due_date=None):
        self.user = user
        self.task = task
        self.due_date = due_date
        self.apply_tags(tags)

    def apply_tags(self, tags):
        for tag_name in tags:
            tag = tag_name.strip().lower()
            self.tags.append(DBSession.merge(Tag(tag)))

    @property
    def sorted_tags(self):
        return sorted(self.tags, key=lambda x: x.name)

    @property
    def past_due(self):
        return self.due_date < datetime.utcnow()


class TodoUser(Base):
    __tablename__ = 'users'
    email = Column(Text, primary_key=True)
    first_name = Column(Text)
    last_name = Column(Text)
    todo_list = relationship(TodoItem, lazy='dynamic')

    def __init__(self, email, first_name=None, last_name=None):
        self.email = email
        self.first_name = first_name
        self.last_name = last_name
