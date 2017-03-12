use std::thread;
use std::time::Duration;
use std::fs;

fn touch(name: &str) {
    let ents = fs::read_dir(".").unwrap();
    let nums = ents.filter_map(|e| {
        let ent_name = e.unwrap().file_name().into_string().unwrap();
        if ent_name.starts_with(name) {
            Some(ent_name[name.len()..].parse::<u32>().unwrap())
        } else {
            None
        }
    });
    let max = nums.max().unwrap_or(0);
    let fname = format!("{}{}", name, max+1);
    fs::File::create(fname).unwrap();
}

fn main() {
    touch("test-build-start-");
    thread::sleep(Duration::from_secs(3));
    touch("test-build-end-");
}
