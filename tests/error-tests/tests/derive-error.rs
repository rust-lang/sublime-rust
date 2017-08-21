// This verifies that "in this macro invocation" is not displayed for attributes.

#[derive(Default)]
//       ^^^^^^^ERR `Default` cannot be derived for enums, only structs
enum E {}

