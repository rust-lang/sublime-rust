mod error_across_mod_f;

fn test() {
    error_across_mod_f::f(1);
//                        ^ERR(<1.24.0-beta) this function takes 0 parameters but 1
//                        ^ERR(<1.24.0-beta) expected 0 parameters
//                        ^MSG(<1.24.0-beta) See Also: error_across_mod_f.rs:4
//  ^^^^^^^^^^^^^^^^^^^^^^^^ERR(>=1.24.0-beta) this function takes 0 parameters but 1
//  ^^^^^^^^^^^^^^^^^^^^^^^^ERR(>=1.24.0-beta) expected 0 parameters
//  ^^^^^^^^^^^^^^^^^^^^^^^^MSG(>=1.24.0-beta) See Also: error_across_mod_f.rs:1
}
