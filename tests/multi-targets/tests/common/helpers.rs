// Example of a module shared among test code.

/*BEGIN*/pub fn helper() {
//       ^^^^^^^^^^^^^^^WARN(>=1.22.0) function is never used
//       ^^^^^^^^^^^^^^^NOTE(>=1.22.0) #[warn(dead_code)]
}/*END*/
// ~WARN(<1.22.0) function is never used
// ~NOTE(<1.22.0,>=1.17.0) #[warn(dead_code)]

/*BEGIN*/pub fn unused() {
//       ^^^^^^^^^^^^^^^WARN(>=1.22.0) function is never used
//       ^^^^^^^^^^^^^^^NOTE(<1.24.0-beta) #[warn(dead_code)]
}/*END*/
// ~WARN(<1.22.0) function is never used
// ~NOTE(<1.22.0,>=1.17.0) #[warn(dead_code)]
