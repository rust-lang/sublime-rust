// Tests for cycling through the errors from a test run.

#[test]
fn passing() {
}

#[test]
fn basic_error1() {
    /*ERR 1 "tests/test_test_output.rs:9:46"*/assert!(false);
}

#[test]
fn basic_error2() {
    /*ERR 2 "tests/test_test_output.rs:14:47"*/assert_eq!(1, 0);
}

#[test]
fn basic_error3() {
    /*ERR 3 "tests/test_test_output.rs:19:47"*/assert_ne!(1, 1);
}

#[test]
fn custom_message() {
    /*ERR 4 "tests/test_test_output.rs:24:47"*/assert!(false, "Custom message");
}

#[test]
fn manual_panic() {
    /*ERR 5 "tests/test_test_output.rs:29:47"*/panic!("manual panic");
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
