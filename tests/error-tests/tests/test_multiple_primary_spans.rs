// This test is for a message with multiple primary spans
// (both spans have no label).

#[repr(C, u64)]
//     ^WARN conflicting representation hints
//        ^^^WARN conflicting representation hints
pub enum C { C }
