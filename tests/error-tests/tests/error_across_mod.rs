mod error_across_mod_f;

fn test() {
    error_across_mod_f::f(1);
//                        ^ERR this function takes 0 parameters but 1
//                        ^ERR expected 0 parameters
//                        ^MSG Note: error_across_mod_f.rs:1
}
