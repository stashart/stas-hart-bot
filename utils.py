def append_to_file(path, text):
    with open(path, "a", encoding="utf-8") as f:
        f.write(text.strip() + "\n")
