/**
 * @author vampas
 */
package org.ufsoft.nam.components {
  import mx.binding.utils.*;
  import mx.containers.*;
  import mx.controls.*;
  import mx.core.Application;
  import mx.core.ScrollPolicy;

  public class SourceUI extends VBox {
    [Bindable] public var sourceName: String;
    private var sourceNameText:         Text;
    private var configButton:           Image;
    private var buffer:                 ProgressBar;

    [Embed(source='/assets/images/configure.png')]
    [Bindable] private var configIcon:Class;

    public function SourceUI() {
      super();

      this.styleName = "sourceBox";
      this.percentWidth = 100;
      verticalScrollPolicy = ScrollPolicy.OFF;
      horizontalScrollPolicy = ScrollPolicy.OFF;

      var topBox:HBox = new HBox();
      topBox.percentWidth = 100;
      var sourceNameText:Text = new Text();

      sourceNameText.text = "@c{sourceName}";
      topBox.addChild(sourceNameText);

      var spacer:Spacer = new Spacer();
      spacer.percentWidth = 100;
      topBox.addChild(spacer);

      configButton = new Image();
      configButton.source = configIcon;
      //configButton.setStyle("icon", configIcon);
      configButton.setStyle("height", 16);
      configButton.setStyle("width", 16);
      configButton.useHandCursor = true;
      configButton.buttonMode = true;
      topBox.addChild(configButton);

      this.addChild(topBox);

      buffer = new ProgressBar();
      buffer.label = "";
      buffer.mode = ProgressBarMode.MANUAL;
      buffer.percentWidth = 100;
      buffer.labelPlacement="right";

      this.addChild(buffer);

      //BindingUtils.bindProperty(this.sourceNameText, "text", this._sourceName);
      //BindingUtils.bindProperty(this, _sourceName, this.sourceNameText, "text");
    }

    /*public function set sourceName(value:String):void {
      this._sourceName = value;
    }
    public function get sourceName():String {
      return this._sourceName;
    }*/
  }
}
