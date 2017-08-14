pub fn f() {
    return;
    println!("Paul is dead");
//  ^^^^^^^^^^^^^^^^^^^^^^^^^ERR /unreachable statement.*Note: remote_note_1.rs:1/
//  ^^^^^^^^^^^^^^^^^^^^^^^^^ERR this error originates in a macro outside of the current crate
}
