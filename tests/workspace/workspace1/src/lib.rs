mod anothermod;

/*BEGIN*/struct S {
    recursive: S
}/*END*/
// ~ERR recursive type has infinite size
// ~ERR recursive type
// ~HELP insert indirection
