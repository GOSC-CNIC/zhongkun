from decimal import Decimal, getcontext


def quantize(value: Decimal, max_digits, decimal_places):
    context = getcontext().copy()
    context.prec = max_digits
    return value.quantize(
        Decimal('.1') ** decimal_places,
        context=context
    )


def quantize_10_2(value: Decimal):
    return quantize(value=value, max_digits=10, decimal_places=2)


def quantize_12_4(value: Decimal):
    return quantize(value=value, max_digits=12, decimal_places=4)


def quantize_18_2(value: Decimal):
    return quantize(value=value, max_digits=18, decimal_places=2)
