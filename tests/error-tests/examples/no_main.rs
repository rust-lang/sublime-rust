// Should display error about no main.

mod no_main_mod;
// Not sure why no-trans doesn't handle this properly.
// end-msg: ERR(check) main function not found
// end-msg: NOTE(check) the main function must be defined
// end-msg: MSG(check) Note: no_main_mod.rs:1
