/**
 * @author vampas
 */
package org.ufsoft.nam.models {
  [Bindable]
  [RemoteClass(alias='org.ufsoft.nam.models.User')]

  public dynamic class User extends Object {
    public var username:  String;
    public var isAdmin:   Boolean;
  }
}

