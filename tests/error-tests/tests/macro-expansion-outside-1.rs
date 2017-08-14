#[macro_use]
extern crate dcrate;

// This is an example of an error in a macro from an external crate.  These
// messages do not have a file_name value, and thus will only be displayed in
// the console.
example_bad_syntax!{}
// end-msg: ERR /expected one of .*, found `:`/
// end-msg: ERR Errors occurred in macro <example_bad_syntax macros> from external crate
// end-msg: ERR Macro text: (  ) => { enum E { Kind ( x : u32 ) } }
// end-msg: ERR /expected one of .* here/
// end-msg: ERR unexpected token
// end-msg: ERR expected one of
// end-msg: ERR expected one of 7 possible tokens here
