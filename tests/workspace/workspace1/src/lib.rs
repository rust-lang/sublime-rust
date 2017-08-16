mod anothermod;

/*BEGIN*/struct S {
//       ^^^^^^^^ERR(>=1.18.0) recursive type has infinite size
//       ^^^^^^^^ERR(>=1.18.0) recursive type `S` has infinite size
//       ^^^^^^^^HELP(>=1.18.0) insert indirection
    recursive: S
//  ^^^^^^^^^^^^ERR(>=1.19.0) recursive without indirection
}/*END*/
// ~ERR(<1.18.0) recursive type has infinite size
// ~ERR(<1.18.0) recursive type `S` has infinite size
// ~HELP(<1.18.0) insert indirection
