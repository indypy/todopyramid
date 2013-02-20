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

    def __init__(self, task, tags, due_date):
        self.task = task
        self.due_date = due_date
        self.apply_tags(tags)

    def apply_tags(self, tags):
        for tag_name in tags:
            tag = tag_name.strip().lower()
            self.tags.append(DBSession.merge(Tag(tag)))
