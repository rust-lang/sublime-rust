// Tests for cycling through the errors from a test run.

#[test]
fn passing() {
}

#[test]
fn basic_error1() {
    // . is used for the column because Rust 1.24 changed the column indexing
    // to be 1-based.
    /*ERR 1 "tests/test_test_output.rs:11:4."*/assert!(false);
}

#[test]
fn basic_error2() {
    /*ERR 2 "tests/test_test_output.rs:16:4."*/assert_eq!(1, 0);
}

#[test]
fn basic_error3() {
    /*ERR 3 "tests/test_test_output.rs:21:4."*/assert_ne!(1, 1);
}

#[test]
fn custom_message() {
    /*ERR 4 "tests/test_test_output.rs:26:4."*/assert!(false, "Custom message");
}

#[test]
fn manual_panic() {
    /*ERR 5 "tests/test_test_output.rs:31:4."*/panic!("manual panic");
}

#[test]
#[should_panic(expected="xyz")]
fn expected_panic1() {
    panic!("xyz");
}

#[test]
#[should_panic(expected="xyz")]
fn expected_panic2() {
}

#[test]
#[ignore]
fn ignored_test() {
    panic!("ignored");
}

#[test]
#[ignore]
fn slow() {
    // This just prints a simple warning.
    std::thread::sleep(std::time::Duration::from_secs(65));
}

#[test]
fn panic_outside_crate() {
    // This (unfortunately) should not show up as an error when running tests
    // since Rust prints the path to src/libcore/result.rs.
    Err::<i32, &str>("err").unwrap();
}
