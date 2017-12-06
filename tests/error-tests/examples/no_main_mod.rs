/*BEGIN*/fn main() {
//       ^^^^^^^^^WARN(no-trans) function is never used
//       ^^^^^^^^^NOTE(no-trans) #[warn(dead_code)]
// 1.24 nightly has changed how these no-trans messages are displayed (instead
// of encompassing the entire function).
}/*END*/
// ~NOTE(check) here is a function named 'main'
