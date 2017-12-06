// Can't have a regular bench because [feature(test)] is restricted
// to nightly.

   #[asdf]
// ^^^^^^^ERR The attribute `asdf` is currently unknown
// ^^^^^^^HELP(nightly) add #![feature(custom_attribute)]
fn f() {}
