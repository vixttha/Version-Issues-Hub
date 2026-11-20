import java.nio.charset.StandardCharsets;
import java.util.Arrays;

class ContractCheck {
    public static void main(String[] args) {
        String original = "café";
        byte[] expected = {99, 97, 102, (byte) 0xc3, (byte) 0xa9};
        byte[] actual = original.getBytes(StandardCharsets.UTF_8);
        if (!Arrays.equals(expected, actual)
                || !original.equals(new String(actual, StandardCharsets.UTF_8))) {
            throw new AssertionError("UTF-8 round trip mismatch");
        }
    }
}
