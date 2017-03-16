#![feature(test)]

extern crate test;

use test::Bencher;

#[bench]
fn example2(b: &mut Bencher) {
    b.iter(|| 1);
}
