#[macro_use]
extern crate dcrate;

fn main() {
    // This ensures that the expansion of nested macros works correctly.

    example!(inner!(b" "));
//  ^^^^^^^^^^^^^^^^^^^^^^^ERR no method named `missing`
//  ^^^^^^^^^^^^^^^^^^^^^^^ERR this error originates in a macro outside of the current crate
//  ^^^^^^^^^^^^^^^^^^^^^^^ERR(>=1.39.0-beta) method not found
}
