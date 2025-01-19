
def upbit_price_unit(item, price):
    if item in [
        'ADA', 'ALGO', 'BLUR', 'CELO', 'ELF', 'EOS', 'GRS', 'GRT',
        'ICX', 'MANA', 'MINA', 'POL', 'SAND', 'SEI', 'STG', 'TRX'
        ]:
        return 1
    '''
    https://docs.upbit.com/docs/krw-market-info
    '''
    if 0.0001 > price:
        return 0.00000001
    elif 0.001 > price:
        return 0.0000001
    elif 0.01 > price:
        return 0.000001
    elif 0.1 > price:
        return 0.00001
    elif 1 > price:
        return 0.0001
    elif 10 > price:
        return 0.001
    elif 100 > price:
        return 0.01
    elif 1000 > price:
        return 0.1
    elif 10000 > price:
        return 1
    elif 100000 > price:
        return 10
    elif 500000 > price:
        return 50
    elif 1000000 > price:
        return 100
    elif 2000000 > price:
        return 500
    return 1000