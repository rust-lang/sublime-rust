# Rust Enhanced

## About

This is a Sublime Text 3 package which supports Rust starting with version 1.0,
it makes no attempt at supporting earlier incompatible versions.

As of version 1.0.0 this package will no longer support Sublime Text 2. At the time of writing, ST3 is almost reaching stable, and we recommend migrating to that version if you need Rust Support.

This package used to be called 'Rust', but as of version 3, Sublime now comes with Rust built-in.  The built-in version on Sublime is actually just a snapshot of this package [with some fixes](https://github.com/sublimehq/Packages/issues/178#issuecomment-197050427).
This package is still active and will continue to update and release, so if you want up to date features, and extra tools (such as syntax checking or building) we recommend using this package. It should override the default Rust within Sublime.
Syntax changes which happen here will eventually be pushed upstream into Sublime Core Packages repo, but extra features will stay here.

For syntax highlighting for Cargo files. Its recommended installing this with the TOML package.

## Installation

Install the Package Control package if you haven't got it yet. Package
Control is the best way to install packages for Sublime Text. See
http://wbond.net/sublime_packages/package_control/installation for
instructions.

Open the palette (`control+shift+P` or `command+shift+P`) in Sublime Text
and select `Package Control: Install Package` and then select `Rust Enhanced` from
the list. That's it.
If you can't see `Rust Enhanced` its most likely because you're using Sublime Text 2.

## Features
### Go To Definition
### Build functionality
Rust Enhanced has the following build functions:
- Cargo Run
- Cargo Test
- Cargo Bench
- Cargo Clean
- Cargo Release
- Cargo Document
- Cargo Clippy
- Rust
- Rust Run


### Cargo tests with highlighting
Thanks to [urschrei](https://github.com/urschrei/)  we have Highlighting for:
- passed test
- failed test
- failed test source line (clickable)
- total number of passed tests
- total number of failed tests > 0
- total number of ignored tests > 0
- total number of measured tests > 0

Example:   
![highlight_rust_test](https://cloud.githubusercontent.com/assets/936006/19247437/3cf6e056-8f23-11e6-9bbe-d8c542287db6.png)

### Syntax Checking
The sublime-rust package now comes with syntax checking.
This relies on Cargo and Rust (>= 1.8.0) being installed and on your system path. Plus Sublime Text >= 3118.
This feature is on by default, but you can adjust the the value of ```rust_syntax_checking``` within your settings (see Settings). Additionally, the colour of the warnings and errors can be changed from the default values (seen below).
```json
{
    "rust_syntax_checking": true,
    "rust_syntax_error_color": "#F00",
    "rust_syntax_warning_color":"#FF0"
}
```
Here is an example:
![testingrust](https://cloud.githubusercontent.com/assets/936006/18091147/938cb244-6ebf-11e6-9db1-b74e5bf4eebc.gif)

Projects with multiple build targets are supported too. If a cargo project has several build targets, it's possible to specify mapping of source file names to the target to enable proper cargo's build target selection during syntax checking.
Syntax checking is accomplished by command:
```bash
    cargo rustc {target} -- <some options>
```
where `{target}` is an empty string by default (perfectly works for cargo projects with only one build target). However, one can specify a certain target by updating plugin settings with the next section:
```
    "projects": {
       // One entry per project. Keys are project names.
       "my_cool_stuff": {
           // Path to the project root dir without trailing /src.
           "root": "/path/to/my/cool/stuff/project",

           // Targets will be used to replace {target} part in the command.
           // If no one target matches an, empty string will be used.
           "targets": {
               "bin/foo.rs": "--bin foo",  // format is "source_code_filename -> target_name"
               "bin/bar.rs": "--bin bar",
               "_default": "--lib"         // or "--bin main"
           }
       }
   }
```

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

We have just moved to the new .sublime-syntax file, which only supports ST3 and upwards. Any PR's should be updating this file and not the old tmLanguage file.

## Credits

Created 2012 by [Daniel Patterson](mailto:dbp@riseup.net), as a near complete from
scratch rewrite of a package by [Felix Martini](https://github.com/fmartini).

This project is currently maintained by [Jason Williams](https://github.com/jayflux)

## License

This package is licensed under the MIT License.
