pub fn f() {
    return;
    println!("Paul is dead");
//  ^^^^^^^^^^^^^^^^^^^^^^^^^ERR unreachable statement
//  ^^^^^^^^^^^^^^^^^^^^^^^^^ERR this error originates in a macro outside of the current crate
//  ^^^^^^^^^^^^^^^^^^^^^^^^^MSG See Also: remote_note_1.rs:1
}
