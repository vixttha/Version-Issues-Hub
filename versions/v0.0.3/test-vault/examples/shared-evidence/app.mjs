const [unitCents, quantity] = process.argv.slice(2).map(Number);
if (![unitCents, quantity, unitCents * quantity].every(value => Number.isSafeInteger(value) && value >= 0)) {
  throw new Error('Expected nonnegative, safe integer inputs and total');
}
console.log(JSON.stringify({ unit_cents: unitCents, quantity, total_cents: unitCents * quantity }));
