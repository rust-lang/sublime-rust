mod somemod;

trait Trait {}

pub fn f() {
    let x = Box::new(0u32);
    let y: &Trait = x;
//                  ^ERR expected &Trait, found
//                  ^ERR mismatched types
//                  ^NOTE expected type `&Trait`
//                  ^NOTE(<1.16.0) found type
//                  ^HELP(>=1.18.0,<1.24.0-nightly) try with `&x`
//                  ^HELP(>=1.24.0-nightly) consider borrowing here
//                  ^HELP(>=1.24.0-nightly) &x
}
