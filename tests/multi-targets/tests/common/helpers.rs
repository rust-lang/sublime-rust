// Example of a module shared among test code.

/*BEGIN*/pub fn helper() {

}/*END*/
// ~WARN function is never used
// ~NOTE(>=1.17.0) #[warn(dead_code)]

/*BEGIN*/pub fn unused() {

}/*END*/
// ~WARN function is never used
// ~NOTE(>=1.17.0) #[warn(dead_code)]
