mod somemod;

trait Trait {}

pub fn f() {
    let x = Box::new(0u32);
    let y: &Trait = x;
                    // ^ERR expected &Trait, found box
                    // ^^ERR mismatched types
                    // ^^^NOTE expected type `&Trait`
                    // ^^^^NOTE found type `Box<u32>`
}
