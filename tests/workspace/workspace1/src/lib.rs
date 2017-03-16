mod anothermod;

struct S {
    recursive: S
}
// ^ERR recursive type has infinite size
// ^^ERR recursive type
// ^^^HELP insert indirection
