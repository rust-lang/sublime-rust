#[cfg(test)]
mod tests {
    fn bad(a: DoesNotExist) {
//            ^^^^^^^^^^^^ERR(<1.16.0,rust_syntax_checking_include_tests=True) type name
//            ^^^^^^^^^^^^ERR(<1.16.0,rust_syntax_checking_include_tests=True) undefined or not in scope
//            ^^^^^^^^^^^^HELP(<1.16.0,rust_syntax_checking_include_tests=True) no candidates
//            ^^^^^^^^^^^^ERR(>=1.16.0,<1.19.0,rust_syntax_checking_include_tests=True,no-trans OR >=1.23.0,rust_syntax_checking_include_tests=True) cannot find type `DoesNotExist`
//            ^^^^^^^^^^^^ERR(>=1.16.0,<1.19.0,rust_syntax_checking_include_tests=True,no-trans OR >=1.23.0,rust_syntax_checking_include_tests=True) not found in this scope
    }

    #[test]
    fn it_works() {
        asdf
//      ^^^^ERR(<1.16.0,rust_syntax_checking_include_tests=True) unresolved name
//      ^^^^ERR(<1.16.0,rust_syntax_checking_include_tests=True) unresolved name
//      ^^^^ERR(>=1.16.0,<1.19.0,rust_syntax_checking_include_tests=True,no-trans OR >=1.23.0,rust_syntax_checking_include_tests=True) cannot find value
//      ^^^^ERR(>=1.16.0,<1.19.0,rust_syntax_checking_include_tests=True,no-trans OR >=1.23.0,rust_syntax_checking_include_tests=True) not found in this scope
    }
}
