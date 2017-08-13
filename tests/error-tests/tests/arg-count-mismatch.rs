// Copyright 2012 The Rust Project Developers. See the COPYRIGHT
// file at the top-level directory of this distribution and at
// http://rust-lang.org/COPYRIGHT.
//
// Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
// http://www.apache.org/licenses/LICENSE-2.0> or the MIT license
// <LICENSE-MIT or http://opensource.org/licenses/MIT>, at your
// option. This file may not be copied, modified, or distributed
// except according to those terms.

// error-pattern: parameters were supplied

/*BEGIN*/fn f(x: isize) {
}/*END*/
// ~ERR defined here

// children without spans, spans with no labels
// Should display error (with link) and a note of expected type.
fn main() { let i: (); i = f(); }
//                         ^^^ERR /this function takes 1 parameter.*Note: ↑:13/
//                         ^^^ERR expected 1 parameter
