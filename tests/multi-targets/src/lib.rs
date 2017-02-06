pub mod lmod1;

pub fn libf1() {
    println!("libf1");
}

fn unused() {
}
// ^WARN function is never used

#[cfg(test)]
mod tests {
    #[test]
    fn it_works() {
    }
}
