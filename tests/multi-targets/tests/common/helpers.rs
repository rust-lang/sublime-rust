// Example of a module shared among test code.

pub fn helper() {

}
// ^WARN function is never used
// ^^NOTE(>=1.17.0) #[warn(dead_code)]

pub fn unused() {

}
// ^WARN function is never used
// ^^NOTE(>=1.17.0) #[warn(dead_code)]
