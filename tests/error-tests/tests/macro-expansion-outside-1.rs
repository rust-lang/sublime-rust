#[macro_use]
extern crate dcrate;

// This is an example of an error in a macro from an external crate.  These
// messages do not have a file_name value, and thus will only be displayed in
// the console (when building).  On-save syntax highlighting will display them
// at the bottom of the "root" source file.

/*BEGIN*/example_bad_syntax!{}/*END*/
// ~ERR(>=1.20.0) /expected one of .*, found `:`/
// ~ERR(>=1.20.0) this error originates in a macro outside of the current crate
// ~ERR(>=1.20.0) /expected one of .* here/
// ~ERR(>=1.20.0,<1.24.0-nightly) unexpected token
// ~ERR(>=1.20.0) /expected one of .*, found `:`/
// ~ERR(>=1.20.0) expected one of
// end-msg: ERR(check,>=1.19.0,<1.20.0-beta) /expected one of .*, found `:`/
// end-msg: ERR(check,>=1.19.0,<1.20.0-beta) Errors occurred in macro <example_bad_syntax macros> from external crate
// end-msg: ERR(check,>=1.19.0,<1.20.0-beta) Macro text: (  ) => { enum E { Kind ( x : u32 ) } }
// end-msg: ERR(check,>=1.19.0,<1.20.0-beta) /expected one of .* here/
// end-msg: ERR(check,>=1.19.0,<1.20.0-beta) unexpected token
// end-msg: ERR(check,>=1.19.0,<1.20.0-beta) expected one of 7 possible tokens here
// end-msg: ERR(check,>=1.19.0,<1.20.0-beta) /expected one of .*, found `:`/
// end-msg: ERR(<1.19.0) /expected one of .*, found `:`/
// end-msg: ERR(<1.19.0) Errors occurred in macro <example_bad_syntax macros> from external crate
// end-msg: ERR(<1.19.0) Macro text: (  ) => { enum E { Kind ( x : u32 ) } }
// end-msg: ERR(>=1.18.0,<1.19.0) /expected one of .* here/
// end-msg: ERR(>=1.18.0,<1.19.0) unexpected token
// end-msg: ERR(<1.19.0) /expected one of .*, found `:`/
// end-msg: ERR(>=1.18.0,<1.19.0) expected one of 7 possible tokens here
