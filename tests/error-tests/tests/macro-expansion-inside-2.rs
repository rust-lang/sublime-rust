#[macro_use]
mod macro_expansion_inside_mod2;

// This is an example of an error in a macro from another module.

fn f() {
    let x: () = example_bad_value!();
//              ^^^^^^^^^^^^^^^^^^^^HELP in this macro invocation
}
