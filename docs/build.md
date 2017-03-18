# Cargo Build System

The Rust Enhanced build system provides an interface for running Cargo. It can
show inline warning and error messages.  It also has a variety of ways of
configuring options for how Cargo is run.

## Usage

When Sublime is set to use "Automatic" build system detection, it will choose
the build system based on the syntax of the currently active view.  If you
want to ensure the Rust Enhanced build system is used regardless of which file
is open, choose it via `Tools > Build System > RustEnhanced`.

The basic Sublime commands available are:

Command | Keyboard | Menu | Description
------- | -------- | ---- | -----------
Build | Ctrl-B / ⌘-B | Tools > Build | Runs the currently active build variant.
Build With... | Ctrl-Shift-B / ⌘-Shift-B | Tools > Build With... | Choose the build variant.
Cancel Build | Ctrl-Break / Ctrl-C | Tools > Cancel Build | Abort the currently running build.
Show Build Results | | Tools > Build Results > Show Build Results | Opens the output panel with build results.
Next Result | F4 | Tools > Build Results > Next Result | Go to the next warning/error message.
Previous Result | Shift-F4 | Tools > Build Results > Previous Result | Go to the previous warning/error message.

## Build Variants

When you select the RustEnhanced build system in Sublime, there are a few
variants that you can select with Tools > Build With... (
Ctrl-Shift-B / ⌘-Shift-B).  They are:

Variant | Command | Description
------- | ------- | -----------
(Default) | <code>cargo&nbsp;build</code> | Builds the project.
Run | <code>cargo&nbsp;run</code> | Runs the binary.
Run (with args)... | <code>cargo&nbsp;run&nbsp;-&#8288;-&#8288;&nbsp;*args*</code> | Runs the binary with optional arguments you specify.
Test | <code>cargo&nbsp;test</code> | Runs unit and integration tests.
Test (with args)... | <code>cargo&nbsp;test&nbsp;-&#8288;-&#8288;&nbsp;*args*</code> | Runs the test with optional arguments you specify.
Bench | <code>cargo&nbsp;bench</code> | Runs benchmarks.
Clean | <code>cargo&nbsp;clean</code> | Removes all built files.
Document | <code>cargo&nbsp;doc</code> | Builds package documentation.
Clippy | <code>cargo&nbsp;clippy</code> | Runs [Clippy](https://github.com/Manishearth/rust-clippy).  Clippy must be installed, and currently requires the nightly toolchain.
Script | <code>cargo&nbsp;script&nbsp;$path</code> | Runs [Cargo Script](https://github.com/DanielKeep/cargo-script).  Cargo Script must be installed.  This is an addon that allows you to run a Rust source file like a script (without a Cargo.toml manifest).

## Cargo Project Settings

You can customize how Cargo is run with settings stored in your
`sublime-project` file.  Settings can be applied per-target (`--lib`,
`--example foo`, etc.), for specific variants ("Build", "Run", "Test", etc.),
or globally.

### Setting Commands

There are several Sublime commands to help you configure the Cargo settings.
They can be accessed from the Command Palette (Ctrl-Shift-P / ⌘-Shift-P). They
are:

Command | Description
------- | -----------
Rust: Set Cargo Target | Set the Cargo target (`--lib`, `--example foo`, etc.) for each build variant.  The "Automatic Detection" option will attempt to determine which target to use based on the current active view in Sublime (a test file will use `--test` or a binary will use `--bin`, etc.).
Rust: Set Cargo Build Profile | Set whether or not to use the `--release` flag.
Rust: Set Cargo Target Triple | Set the target triple (such as `x86_64-apple-darwin`).
Rust: Set Cargo Features | Set the Cargo build features to use.
Rust: Set Cargo Toolchain | Set the Rust toolchain to use (`nightly`, `beta`, etc.).  Use the Targets > "All Targets" to set globally.

Caution: If you have not created a `sublime-project` file, then any changes
you make will be lost if you close the Sublime window.

### Settings

Settings are stored in your `sublime-project` file under the `"settings"` key.
Settings are organized per Cargo package.  The top-level keys for each package are:

Key | Description
--- | -----------
`"defaults"` | Default settings used if not set per target or variant.
`"targets"` | Settings per target.
`"variants"` | Settings per build variant.

An example of a `sublime-project` file:

```json
{
    "folders": [
        { "path": "." }
    ],
    "settings": {
        "cargo_build": {
            "paths": {
                "path/to/package": {
                    "defaults": {
                        "release": true
                    },
                    "targets": {
                        "--example ex1": {
                            "extra_run_args": "-f file"
                        }
                    },
                    "variants": {
                        "bench": {
                            "toolchain": "nightly"
                        },
                        "clippy": {
                            "toolchain": "nightly"
                        }
                    }
                }
            }
        }
    }
}
```

The available settings are:

Setting Name | Description
------------ | -----------
`release` | If true, uses the `--release` flag.
`target_triple` | If set, uses the `--target` flag with the given value.
`toolchain` | The Rust toolchain to use (such as `nightly` or `beta`).
`target` | The Cargo target (such as `"--bin myprog"`).  Applies to `variants` only.  Can be `"auto"` (see "Set Cargo Target" above).
`no_default_features` | If True, sets the `--no-default-features` flag.
`features` | A string with a space separated list of features to pass to the `--features` flag.  Set to "ALL" to pass the `--all-features` flag.
`extra_cargo_args` | Extra arguments passed to Cargo (before the `--` flags separator).
`extra_run_args` | Extra arguments passed to Cargo (after the `--` flags separator).

The extra args settings support standard Sublime variable expansion (see
[Build System
Variables](http://docs.sublimetext.info/en/latest/reference/build_systems/configuration.html#build-system-variables))

## Multiple Cargo Projects (Advanced)

You can have multiple Cargo projects in a single Sublime project (such as when
using Cargo workspaces, or if you simply have multiple projects in different
folders).

If you have multiple Cargo projects in your Sublime window, the build system
will use the currently active view to attempt to determine which project to
build.

## Custom Variants (Advanced)

TODO
