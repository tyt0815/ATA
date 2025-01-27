def format_float(value, n):
    result = str(value)[:n]
    if result[-1] == '.':  # 소수점만 남는 경우 제거
        result = result[:-1]
    return float(result)