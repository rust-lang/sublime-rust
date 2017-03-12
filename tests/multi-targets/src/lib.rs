pub mod lmod1;

pub fn libf1() {
    println!("libf1");
    // Testing a Clippy warning (char_lit_as_u8).
    'x' as u8;
}

fn unused() {
}
// ^WARN function is never used

