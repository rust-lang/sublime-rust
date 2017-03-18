fn main() {
    print!("feats: ");
    let mut v = Vec::new();
    if cfg!(feature="feat1") {
        v.push("feat1");
    }
    if cfg!(feature="feat2") {
        v.push("feat2")
    }
    if cfg!(feature="feat3") {
        v.push("feat3")
    }
    println!("{}", v.join(" "));
}
