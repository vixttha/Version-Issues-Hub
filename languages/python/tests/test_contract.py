import unittest


def debit(balance, amount):
    if amount < 0 or amount > balance:
        return balance
    return balance - amount


class DebitContract(unittest.TestCase):
    def test_rejected_debit_preserves_balance(self):
        self.assertEqual(debit(10, 11), 10)
        self.assertEqual(debit(10, -1), 10)
        self.assertEqual(debit(10, 10), 0)
