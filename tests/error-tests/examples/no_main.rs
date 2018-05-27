// Should display error about no main.

mod no_main_mod;
// When --profile=test is used with `cargo check`, this error will not happen
// due to the synthesized main created by the test harness.
// end-msg: ERR(rust_syntax_checking_include_tests=False OR <1.23.0,rust_syntax_checking_include_tests=True) /`?main`? function not found/
// end-msg: NOTE(rust_syntax_checking_include_tests=False OR <1.23.0,rust_syntax_checking_include_tests=True) the main function must be defined
// end-msg: MSG(rust_syntax_checking_include_tests=False OR <1.23.0,rust_syntax_checking_include_tests=True) See Also: no_main_mod.rs:4
