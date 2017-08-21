#[macro_export]
macro_rules! example_bad_value {
    () => (1i32)
//         ^^^^ERR mismatched types
//         ^^^^ERR expected (), found i32
//         ^^^^NOTE expected type `()`
//         ^^^^MSG macro-expansion-inside-2.rs:7
}
