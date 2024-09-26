from src.cogs import dice


def test_parse_dice():
    parser = dice.DiceParser("1d20+3d6-2d4+5-2d5")

    text = ""

    print("Roll breakdown:")
    for sign, component in parser.components:
        roll = component.roll()
        text += f"{sign}{component}: {roll}"

    print(text)
    assert True
