/**
 * @author vampas
 */
package org.ufsoft.nam {
  import flash.display.DisplayObject;
  import flash.net.SharedObject;
  import flash.utils.setTimeout

  import mx.collections.ItemResponder;
  import mx.core.Application;
  import mx.controls.LinkButton;
  import mx.containers.VBox;
  import mx.managers.PopUpManager;
  import mx.messaging.Consumer;
  import mx.messaging.ChannelSet;
  import mx.messaging.channels.AMFChannel;
  import mx.messaging.channels.StreamingAMFChannel;
  import mx.messaging.events.ChannelEvent;
  import mx.messaging.events.ChannelFaultEvent;
  import mx.messaging.events.MessageEvent;
  import mx.messaging.events.MessageFaultEvent;
  import mx.messaging.messages.AsyncMessage;
  import mx.rpc.AsyncToken;
  import mx.rpc.AsyncResponder;
  import mx.rpc.remoting.mxml.RemoteObject;
  import mx.rpc.events.ResultEvent;
  import mx.rpc.events.FaultEvent;

  import org.osflash.thunderbolt.Logger;

  import org.ufsoft.i18n.*;
  import org.ufsoft.nam.components.Authentication;
  import org.ufsoft.nam.events.ConnectionEvent;
  import org.ufsoft.nam.models.User;

  public class NAMApplication extends Application {

    // Constants
    private static const CONNECT_TIMEOUT        :Number = 5;
    private static const MAX_CONNECTION_FAILURES:Number = 10;


    private var cookie:                       SharedObject;
    private var locale:                       Locale;

    // Connection related variables
    private var STREAMING_AVAILABLE:          Boolean;
    private var CONNECTED_ONCE:               Boolean=false;
    //private var serverAMFUrl:                 String;
    private var serverStreamingUrl:           String;
    private var serverPollingUrl:             String;
    private var serverLongPollingUrl:         String;
    private var streamingChannel:             StreamingAMFChannel;
    private var pollingChannel:               AMFChannel;
    private var longPollingChannel:           AMFChannel;
    private var servicesChannel:              AMFChannel;
    private var appChannelSet:                ChannelSet;
    private var conversionsConsumer:          Consumer;
    private var newConversionsConsumer:       Consumer;
    private var updatedConversionsConsumer:   Consumer;
    private var completedConversionsConsumer: Consumer;
    private var i18nService:                  RemoteObject;
    private var remoteService:                RemoteObject;
    private var connectionFailures:           Number = 0;
    private var authenticatedUsername:        String;
    private var authForm:                     Authentication = new Authentication();

    public var authenticatedUser:             User;
    public var sourcesBox:                    VBox;

    public function NAMApplication() {
      super();

      serverStreamingUrl = '/amf-streaming';
      serverPollingUrl = '/amf-polling';
      serverLongPollingUrl = '/amf-long-polling';

      cookie = SharedObject.getLocal("RTPNetworkAudioMonitor", "/");
      STREAMING_AVAILABLE = cookie.data.streaming_available || true;
      authenticatedUsername = cookie.data.username || "";
      locale = Locale.getInstance();
      locale.addEventListener(TranslationEvent.LOADED, translationLoaded);
      locale.load(cookie.data.locale || 'pt_PT');
    }

    public function setCookiePropery(name:String, value:Object):void {
      cookie.setProperty(name, value);
      cookie.flush();
    }

    private function translationLoaded(event:TranslationEvent):void {
      Logger.info("Translation Loaded. Storing locale in cookie");
      this.setCookiePropery('locale', Locale.getInstance().getLocale());
    }


    public function getChannel():ChannelSet {
      if ( appChannelSet != null ) {
        // channel set is defined already, return it
        return appChannelSet;
      }
      Logger.info("Creating channel");
      // Create a channel set and add channel(s) to it
      appChannelSet = new ChannelSet();

      if ( STREAMING_AVAILABLE ) {
        Logger.info("Streaming available. Adding streaming channel");
        streamingChannel = new StreamingAMFChannel("amf-streaming",
                                                  serverStreamingUrl);
        streamingChannel.connectTimeout = CONNECT_TIMEOUT;
        appChannelSet.addChannel(streamingChannel);
      }

      pollingChannel = new AMFChannel("amf-polling", serverPollingUrl);
      pollingChannel.pollingInterval = 2; // in seconds
      pollingChannel.connectTimeout = CONNECT_TIMEOUT;
      appChannelSet.addChannel(pollingChannel);

      longPollingChannel = new AMFChannel("amf-long-polling", serverPollingUrl);
      longPollingChannel.pollingInterval = 5; // in seconds
      longPollingChannel.connectTimeout = CONNECT_TIMEOUT;
      appChannelSet.addChannel(longPollingChannel);

      /*servicesChannel = new AMFChannel("rpc", serverAMFUrl)
      appChannelSet.addChannel(servicesChannel);*/

      appChannelSet.addEventListener(ChannelEvent.CONNECT, channelConnected);
      appChannelSet.addEventListener(ChannelEvent.DISCONNECT, channelDisconnected);
      appChannelSet.addEventListener(ChannelFaultEvent.FAULT, channelFault);
      return appChannelSet;
    }

    private function channelFault(event:ChannelFaultEvent):void {
      if ( event.channelId == "amf-streaming" && CONNECTED_ONCE==false ) {
        Logger.info("Permanently disabling streaming support")
        STREAMING_AVAILABLE = false;
        this.setCookiePropery('streaming_available', STREAMING_AVAILABLE);
      }
      Logger.error("channelFault", String(event));
      connectionFailures += 1;
    }

    private function channelConnected(event:ChannelEvent):void {
      if ( event.reconnecting ) {
        Logger.warn("channelConnected - Reconnecting", String(event));
        this.dispatchEvent(new ConnectionEvent(ConnectionEvent.RECONNECTING));
        setTimeout(queryConnection, 10);
      } else if ( event.rejected ) {
        Logger.error("channelConnected - Rejected", String(event));
        this.dispatchEvent(new ConnectionEvent(ConnectionEvent.DISCONNECTED));
        setTimeout(queryConnection, 10);
      } else {
        Logger.info("channelConnected - Connected", String(event));
        this.dispatchEvent(new ConnectionEvent(ConnectionEvent.CONNECTED));
        connectionFailures = 0;
        if ( ! CONNECTED_ONCE ) {
          CONNECTED_ONCE = true;
        }
      }
    }

    private function channelDisconnected(event:ChannelEvent):void {
      if ( event.reconnecting ) {
        Logger.warn("channelDisconnected - Reconnecting", String(event));
        this.dispatchEvent(new ConnectionEvent(ConnectionEvent.RECONNECTING));
      } else if ( event.rejected ) {
        Logger.error("channelDisconnected - Rejected", String(event));
        this.dispatchEvent(new ConnectionEvent(ConnectionEvent.DISCONNECTED));
      } else {
        Logger.info("channelDisconnected - Disconnected", String(event));
        this.dispatchEvent(new ConnectionEvent(ConnectionEvent.DISCONNECTED));
      }
      setTimeout(queryConnection, 10);
    }

    private function queryConnection():void {
      if ( appChannelSet.connected ) {
        this.dispatchEvent(new ConnectionEvent(ConnectionEvent.CONNECTED));
      } else if ( connectionFailures <= MAX_CONNECTION_FAILURES ) {
          setTimeout(queryConnection, 10);
      } else {
        Logger.warn("Desconnecting all channels");
        appChannelSet.disconnectAll();
      }
    }

    public function getI18nService():RemoteObject {
      if ( i18nService == null) {
        Logger.info("Creating I18N Service object");
        i18nService = new RemoteObject("I18N");
        i18nService.channelSet = getChannel();
        i18nService.showBusyCursor = true;
        i18nService.addEventListener(FaultEvent.FAULT, remoteServiceFault);
      };
      return i18nService;
    }

    public function getService():RemoteObject {
      if ( remoteService == null) {
        Logger.info("Creating Regular Service object");
        remoteService = new RemoteObject("NAM");
        remoteService.channelSet = getChannel();
        remoteService.showBusyCursor = true;
        remoteService.addEventListener(FaultEvent.FAULT, remoteServiceFault);
      };
      return remoteService;
    }

    private function remoteServiceFault(event:FaultEvent):void {
      Logger.error("remoteServiceFault", event);
    }

    public function toggleSourcesBox():void {
      if ( sourcesBox.width <=0 ) {
        sourcesBox.width = 300;
      } else if ( sourcesBox.width >=0 ) {
        sourcesBox.width = 0;
      }
    }

    public function showAuthForm():void {
      PopUpManager.addPopUp(authForm, DisplayObject(this), true);
    }

    public function loginUser(username:String, password:String):void {
      authenticatedUsername = username;
      var token:AsyncToken = appChannelSet.login(username, password);
      token.addResponder(new AsyncResponder(loginSucess, loginFailed));

      var utoken:AsyncToken = getService().get_user();
      token.addResponder(new ItemResponder(getAccountSuccess, getAccountFailure));
    }

    private function loginSucess(event:ResultEvent, token:AsyncToken):void {
      Logger.info("Authentication Success", event.result);
    }

    private function getAccountSuccess(event:ResultEvent, token:AsyncToken):void {
      //Logger.info("Get Account Success0", event);
      //Logger.info("Get Account Success1", event.result as User);
      authenticatedUser = event.result as User;
      Logger.info("Get Account Success II", authenticatedUser);
    }

    private function getAccountFailure(event:FaultEvent, token:AsyncToken):void {
      Logger.info("Get Account Failure", event.message);
    }

    private function loginFailed(event:FaultEvent, token:AsyncToken):void {
      Logger.info("Authentication Failure", event.message);
      PopUpManager.addPopUp(authForm, DisplayObject(this), true);
    }

    public function logoutUser():void {
      Logger.info("Logging out user");
      var token:AsyncToken = appChannelSet.logout();
      token.addResponder(new AsyncResponder(logoutSucess, logoutFailure));
    }

    private function logoutSucess(event:ResultEvent, token:AsyncToken):void {
      Logger.info("Logout Success", event.result);
      authenticatedUser = null;
    }

    private function logoutFailure(event:FaultEvent, token:AsyncToken):void {
      Logger.info("Logout Failure", event.message);
    }

    public function getAuthenticatedUsername():String {
      return authenticatedUsername;
    }
  }
}
