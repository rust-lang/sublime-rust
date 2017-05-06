#[macro_use]
extern crate dcrate;

fn main() {
    // This ensures that the expansion of nested macros works correctly.

    example!(inner!(b" "));
//  ^^^^^^^^^^^^^^^^^^^^^^^ERR no method named `missing`
}
