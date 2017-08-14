#[macro_export]
macro_rules! example {
    ($submac:ident!( $($args:tt)* )) => (
        $submac!($($args)*)
    )
}

#[macro_export]
macro_rules! inner {
    ($x:expr) => ($x.missing())
}

#[macro_export]
macro_rules! example_bad_syntax {
    () => {
        enum E {
            Kind(x: u32)
        }
    }
}

#[macro_export]
macro_rules! example_bad_value {
    () => (1i32)
}
