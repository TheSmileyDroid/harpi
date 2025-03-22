Siga o PEP 8 para estilo de código. Utilize PEP 484 para anotações de tipo. Mantenha classes e funções com responsabilidades únicas. Documente todo código público utilizando docstrings.

```python
def calculate_total(items: list[float], tax_rate: float) -> float:
    """Calculate the total price including tax."""
    subtotal = sum(items)
    return subtotal * (1 + tax_rate)
```

```python
from typing import Dict, List, Optional, Union, TypedDict, Callable

def find_user(user_id: int) -> Optional[dict]:
    ...

def process_input(value: str) -> Union[int, float, str]:
    ...

class UserData(TypedDict):
    id: int
    name: str
    email: Optional[str]
```

Implemente testes unitários com pytest. Configure hooks de pré-commit para linting e formatação.  Utilize dataclasses para dados estruturados. Prefira exceções explícitas sobre retornos de erro. Implemente logging consistente.
Use os principio de Código Limpo: nomes significativos, funções curtas, evite duplicação, Comente apenas o necessário. Use injeção de dependência para facilitar testes e manutenção.
