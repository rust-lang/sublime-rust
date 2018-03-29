// Copyright 2013 The Rust Project Developers. See the COPYRIGHT
// file at the top-level directory of this distribution and at
// http://rust-lang.org/COPYRIGHT.
//
// Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
// http://www.apache.org/licenses/LICENSE-2.0> or the MIT license
// <LICENSE-MIT or http://opensource.org/licenses/MIT>, at your
// option. This file may not be copied, modified, or distributed
// except according to those terms.

// This test exercises a message with multiple "far away" child messages.

trait Foo { fn method(&self) {} }
//          ^^^^^^^^^^^^^^^^^^^NOTE(<1.24.0) candidate #1
//          ^^^^^^^^^^^^^^^^^^^MSG(<1.24.0) See Primary: ↓:28
//          ^^^^^^^^^^^^^^^^NOTE(>=1.24.0) candidate #1
//          ^^^^^^^^^^^^^^^^MSG(>=1.24.0) See Primary: ↓:28
trait Bar { fn method(&self) {} }
//          ^^^^^^^^^^^^^^^^^^^NOTE(<1.24.0) candidate #2
//          ^^^^^^^^^^^^^^^^^^^MSG(<1.24.0) See Primary: ↓:28
//          ^^^^^^^^^^^^^^^^NOTE(>=1.24.0) candidate #2
//          ^^^^^^^^^^^^^^^^MSG(>=1.24.0) See Primary: ↓:28

impl Foo for usize {}
impl Bar for usize {}

fn main() {
    1_usize.method();
//          ^^^^^^ERR multiple applicable items
//          ^^^^^^ERR multiple `method` found
//          ^^^^^^MSG See Also: ↑:13
//          ^^^^^^MSG See Also: ↑:18
}
