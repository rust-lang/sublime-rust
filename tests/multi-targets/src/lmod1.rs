pub fn fmod1() {
    println!("fmod1");
    d();
    // ^WARN deprecated
    // ^^NOTE(>=1.17.0) #[warn(deprecated)]
}

#[deprecated]
pub fn d() {
}
