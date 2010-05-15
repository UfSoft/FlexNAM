import getpass
from nam.database.upgrades.versions import *
from nam.utils.crypto import gen_pwhash, check_pwhash

DeclarativeBase = declarative_base()
metadata = DeclarativeBase.metadata


class User(DeclarativeBase):
    """Repositories users table"""
    __tablename__ = 'accounts'

    username        = db.Column(db.String, primary_key=True)
    display_name    = db.Column(db.String(50))
    password_hash   = db.Column(db.String, default="!")
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


class Source(DeclarativeBase):
    __tablename__   = 'sources'

    id              = db.Column(db.Integer, primary_key=True)
    uri             = db.Column(db.String)
    name            = db.Column(db.String)


class MessageKind(DeclarativeBase):
    __tablename__   = 'message_kinds'

    id              = db.Column(db.Integer, primary_key=True)
    kind            = db.Column(db.String)


class Messages(DeclarativeBase):
    __tablename__   = 'messages'

    id              = db.Column(db.Integer, primary_key=True)
    stamp           = db.Column(db.DateTime, default=datetime.utcnow)
    source          = db.Column(db.ForeignKey('sources.id'))
    kind            = db.Column(db.ForeignKey('message_kinds.id'))
    message         = db.Column(db.String)


def create_admin_user(migrate_engine):

    session = orm.create_session(migrate_engine, autoflush=True, autocommit=False)

    def ask_detail(question):
        detail = raw_input(question)
        if not detail:
            ask_detail(question)
        return detail

    def ask_password():
        try:
            # It's not a password being requested, it's a password to define
            passwd = getpass.getpass("Define a password for the new user:")
            if not passwd:
                return ask_password()
            verify_password = getpass.getpass("Verify Password:")
            if passwd != verify_password:
                print "Passwords do not match."
                return ask_password()
            return passwd
        except KeyboardInterrupt:
            exit(1)

    print "Creating initial administrator user"
    username = ask_detail("Initial Admin Username:")
    password = ask_password()

    user = User(username=username, password=password, is_admin=True)
    session.add(user)
    session.commit()

def upgrade(migrate_engine):
    # Upgrade operations go here. Don't create your own engine; use the engine
    # named 'migrate_engine' imported from migrate.
    metadata.create_all(migrate_engine)
    create_admin_user(migrate_engine)


def downgrade(migrate_engine):
    # Operations to reverse the above upgrade go here.
    metadata.drop_all(migrate_engine)

