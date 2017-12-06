fn main() {
    println!("altmain");
}

/*BEGIN*/fn warning_example() {
//       ^^^^^^^^^^^^^^^^^^^^WARN(>=1.22.0) function is never used
//       ^^^^^^^^^^^^^^^^^^^^NOTE(>=1.22.0) #[warn(dead_code)]
}/*END*/
// ~WARN(<1.22.0) function is never used
// ~NOTE(<1.22.0,>=1.17.0) #[warn(dead_code)]
