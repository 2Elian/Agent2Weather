import os

def count_lines_in_file(file_path: str) -> int:
    """
    Count the number of non-empty lines in a file.
    """
    count = 0
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():  # 非空行
                count += 1
    return count

def count_lines_in_directory(directory: str) -> int:
    """
    Recursively count lines in all .py files under the directory.
    """
    total_lines = 0
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                lines = count_lines_in_file(file_path)
                total_lines += lines
                print(f"{file_path}: {lines} lines")
    return total_lines

if __name__ == "__main__":
    directory_to_scan = r"G:\项目成果打包\气象局服务材料写作系统\宜春\RAG\Weather-Agent-YiChun"
    total = count_lines_in_directory(directory_to_scan)
    print(f"Total lines in all .py files: {total}")
