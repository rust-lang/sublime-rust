// Tests for "bench here" commands.

#![feature(test)]

extern crate test;

use test::Bencher;

  #[bench] // comment
fn bench1(b: &mut Bencher) {
    b.iter(|| 1);
}

#[bench]
fn bench2(b: &mut Bencher) {
    b.iter(|| 2);
}
