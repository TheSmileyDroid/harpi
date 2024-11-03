from src.HarpiLib.dice import dice_parser


def test_parse_dice():
    parser = dice_parser.DiceParser("1d20+3d6-2d4+5-2d5")

    text = ""

    print("Roll breakdown:")
    for sign, component in parser.components:
        roll = component.roll()
        text += f"{sign}{component}: {roll}"

    print(text)
    assert True
