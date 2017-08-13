// Should display error about no main.

mod no_main_mod;
// Not sure why no-trans doesn't handle this properly.
// end-msg: ERR(!no-trans) /main function not found.*Note: no_main_mod.rs:1/
// end-msg: NOTE(!no-trans) the main function must be defined
