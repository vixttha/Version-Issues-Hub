#include <iostream>

bool within(int value, int low, int high) {
    return value >= low && value <= high;
}

int main() {
    if (!within(5, 5, 8) || !within(8, 5, 8) || within(4, 5, 8) || within(9, 5, 8)) {
        std::cerr << "Inclusive range mismatch\n";
        return 1;
    }
    return 0;
}
