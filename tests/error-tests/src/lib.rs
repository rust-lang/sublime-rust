#[cfg(test)]
mod tests {
    fn bad(a: DoesNotExist) {
              // ^ERR undefined or not in scope
              // ^^ERR type name
              // ^^^HELP no candidates
    }

    #[test]
    fn it_works() {
        asdf
        // ^ERR unresolved name
        // ^^ERR unresolved name
    }
}
