#[cfg(test)]
mod tests {
    fn bad(a: DoesNotExist) {
//            ^^^^^^^^^^^^ERR(<1.16.0) undefined or not in scope
//            ^^^^^^^^^^^^ERR(<1.16.0) type name
//            ^^^^^^^^^^^^HELP(<1.16.0) no candidates
//            ^^^^^^^^^^^^ERR(>=1.16.0,rust_syntax_checking_include_tests=True) not found in this scope
//            ^^^^^^^^^^^^ERR(>=1.16.0,rust_syntax_checking_include_tests=True) cannot find type `DoesNotExist`
    }

    #[test]
    fn it_works() {
        asdf
//      ^^^^ERR(<1.16.0) unresolved name
//      ^^^^ERR(<1.16.0) unresolved name
//      ^^^^ERR(>=1.16.0,rust_syntax_checking_include_tests=True) not found in this scope
//      ^^^^ERR(>=1.16.0,rust_syntax_checking_include_tests=True) cannot find value
    }
}
