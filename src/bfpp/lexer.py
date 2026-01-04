import re


def preprocess(code: str) -> str:
    code = re.sub(r'//.*', '', code)
    code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)
    return code


def tokenize(line: str):
    tokens = []
    i = 0
    while i < len(line):
        if line[i].isspace():
            i += 1
            continue

        if line[i] == '"':
            j = i + 1
            while j < len(line) and line[j] != '"':
                j += 1
            tokens.append(line[i:j + 1])
            i = j + 1
        elif line[i:i + 2] in {"==", ">=", "<=", "!="}:
            tokens.append(line[i:i + 2])
            i += 2
        elif line[i] in '{}()[]<>,;=!&|~+-*/%':
            tokens.append(line[i])
            i += 1
        else:
            j = i
            while j < len(line) and not line[j].isspace() and line[j] not in '{}()[]<>,;=!&|~+-*/%':
                j += 1
            tokens.append(line[i:j])
            i = j

    return tokens
