// 1.21 added new support for messages with multiple spans.
/*BEGIN*/fn foo(x: &mut Vec<&u32>, y: &u32) {
//                          ^^^^ERR(>=1.21.0)
//                                    ^^^^ERR(>=1.21.0) these two types
  x.push(y);
//       ^ERR(>=1.21.0) lifetime mismatch
//       ^ERR(>=1.21.0) ...but data from
//       ^ERR(<1.21.0) lifetime of reference outlives
}/*END*/
// ~NOTE(<1.21.0) ...the reference is valid
// ~NOTE(<1.21.0) ...but the borrowed content
