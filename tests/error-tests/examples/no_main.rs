// Should display error about no main.

  mod no_main_mod;
//^^^^^^^^^^^^^^^^ERR(>=1.39.0-beta,rust_syntax_checking_include_tests=False) `main` function not found
//^^^^^^^^^^^^^^^^ERR(>=1.39.0-beta,rust_syntax_checking_include_tests=False) the main function must be defined
//^^^^^^^^^^^^^^^^NOTE(>=1.39.0-beta,rust_syntax_checking_include_tests=False) you have one or more functions named `main`
//^^^^^^^^^^^^^^^^HELP(>=1.39.0-beta,rust_syntax_checking_include_tests=False) either move the `main`
//^^^^^^^^^^^^^^^^MSG(>=1.39.0-beta,rust_syntax_checking_include_tests=False) See Also: no_main_mod.rs:4
// When --profile=test is used with `cargo check`, this error will not happen
// due to the synthesized main created by the test harness.
// end-msg: ERR(<1.39.0-beta,rust_syntax_checking_include_tests=False OR <1.23.0,rust_syntax_checking_include_tests=True) /`?main`? function not found/
// end-msg: NOTE(<1.39.0-beta,rust_syntax_checking_include_tests=False OR <1.23.0,rust_syntax_checking_include_tests=True) the main function must be defined
// end-msg: MSG(<1.39.0-beta,rust_syntax_checking_include_tests=False OR <1.23.0,rust_syntax_checking_include_tests=True) See Also: no_main_mod.rs:4
