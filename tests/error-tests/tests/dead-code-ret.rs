// Copyright 2014 The Rust Project Developers. See the COPYRIGHT
// file at the top-level directory of this distribution and at
// http://rust-lang.org/COPYRIGHT.
//
// Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
// http://www.apache.org/licenses/LICENSE-2.0> or the MIT license
// <LICENSE-MIT or http://opensource.org/licenses/MIT>, at your
// option. This file may not be copied, modified, or distributed
// except according to those terms.

// error-pattern: unreachable statement

#![deny(unreachable_code)]
//      ^^^^^^^^^^^^^^^^NOTE lint level defined here
//      ^^^^^^^^^^^^^^^^MSG See Primary: ↓:20

fn main() {
    return;
//  ^^^^^^ERR(>=1.39.0-beta) any code following
    println!("Paul is dead");
//  ^^^^^^^^^^^^^^^^^^^^^^^^^ERR unreachable statement
//  ^^^^^^^^^^^^^^^^^^^^^^^^^ERR this error originates in a macro outside of the current crate
//  ^^^^^^^^^^^^^^^^^^^^^^^^^ERR(>=1.39.0-beta) unreachable statement
//  ^^^^^^^^^^^^^^^^^^^^^^^^^MSG See Also: ↑:13

}

// This is a test of macro expansion, should print error on println!
// Also, note on the lint level above.
