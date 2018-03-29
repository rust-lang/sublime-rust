#[macro_use]
mod macro_expansion_inside_mod1;

// This is an example of an error in a macro from another module.

/*BEGIN*/example_bad_syntax!{}/*END*/
// ~HELP(>=1.20.0) in this macro invocation
// ~HELP(>=1.20.0) in this macro invocation
// ~MSG(>=1.20.0) See Primary: macro_expansion_inside_mod1.rs:7
// ~MSG(>=1.20.0) See Primary: macro_expansion_inside_mod1.rs:7
