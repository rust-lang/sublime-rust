trait Trait {}

// This triggers a warning about lifetimes with help.
fn f2</*WARN 2*/'a: 'static>(_: &'a i32) {}

pub fn f() {
    let x = Box::new(0u32);
    // This is an error with a note and help.
    let y: &Trait = /*ERR 1*/x;
}
