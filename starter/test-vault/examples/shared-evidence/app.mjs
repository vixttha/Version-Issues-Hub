const args = process.argv.slice(2);
if (args.length !== 2 || !args.every(value => /^[0-9]+$/.test(value))) {
  throw new Error('Expected exactly two nonnegative decimal integers');
}
const [unitCents, quantity] = args.map(Number);
const totalCents = unitCents * quantity;
if (![unitCents, quantity, totalCents].every(Number.isSafeInteger)) {
  throw new Error('Expected safe integer inputs and total');
}
console.log(JSON.stringify({ unit_cents: unitCents, quantity, total_cents: totalCents }));
