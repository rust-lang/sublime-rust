pub fn f() {
    return;
//  ^^^^^^ERR(>=1.39.0-beta) any code following
    println!("Paul is dead");
//  ^^^^^^^^^^^^^^^^^^^^^^^^^ERR unreachable statement
//  ^^^^^^^^^^^^^^^^^^^^^^^^^ERR this error originates in a macro outside of the current crate
//  ^^^^^^^^^^^^^^^^^^^^^^^^^MSG See Also: remote_note_1.rs:1
//  ^^^^^^^^^^^^^^^^^^^^^^^^^ERR(>=1.39.0-beta) unreachable statement
}
