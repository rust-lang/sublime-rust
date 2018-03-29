#[macro_export]
macro_rules! example_bad_value {
    () => (1i32)
//         ^^^^ERR mismatched types
//         ^^^^ERR expected (), found i32
//         ^^^^NOTE expected type `()`
//         ^^^^NOTE(<1.16.0) found type `i32`
//         ^^^^MSG See Also: macro-expansion-inside-2.rs:7
}
