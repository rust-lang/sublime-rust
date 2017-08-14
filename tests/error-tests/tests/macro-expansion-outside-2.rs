#[macro_use]
extern crate dcrate;

// This is an example of an error in a macro from an external crate.  These
// messages do not have a file_name value, and thus will only be displayed in
// the console.
// example_bad_syntax!{}

fn f() {
    let x: () = example_bad_value!();
//              ^^^^^^^^^^^^^^^^^^^^ERR mismatched types
//              ^^^^^^^^^^^^^^^^^^^^ERR this error originates in a macro outside
//              ^^^^^^^^^^^^^^^^^^^^ERR expected (), found i32
//              ^^^^^^^^^^^^^^^^^^^^NOTE expected type
}
