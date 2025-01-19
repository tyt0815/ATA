
def upbit_price_unit(item, price):
    excepted_items = ['ADA', 'ALGO', 'BLUR', 'CELO', 'ELF', 'EOS', 'GRS', 'GRT', 'ICX', 'MANA', 'MINA', 'POL', 'SAND', 'SEI', 'STG', 'TRX']
    if item in excepted_items:
        return 1
    d = 1
    while 0.0001 * d <= 100000:
        if price < 0.0001 * d:
            return 0.00000001 * d
        d *= 10
    if price < 500000:
        return 50
    elif price < 1000000:
        return 100
    elif price < 2000000:
        return 500
    return 1000