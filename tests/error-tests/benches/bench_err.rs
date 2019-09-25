// Can't have a regular bench because [feature(test)] is restricted
// to nightly.

   #[asdf]
// ^^^^^^^ERR(<1.30.0-beta) The attribute `asdf` is currently unknown
//   ^^^^ERR(>=1.30.0-beta,<1.38.0-beta) The attribute `asdf` is currently unknown
//   ^^^^NOTE(>=1.36.0-beta,<1.38.0-beta) for more information
//   ^^^^ERR(>=1.38.0-beta) cannot find attribute
fn f() {}
