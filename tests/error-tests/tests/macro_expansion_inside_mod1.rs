#[macro_export]
macro_rules! example_bad_syntax {
    () => {
        enum E {
            // This is somewhat of an odd example, since rustc gives two
            // syntax errors.
            Kind(x: u32)
//                ^ERR /expected one of .*, found `:`/
//                ^ERR(>=1.18.0) /expected one of .* here/
//                ^MSG(>=1.20.0) See Also: macro-expansion-inside-1.rs:6
//                ^ERR /expected one of .*, found `:`/
//                ^ERR(>=1.18.0) expected one of
//                ^MSG(>=1.20.0) See Also: macro-expansion-inside-1.rs:6
        }
    }
}
