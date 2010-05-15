package org.ufsoft.nam.models
{
  import org.osflash.thunderbolt.Logger;

  [RemoteClass(alias='org.ufsoft.nam.models.User')]
  [Bindable]
  public dynamic class User extends Object
  {
    public var username:    String;
    public var is_admin:    Boolean;
    public var is_somebody: Boolean;

    /*public function User():void {
      Logger.info("USER", this);
      super();
    }*/
  }
}


