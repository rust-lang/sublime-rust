// start-msg: WARN(>=1.33.0-beta) crate `SNAKE` should have a snake case
// start-msg: NOTE(>=1.33.0-beta) #[warn(non_snake_case)]
// start-msg: HELP(>=1.33.0-beta) convert the identifier to snake case: `snake`
fn main() {
}
// end-msg: WARN(<1.33.0-beta) crate `SNAKE` should have a snake case
// end-msg: NOTE(>=1.17.0,<1.33.0-beta) #[warn(non_snake_case)] on by default
