// Copyright 2017 The Rust Project Developers. See the COPYRIGHT
// file at the top-level directory of this distribution and at
// http://rust-lang.org/COPYRIGHT.
//
// Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
// http://www.apache.org/licenses/LICENSE-2.0> or the MIT license
// <LICENSE-MIT or http://opensource.org/licenses/MIT>, at your
// option. This file may not be copied, modified, or distributed
// except according to those terms.

use std::fmt::Debug;

trait Foo {
    fn foo(&self, _: &impl Debug);
//                    ^^^^^^^^^^ERR(>=1.28.0-beta) declaration in trait here
//                    ^^^^^^^^^^ERR(<1.28.0-beta) annotation in trait
//                    ^^^^^^^^^^MSG See Primary: ↓:21
}

impl Foo for () {
    fn foo<U: Debug>(&self, _: &U) { }
//         ^ERR method `foo` has incompatible signature
//         ^ERR(>=1.28.0-beta) expected `impl Trait`, found generic parameter
//         ^ERR(<1.28.0-beta) annotation in impl
//         ^MSG See Also: ↑:14
//        ^^^^^^^^^^HELP(>=1.28.0-beta) try removing the generic parameter
//        ^^^^^^^^^^HELP(>=1.28.0-beta) /Accept Replacement:</a> </div>/
//                              ^HELP(>=1.28.0-beta) try removing the generic parameter
//                              ^HELP(>=1.28.0-beta) /Accept Replacement:.*impl Debug/
}

trait Bar {
    fn bar<U: Debug>(&self, _: &U);
//         ^ERR(>=1.28.0-beta) declaration in trait here
//         ^ERR(<1.28.0-beta) annotation in trait
//         ^MSG See Primary: ↓:40
}

impl Bar for () {
    fn bar(&self, _: &impl Debug) { }
//                    ^^^^^^^^^^ERR method `bar` has incompatible signature
//                    ^^^^^^^^^^ERR(>=1.28.0-beta) expected generic parameter
//                    ^^^^^^^^^^HELP(>=1.28.0-beta) try changing the `impl Trait` argument
//                    ^^^^^^^^^^ERR(<1.28.0-beta) annotation in impl
//                    ^^^^^^^^^^MSG See Also: ↑:33
//        |HELP(>=1.28.0-beta) try changing the `impl Trait` argument
//        |HELP(>=1.28.0-beta) /Accept Replacement:.*<U: Debug>/
//                    ^^^^^^^^^^HELP(>=1.28.0-beta) /Accept Replacement:.*U</div>/
}

// With non-local trait (#49841):

use std::hash::{Hash, Hasher};

struct X;

impl Hash for X {
    fn hash(&self, hasher: &mut impl Hasher) {}
//                              ^^^^^^^^^^^ERR method `hash` has incompatible signature
//                              ^^^^^^^^^^^ERR(>=1.28.0-beta) expected generic parameter
//                              ^^^^^^^^^^^ERR(<1.28.0-beta) annotation in impl
}
