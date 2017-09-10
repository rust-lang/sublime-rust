trait Trait {}

// This triggers a warning about lifetimes with help.
fn f2</*WARN 2,1 "tests/test_all_levels.rs:4" " --> tests/test_all_levels.rs:4:85"*/'a: 'static>(_: &'a i32) {}

pub fn f() {
    let x = Box::new(0u32);
    // This is an error with a note and help.
    let y: &Trait = /*ERR 1,2 "tests/test_all_levels.rs:9" " --> tests/test_all_levels.rs:9:98"*/x;
}
