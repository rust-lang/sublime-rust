/*BEGIN*/fn main() {
//       ^^^^^^^^^WARN(>=1.23.0,rust_syntax_checking_include_tests=True) function is never used
//       ^^^^^^^^^NOTE(>=1.23.0,rust_syntax_checking_include_tests=True) #[warn(dead_code)]
}/*END*/
// ~NOTE(rust_syntax_checking_include_tests=False OR <1.23.0,rust_syntax_checking_include_tests=True) here is a function named
// ~MSG(rust_syntax_checking_include_tests=False OR <1.23.0,rust_syntax_checking_include_tests=True) See Primary: no_main.rs
