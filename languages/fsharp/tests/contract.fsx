let applyEvent completed identifier =
    Set.add identifier completed

let once = applyEvent Set.empty "one"
let replayed = applyEvent once "one"
let two = applyEvent replayed "two"

if Set.count replayed <> 1 || Set.count two <> 2 then
    failwith "Completion replay changed the state incorrectly"
