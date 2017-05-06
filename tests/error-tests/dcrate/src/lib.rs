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
