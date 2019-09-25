// Testing a Clippy warning (char_lit_as_u8).

pub fn clippy_example() {
    println!("libf1");
    'x' as u8;
//  ^^^^^^^^^WARN character literal
//  ^^^^^^^^^NOTE char_lit_as_u8
//  ^^^^^^^^^NOTE(>=1.39.0-beta) `char` is four bytes
//  ^^^^^^^^^HELP(<1.39.0-beta) Consider using a byte
//  ^^^^^^^^^HELP(>=1.39.0-beta) use a byte literal
//  ^^^^^^^^^HELP for further information
//  ^^^^^^^^^HELP(>=1.39.0-beta) /Accept Replacement:.*b'x'/
//  ^^^^^^^^^^WARN statement with no effect
//  ^^^^^^^^^^NOTE no_effect
//  ^^^^^^^^^^HELP for further information
}
