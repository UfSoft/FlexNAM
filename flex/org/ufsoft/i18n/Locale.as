/**
 * @author vampas
 */
package org.ufsoft.i18n {

  import flash.events.Event;
  import flash.events.EventDispatcher;
  import mx.collections.ItemResponder;
  import mx.collections.ArrayCollection;
  import mx.core.Application;
  import mx.resources.ResourceManager;
  import mx.resources.ResourceBundle;
  import mx.rpc.AsyncToken;
  import mx.rpc.events.ResultEvent;
  import mx.rpc.events.FaultEvent;

  import org.osflash.thunderbolt.Logger;

  import org.ufsoft.i18n.*;

  public class Locale extends EventDispatcher {

    private static var singleton:Locale;
    private var rb    : ResourceBundle;
    private var loaded: Boolean = false;

    public var _locale: String;
    public var bundle : String = "nam";

    public function Locale(caller:Function = null) {
      super();
      if(caller != Locale.getInstance) {
        throw new Error("Singleton is a singleton class, use Locale.getInstance() instead");
      }
      addEventListener(TranslationEvent.LOAD, backgroundLoad);
      addEventListener(TranslationEvent.PARSE, parseTranslation);
      addEventListener(TranslationEvent.LOADED, translationLoaded);
    }

    public static function getInstance():Locale {
      if (Locale.singleton == null) {
        Locale.singleton = new Locale(arguments.callee);
      }
      return Locale.singleton;
    }

    public function load(locale:String):void {
      if ( locale != this._locale) {
        this.loaded = false;
        Logger.info("Loading locale " + locale);
        this._locale = locale;
        dispatchEvent(new TranslationEvent(TranslationEvent.LOAD, locale));
      }
    }

    private function backgroundLoad(event:TranslationEvent):void {
      if ( ! ResourceManager.getInstance().getResourceBundle(event.locale, this.bundle ) ) {
        Logger.info("Creating Token");
        var token:AsyncToken = Application.application.getI18nService().get_translations(event.locale);
        Logger.info("Adding Token Responder", token);
        token.addResponder(new ItemResponder(loadComplete, loadFailed, token));
      } else {
        Logger.info("Dispatching Translation Loaded Event");
        dispatchEvent(new TranslationEvent(
          TranslationEvent.LOADED, event.locale, event.translations));
      }
    }

    public function loadComplete(event:ResultEvent, token:AsyncToken):void {
      var translations:ArrayCollection = event.result as ArrayCollection;
      Logger.info("Locale load complete", translations);
      dispatchEvent(new TranslationEvent(TranslationEvent.PARSE, getLocale(), translations));
    }

    public function loadFailed(event:FaultEvent, token:AsyncToken):void {
      Logger.info("Failed to load translations", event);
    }

    private function parseTranslation(event:TranslationEvent):void {
      Logger.info("Parsing locale " + event.locale);
      //Logger.info("Translations " + event.translations);
      rb = new ResourceBundle(event.locale, this.bundle);
      for each (var translation:Translation in event.translations ) {
        //trace(item);
        //Firebug.debug(item);
        //Logger.info("Got Translation Item:", translation);
        rb.content[translation.msgid] = translation.msgstr;
      }
      ResourceManager.getInstance().addResourceBundle(rb);
      Logger.info("Parsed locale " + getLocale());
      dispatchEvent(new TranslationEvent(
        TranslationEvent.LOADED, event.locale, event.translations));
    }

    private function translationLoaded(event:TranslationEvent):void {
      ResourceManager.getInstance().localeChain = [event.locale, 'en'];
      this.loaded = true;
      ResourceManager.getInstance().update();
      Logger.info("Loaded locale " + getLocale());
    }

    public function getLocale():String {
      return this._locale;
    }
  }
}


