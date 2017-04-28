pub mod lmod1;

pub fn libf1() {
    println!("libf1");
}

fn unused() {
}
// ^WARN function is never used
// ^^NOTE(>=1.17.0) #[warn(dead_code)]
