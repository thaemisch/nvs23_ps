import random
import string

def generate_random_string(length):
    letters = string.ascii_letters + string.digits + string.punctuation
    return ''.join(random.choice(letters) for _ in range(length))

def create_random_file(file_path, size):
    size_in_bytes = convert_size_to_bytes(size)
    with open(file_path, 'w') as file:
        remaining_size = size_in_bytes
        while remaining_size > 0:
            chunk_size = min(remaining_size, 1024)
            random_string = generate_random_string(chunk_size)
            file.write(random_string)
            remaining_size -= chunk_size

def convert_size_to_bytes(size):
    size = size.upper()
    if size.endswith("KB"):
        return int(size[:-2]) * 1000
    elif size.endswith("MB"):
        return int(size[:-2]) * 1000 * 1000
    elif size.endswith("GB"):
        return int(size[:-2]) * 1000 * 1000 * 1000
    elif size.endswith("TB"):
        return int(size[:-2]) * 1000 * 1000 * 1000 * 1000
    elif size.endswith("B"):
        return int(size[:-1])
    else:
        raise ValueError("Invalid size format. Please provide a size in bytes (B), kilobytes (KB), megabytes (MB), gigabytes (GB), or terabytes (TB).")


if __name__ == '__main__':
    create_random_file('test.txt', 0.88)