#[macro_export]
macro_rules! example_bad_syntax {
    () => {
        enum E {
            Kind(x: u32)
//                ^ERR /expected one of .*, found `:`/
//                ^ERR(>=1.18.0) /expected one of .* here/
//                ^MSG(>=1.20.0-beta) Note: macro-expansion-inside-1.rs:6
//                ^ERR /expected one of .*, found `:`/
//                ^ERR(>=1.18.0) expected one of 7 possible tokens here
        }
    }
}
