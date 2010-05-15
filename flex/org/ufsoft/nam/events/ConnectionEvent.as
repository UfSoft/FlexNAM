/**
 * @author vampas
 */
package org.ufsoft.nam.events {

  import flash.events.Event;

  public class ConnectionEvent extends Event {

    public static const CONNECTING:String   = "connecting";
    public static const CONNECTED:String    = "connected";
    public static const RECONNECTING:String = "reconnecting";
    public static const DISCONNECTED:String = "disconnected";

    public function ConnectionEvent(type:String, bubbles:Boolean=true, cancelable:Boolean=false) {
      super(type, bubbles, cancelable);
    }

    override public function clone():Event {
      var event:ConnectionEvent = new ConnectionEvent(type, bubbles, cancelable);
      return event;
    }
  }
}
