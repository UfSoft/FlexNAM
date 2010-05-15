
import logging
from twisted.web import resource
from amfast.remoting.channel import SecurityError
from nam.core import application
from nam.database import db, AnonymousUser, User
from twisted.mail.test.test_imap import Account

log = logging.getLogger(__name__)

class FUser(object):
    def __init__(self, username, is_somebody, is_admin):
        self.username = username
        self.is_somebody = is_somebody
        self.is_admin = is_admin

class Auth(object):
    def authenticate(self, username, password):
        try:
            session = db.session()
            user = session.query(User).get(username)
            if user:
                return user.check_password(password)
            raise SecurityError("Invalid Credentials")
        finally:
            session.close()

    def get_user(self, packet, message):
        # Get a Connection object from a Flex message.
        my_flex_message = message.body[0]
        connection = my_flex_message.connection
        try:
            session = db.session()
            account = session.query(User).get(connection.flex_user)
            if account:
                log.debug("REturning account %s", account)
#                return FUser(account.username, account.is_somebody, account.is_admin)
#                session.expunge(account)
                return account
            log.debug("REturning annonymous account")
            return AnonymousUser()
        finally:
            session.close()


class SAObject(object):
    """Handles common operations for persistent objects."""

    def getClassDefByAlias(self, alias):
        return self.class_def_mapper.getClassDefByAlias(alias)

#---- These operations are performed on a single object. ---#
    def load(self, class_alias, key):
        class_def = self.getClassDefByAlias(class_alias)
        session = db.session()
        return session.query(class_def.class_).get(key)

    def loadAttr(self, class_alias, key, attr):
        obj = self.load(class_alias, key)
        return getattr(obj, attr)

    def save(self, obj):
        session = db.session()
        merged_obj = session.merge(obj)
        session.commit()
        return merged_obj

    def saveAttr(self, class_alias, key, attr, val):
        session = db.session()
        obj = self.load(class_alias, key)
        setattr(obj, attr, val)
        session.commit()
        return getattr(obj, attr)

    def remove(self, class_alias, key):
        class_def = self.getClassDefByAlias(class_alias)
        session = db.session()
        obj = session.query(class_def.class_).get(key)
        session.delete(obj)
        session.commit()

#---- These operations are performed on multiple objects. ----#
    def loadAll(self, class_alias):
        class_def = self.getClassDefByAlias(class_alias)
        session = db.session()
        return session.query(class_def.class_).all()

    def saveList(self, objs):
        for obj in objs:
            self.save(obj)
        return objs

    def removeList(self, class_alias, keys):
        for key in keys:
            self.remove(class_alias, key)

    def insertDefaultData(self):
        user = models.User()
        user.first_name = 'Bill'
        user.last_name = 'Lumbergh'
        for label, email in {'personal': 'bill@yahoo.com', 'work': 'bill@initech.com'}.iteritems():
            email_obj = models.Email()
            email_obj.label = label
            email_obj.email = email
            user.emails.append(email_obj)

        for label, number in {'personal': '1-800-555-5555', 'work': '1-555-555-5555'}.iteritems():
            phone_obj = models.PhoneNumber()
            phone_obj.label = label
            phone_obj.number = number
            user.phone_numbers.append(phone_obj)

        session = db.session()
        session.add(user)
        session.commit()


class I18nService(object):
    def get_languages(self, packet, message, locale='en'):
        log.debug("Returning languages: %s", application.languages)
        return application.languages

    def get_translations(self, packet, message, locale):
        log.debug("Returning translations for locale: %s: %s", locale,
                  application.locales.get(locale, application.locales['en']))
        if locale in application.locales:
            return application.locales[locale]
        return application.locales['en']

class UploadsResource(resource.Resource):
    def render_POST(self, request):
        filename = request.args['Filename'][0]
        filedata = request.args['Filedata'][0]
        session = db.session()

