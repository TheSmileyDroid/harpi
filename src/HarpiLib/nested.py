def get_nested_attr(
    obj: object,
    attr_chain: str,
    default: object = None,
) -> object:
    """Acessa atributos aninhados de forma segura.

    Args:
        obj: O objeto inicial.
        attr_chain (str): Uma string com os nomes dos
            atributos separados por pontos.
        default: Valor a ser retornado se algum
            atributo for None ou não existir.

    Returns:
        O valor do atributo aninhado ou o valor padrão.
    """
    try:
        for attr in attr_chain.split("."):
            obj = getattr(obj, attr)
            if obj is None:
                return default
        return obj
    except AttributeError:
        return default
