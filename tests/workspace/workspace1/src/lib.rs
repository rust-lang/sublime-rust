mod anothermod;

/*BEGIN*/struct S {
//       ^^^^^^^^ERR(>=1.18.0) recursive type has infinite size
//       ^^^^^^^^ERR(>=1.18.0) recursive type `S` has infinite size
//       ^^^^^^^^HELP(>=1.18.0) insert indirection
    recursive: S
}/*END*/
// ~ERR(<1.18.0) recursive type has infinite size
// ~ERR(<1.18.0) recursive type `S` has infinite size
// ~HELP(<1.18.0) insert indirection
