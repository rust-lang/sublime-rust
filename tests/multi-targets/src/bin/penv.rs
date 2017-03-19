fn main() {
    for (key, value) in std::env::vars() {
        println!("{}={}", key, value);
    }
}
