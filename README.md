# Sublime Text package for Rust

## About

This package supports Rust starting with version 1.0,
it makes no attempt at supporting earlier incompatible versions.   
This package is soley for Sublime Text 3+, and may not work on version 2

## Installation

Install the Package Control package if you haven't got it yet. Package
Control is the best way to install packages for Sublime Text. See
http://wbond.net/sublime_packages/package_control/installation for
instructions.

Open the palette (`control+shift+P` or `command+shift+P`) in Sublime Text
and select `Package Control: Install Package` and then select `Rust` from
the list. That's it.  

## Syntax Checking
The sublime-rust package now comes with syntax checking.  
This relies on Cargo and Rust (>= 1.8.0) being installed and on your system path, and on Sublime Text >= 3118.
Once installed sublime will make a call to cargo to syntax check the project you're on then will feedback any line numbers which are failing by displaying a dot within the gutter of the editor. By clicking the dot you should get a tooltip of the error displayed.  
This feature is in Alpha stage and not on by default, so you will need to change the value of ```rust_syntax_checking``` to true within your settings (see Settings).   
```json
{
	"rust_syntax_checking": true
}
```
Here is an example:   
![testingrust](https://cloud.githubusercontent.com/assets/936006/18091147/938cb244-6ebf-11e6-9db1-b74e5bf4eebc.gif)

## Settings
You can customize the behaviour of sublime-rust by creating a settings file in your User package. This can be accessed from within SublimeText by going to the menu Preferences > Browse Packages.... Create a file named Rust.sublime-settings or alternatively copy the default settings file Packages/sublime-rust/Rust.sublime-settings to your User package and edit it to your liking.

Note: File names are case-sensitive on some platforms (e.g. Linux) so the file name should be exactly Rust.sublime-settings with capitalization preserved.

## Development

The files are written in the JSON format supported by the Sublime Text
package [AAAPackageDev](https://github.com/SublimeText/AAAPackageDev),
because the format is much easier to read / edit
than the xml based plist format.

So install that package and then work on the .JSON-* files. There is a
build system that comes with that package, so if everything is set up
right, you should just be able to trigger the build (F7) and get the
corresponding .tmLanguage / .tmPreferences files. It will also display
errors if you have not formatted the file correctly.

One impact of using this indirect format is that you usually have to double
escape anything in the match patterns, ie, "\\(" has to be "\\\\(" as otherwise
it will try to interpret '\\(' as a JSON escape code (which doesn't exist).

## Credits

Created 2012 by [Daniel Patterson](mailto:dbp@riseup.net), as a near complete from
scratch rewrite of a package by [Felix Martini](https://github.com/fmartini).

Derived primarily from the Vim syntax file, maintained by
[Patrick Walton](https://github.com/pcwalton) and
[Ben Blum](https://github.com/bblum)

Currently maintained by [Jason Williams](https://github.com/jayflux)

## License

This package is licensed under the MIT License.
