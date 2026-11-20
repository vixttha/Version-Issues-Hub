fn payload(input: &[u8]) -> Option<&[u8]> {
    let (length, bytes) = input.split_first()?;
    (usize::from(*length) == bytes.len()).then_some(bytes)
}

#[test]
fn rejects_truncated_payload() {
    assert_eq!(payload(&[2, 8, 9]), Some(&[8, 9][..]));
    assert_eq!(payload(&[2, 8]), None);
    assert_eq!(payload(&[]), None);
}
