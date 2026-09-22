from pdo.rego.utils import AsymmetricEncryption
import sys


def read_data(input_data_file, private_key_file, out_data):
    with open(input_data_file, "rb") as f:
        encrypted_data = f.read()

    with open(private_key_file, "rb") as f:
        private_key = f.read()

    data = AsymmetricEncryption().decrypt(private_key, encrypted_data)

    with open(out_data, "wb") as f:
        f.write(data)


if __name__ == "__main__":
    input_data_file = sys.argv[1]
    private_key_file = sys.argv[2]
    out_data = sys.argv[3]

    read_data(input_data_file, private_key_file, out_data)
