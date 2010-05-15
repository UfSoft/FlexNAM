'''
Created on 21 Apr 2010

@author: vampas
'''

from ConfigParser import SafeConfigParser
from types import ModuleType
from os import makedirs, listdir, remove
from os.path import (abspath, basename, dirname, expanduser, join, isfile,
                     isdir, splitext)

from babel.core import Locale, UnknownLocaleError
from babel.messages.mofile import read_mo

from twisted.web import static, server, resource, vhost
from twisted.internet import reactor

usefull_path = lambda path: abspath(expanduser(path))

LOCALES_DIR = join(dirname(__file__), 'locale')

AS_NAMESPACE = 'org.ufsoft.nam'
AS_MODELS_NAMESPACE = '%s.models' % AS_NAMESPACE
AS_I18N_NAMESPACE = 'org.ufsoft.i18n'

class Translation(object):
    def __init__(self, msgid, msgstr):
        self.msgid = msgid
        self.msgstr = msgstr


class Language(object):
    def __init__(self, locale, display_name):
        self.locale = locale
        self.display_name = display_name


class Application(object):

    def __init__(self):
        self.config = ModuleType('nam.config')
        self.config.file = 'nam.ini'
        self.config.parser = SafeConfigParser()
        self.locales = {}
        self.languages = []

    def config_initial_populate(self):
        parser = self.config.parser
        parser.add_section('main')
        parser.set("main", "uploads_dir", '%(here)s/uploads')
        parser.set("main", "database_uri", '')

    def config_load(self, config_dir=None):
        config_dir = config_dir or self.config.dir
        parser = self.config.parser
        parser.read([join(config_dir, self.config.file)])
        self.config.parser.set('DEFAULT', 'here', config_dir)
        self.config.uploads_dir = usefull_path(parser.get('main',
                                                          'uploads_dir'))
        if not isdir(self.config.uploads_dir):
            makedirs(self.config.uploads_dir)

        self.config.database_uri = parser.get('main', 'database_uri')

    def config_save(self, config_dir=None):
        config_dir = config_dir or self.config.dir
        self.config.parser.remove_option('DEFAULT', 'here')
        self.config.parser.remove_section('DEFAULT')
        self.config.parser.write(open(join(config_dir, self.config.file), 'w'))

    def setup_locales(self):
        for locale in listdir(LOCALES_DIR):
            locale_dir = join(LOCALES_DIR, locale)

            if not isdir(locale_dir):
                continue
            try:
                l = Locale.parse(locale)
            except UnknownLocaleError:
                continue

            mo_file = join(LOCALES_DIR, locale, 'LC_MESSAGES', 'messages.mo')
            if not isfile(mo_file):
                continue

            self.languages.append(Language(locale, l.display_name))
            self.locales[locale] = []

            catalog = read_mo(open(mo_file, 'rb'))
            for msg in list(catalog)[1:]:
                self.locales[locale].append(
                    Translation(msg.id, msg.string and msg.string or msg.id)
                )
        self.languages.sort(key=lambda x: x.display_name.lower())

    def setup_logging(self):
        import logging
        global log
        log = logging.getLogger(__name__)

    def build_root(self):
        from nam.database import db, User, AnonymousUser
        from nam import controllers
        from amfast.class_def.code_generator import CodeGenerator
        from amfast.class_def import ClassDefMapper, DynamicClassDef
        from amfast.class_def.sa_class_def import SaClassDef
        from amfast.decoder import Decoder
        from amfast.encoder import Encoder
        from amfast.remoting import Service, CallableTarget, ExtCallableTarget
        from amfast.remoting.sa_connection_manager import SaConnectionManager
        from amfast.remoting.sa_subscription_manager import SaSubscriptionManager
        from amfast.remoting.twisted_channel import (TwistedChannel,
                                                     TwistedChannelSet,
                                                     StreamingTwistedChannel)


        class SACallableTarget(CallableTarget):
            def invoke(self, packet, msg, args):
                try:
                    CallableTarget.session = db.session()
                    return CallableTarget.invoke(self, packet, msg, args)
                finally:
                    CallableTarget.session.close()
                    del CallableTarget.session


        # If the code is completely asynchronous,
        # you can use the dummy_threading module
        # to avoid RLock overhead.
#        import dummy_threading
#        amfast.mutex_cls = dummy_threading.RLock

        share_path = join(dirname(__file__), 'shared')
        root = vhost.NameVirtualHost()
        root.default = static.File(share_path)
        root.addHost("localhost", static.File(share_path))

#        root.putChild("upload", controllers.UploadResource())
        root.putChild("uploads", static.File(self.config.uploads_dir))


        # Setup ChannelSet
        channel_set = TwistedChannelSet(notify_connections=True)

        # Check authentication
        authentication = controllers.Auth()
        channel_set.checkCredentials = authentication.authenticate

        # Setup connection manager
        channel_set.connection_manager = SaConnectionManager(
            self.database_engine,
            db.metadata,
#            table_prefix='amfast_'
        )
        channel_set.connection_manager.createTables()

        channel_set.subscription_manager = SaSubscriptionManager(
            self.database_engine,
            db.metadata,
#            table_prefix='amfast_'
        )
        channel_set.subscription_manager.createTables()

        # Map class aliases
        # These same aliases must be
        # registered in the client
        # with the registClassAlias function,
        # or the RemoteClass metadata tag.
        class_mapper = ClassDefMapper()
        class_mapper.mapClass(DynamicClassDef(
            Translation, '%s.Translation' % AS_I18N_NAMESPACE
        ))
        class_mapper.mapClass(DynamicClassDef(
            Language, '%s.Language' % AS_I18N_NAMESPACE
        ))

#        # Database class aliases
#        class_mapper.mapClass(SaClassDef(User, '%s.User' % AS_MODELS_NAMESPACE))
#        class_mapper.mapClass(SaClassDef(AnonymousUser, '%s.AnonymousUser' % AS_MODELS_NAMESPACE))

        class_mapper.mapClass(DynamicClassDef(User, '%s.User' % AS_MODELS_NAMESPACE, ('username', 'is_admin', 'is_somebody')))
#        class_mapper.mapClass(DynamicClassDef(AnonymousUser, '%s.AnonymousUser' % AS_MODELS_NAMESPACE))

#        class_mapper.mapClass(SaClassDef(Sound, '%s.Sound' % AS_NAMESPACE))
#        class_mapper.mapClass(SaClassDef(SoundTag, '%s.SoundTag' % AS_NAMESPACE))


        # Map service targets to controller methods
        sa_obj = controllers.SAObject()
        sa_service = Service('SA')
        sa_service.mapTarget(SACallableTarget(sa_obj.load, 'load'))
        sa_service.mapTarget(SACallableTarget(sa_obj.loadAttr, 'loadAttr'))
        sa_service.mapTarget(SACallableTarget(sa_obj.loadAll, 'loadAll'))
        sa_service.mapTarget(SACallableTarget(sa_obj.saveList, 'saveList'))
        sa_service.mapTarget(SACallableTarget(sa_obj.save, 'save'))
        sa_service.mapTarget(SACallableTarget(sa_obj.remove, 'remove'))
        sa_service.mapTarget(SACallableTarget(sa_obj.removeList, 'removeList'))
        sa_service.mapTarget(SACallableTarget(sa_obj.insertDefaultData, 'insertDefaultData'))
        channel_set.service_mapper.mapService(sa_service)

        # I18N Service
        i18n_obj = controllers.I18nService()
        i18n_service = Service('I18N')
        i18n_service.mapTarget(ExtCallableTarget(i18n_obj.get_languages, 'get_languages'))
        i18n_service.mapTarget(ExtCallableTarget(i18n_obj.get_translations, 'get_translations'))
        channel_set.service_mapper.mapService(i18n_service)

        nam_service = Service('NAM')
        nam_service.mapTarget(ExtCallableTarget(authentication.get_user, 'get_user'))
        channel_set.service_mapper.mapService(nam_service)

        # Streaming
        amf_streaming = StreamingTwistedChannel('amf-streaming')
        channel_set.mapChannel(amf_streaming)

        # Regular polling
        amf_polling = TwistedChannel('amf-polling')
        channel_set.mapChannel(amf_polling)

        # Long polling
        amf_long_polling = TwistedChannel('amf-long-polling',
                                          wait_interval=90000)
        channel_set.mapChannel(amf_long_polling)

        # Set Channel options
        # We're going to use the same
        # Encoder and Decoder for all channels
        encoder = Encoder(use_collections=True, use_proxies=True,
                          class_def_mapper=class_mapper, use_legacy_xml=True)
        decoder = Decoder(class_def_mapper=class_mapper)
        for channel in channel_set:
            channel.endpoint.encoder = encoder
            channel.endpoint.decoder = decoder

        root.putChild('amf-streaming', amf_streaming)
        root.putChild('amf-polling', amf_polling)
        root.putChild('amf-long-polling', amf_long_polling)
        self.server = server.Site(root)
        self.channel_set = channel_set

        # Generate source code for mapped models
#        coder = CodeGenerator(indent='  ')
#        coder.generateFilesFromMapper(class_mapper, use_accessors=False,
#                                      packaged=True, constructor=False,
#                                      bindable=True, extends='Object',
#                                      dir=join(self.config.dir, '..', 'flex'))


        return self.server


    def save_file(self, filename, filedata):
        output = join(self.config.uploads_dir, filename)
        f = open(output, 'wb')
        f.write(filedata)
        f.close()
        self.add_conversion(filename)

    def emit_flex_message(self, headers=None, body=None, topic='messages'):
        from amfast.remoting import flex_messages
        msg = flex_messages.AsyncMessage(headers=headers, body=body,
                                         destination=topic)
        self.channel_set.publishMessage(msg)

    def emit_flex_object(self, headers=None, body=None, topic='messages',
                         sub_topic=None):
        self.channel_set.publishObject(body, topic, sub_topic=sub_topic,
                                       headers=headers, ttl=30000)

application = Application()
