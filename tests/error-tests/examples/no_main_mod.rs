/*BEGIN*/fn main() {
//       ^^^^^^^^^WARN(rust_syntax_checking_include_tests=True) function is never used
//       ^^^^^^^^^NOTE(rust_syntax_checking_include_tests=True) #[warn(dead_code)]
// 1.24 nightly has changed how these no-trans messages are displayed (instead
// of encompassing the entire function).
}/*END*/
// ~NOTE(rust_syntax_checking_include_tests=False) here is a function named 'main'
