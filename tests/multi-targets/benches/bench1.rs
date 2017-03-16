#![feature(test)]

extern crate test;

use test::Bencher;

#[bench]
fn example1(b: &mut Bencher) {
    b.iter(|| 1);
}
