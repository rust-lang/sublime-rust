/*BEGIN*/fn main() {
//       ^^^^^^^^^WARN(>=1.23.0,rust_syntax_checking_include_tests=True) function is never used
//       ^^^^^^^^^NOTE(>=1.23.0,rust_syntax_checking_include_tests=True) #[warn(dead_code)]
}/*END*/
// ~NOTE(rust_syntax_checking_include_tests=False OR <1.23.0,rust_syntax_checking_include_tests=True,check) here is a function named 'main'
// ~MSG(rust_syntax_checking_include_tests=False OR <1.23.0,rust_syntax_checking_include_tests=True,check) See Primary: no_main.rs
// ~WARN(<1.19.0,no-trans,rust_syntax_checking_include_tests=True) function is never used
// ~NOTE(>=1.17.0,<1.19.0,no-trans,rust_syntax_checking_include_tests=True) #[warn(dead_code)]
