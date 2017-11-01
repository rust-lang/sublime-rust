// Tests for "test here" command.

  #[test]
fn test1() {

}

# [ test ] //comment

#[should_panic(expected="xyz")] /* comment */

pub fn expected_panic1() {
    panic!("xyz");
}

#[test]
fn test2() {
    fn inner() {

    }
    inner();
}#[test]
fn test3() {

}

// #[test]
// fn test4() {
// }

/*#[test]
fn test5() {
}
*/

#[test] fn test6() {

}
