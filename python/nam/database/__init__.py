# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8 et
"""
    nam.database
    ~~~~~~~~~~~~~~~~~~~~~

    This module is a layer on top of SQLAlchemy to provide asynchronous
    access to the database and has the used tables/models used in the
    application

    :copyright: © 2010 UfSoft.org - Pedro Algarvio <ufs@ufsoft.org>
    :license: BSD, see LICENSE for more details.
"""

import os
import sys
import logging
from os import path
from datetime import datetime
from types import ModuleType
from uuid import uuid4

import sqlalchemy
from sqlalchemy import and_, or_
from sqlalchemy import orm
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.engine.url import make_url, URL

from nam.utils.crypto import gen_pwhash, check_pwhash

from twisted.conch.ssh.keys import Key
from twisted.python import log as twlog

log = logging.getLogger(__name__)

def get_engine():
    """Return the active database engine (the database engine of the active
    application).  If no application is enabled this has an undefined behavior.
    If you are not sure if the application is bound to the active thread, use
    :func:`~zine.application.get_application` and check it for `None`.
    The database engine is stored on the application object as `database_engine`.
    """
    from nam.core import application
    return application.database_engine

def create_engine():
    if config.db.engine == 'sqlite':
        info = URL('sqlite', database=path.join(config.db.path, config.db.name))
    else:
        if config.db.username and config.db.password:
            uri = '%(engine)s://%(username)s:%(password)s@%(host)s/%(name)s'
        if config.db.username and not config.db.password:
            uri = '%(engine)s://%(username)s@%(host)s/%(name)s'
        else:
            uri = '%(engine)s://%(host)s/%(name)s'
        info = make_url(uri % config.db.__dict__)
    if info.drivername == 'mysql':
        info.query.setdefault('charset', 'utf8')
    options = {'convert_unicode': True, 'echo': config.db.echo}
    # alternative pool sizes / recycle settings and more.  These are
    # interpreter wide and not from the config for the following reasons:
    #
    # - system administrators can set it independently from the webserver
    #   configuration via SetEnv and friends.
    # - this setting is deployment dependent should not affect a development
    #   server for the same instance or a development shell
    for key in 'pool_size', 'pool_recycle', 'pool_timeout':
        value = os.environ.get('SB_DATABASE_' + key.upper())
        if value is not None:
            options[key] = int(value)
    return sqlalchemy.create_engine(info, **options)

def session():
    return orm.create_session(get_engine(), autoflush=True, autocommit=False)

#: create a new module for all the database related functions and objects
sys.modules['nam.database.db'] = db = ModuleType('db')
key = value = mod = None
for mod in sqlalchemy, orm:
    for key, value in mod.__dict__.iteritems():
        if key in mod.__all__:
            setattr(db, key, value)
del key, mod, value
db.and_ = and_
db.or_ = or_
#del and_, or_

DeclarativeBase = declarative_base()
metadata = DeclarativeBase.metadata

db.session = session
db.metadata = metadata


class SchemaVersion(DeclarativeBase):
    """SQLAlchemy-Migrate schema version control table."""

    __tablename__   = 'migrate_version'
    repository_id   = db.Column(db.String(255), primary_key=True)
    repository_path = db.Column(db.Text)
    version         = db.Column(db.Integer)

    def __init__(self, repository_id, repository_path, version):
        self.repository_id = repository_id
        self.repository_path = repository_path
        self.version = version


class User(DeclarativeBase):
    """Repositories users table"""
    __tablename__ = 'accounts'

    is_somebody     = True

    username        = db.Column(db.String, primary_key=True)
    display_name    = db.Column(db.String(50))
    password_hash   = db.Column(db.String)
    added_on        = db.Column(db.DateTime, default=datetime.utcnow)
    last_login      = db.Column(db.DateTime, default=datetime.utcnow)
    is_admin        = db.Column(db.Boolean, default=False)

    def __init__(self, username=None, display_name=None, password=None,
                 is_admin=False):
        self.username = username
        self.display_name = display_name
        if password:
            self.set_password(password)
        self.is_admin = is_admin

    def set_password(self, password):
        self.password_hash = gen_pwhash(password)

    def check_password(self, password):
        if self.password_hash == '!':
            return False
        if check_pwhash(self.password_hash, password):
            self.last_login = datetime.utcnow()
            return True
        return False

class AnonymousUser(User):
    is_somebody = is_admin = False

class Source(DeclarativeBase):
    __tablename__   = 'sources'

    id              = db.Column(db.Integer, primary_key=True)
    uri             = db.Column(db.String)
    name            = db.Column(db.String)
    logo            = db.Column(db.String)
