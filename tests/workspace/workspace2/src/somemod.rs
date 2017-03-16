fn f() {
    someerr
    // ^ERR(<1.16.0) unresolved name
    // ^^ERR(<1.16.0) unresolved name `someerr`
    // ^^^ERR(>=1.16.0) not found in this scope
    // ^^^^ERR(>=1.16.0) cannot find value
}

