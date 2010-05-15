/**
 * @author vampas
 */
package org.ufsoft.i18n {

  import flash.events.Event;
  import mx.collections.ArrayCollection;
  import org.osflash.thunderbolt.Logger;

  public class TranslationEvent extends Event {
    public static const LOAD:    String = "LoadTranslation";
    public static const LOADED:  String = "LoadedTranslation";
    public static const PARSE:   String = "ParseTranslation";
    public static const FAILURE: String = "TranslationFailure";

    public var locale       : String;
    public var translations : ArrayCollection;

    public function TranslationEvent (type:         String,
                                      locale:       String  = null,
                                      translations: ArrayCollection   = null,
                                      bubbles:      Boolean = true,
                                      cancelable:   Boolean = false) {
      super(type, bubbles, cancelable);
      this.locale = locale;
      this.translations = translations;
      //Logger.info("New TranslationEvent. Locale:", locale, "Translations:", translations);

    }

    override public function clone():Event {
      return new TranslationEvent(type, locale, translations, bubbles, cancelable);
    }
  }
}


