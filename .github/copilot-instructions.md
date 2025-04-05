# GitHub Copilot Instructions
## Python
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
Use asserts para verificar condições e tipos.

## Typescript
Para TypeScript, siga as melhores práticas de tipagem. Utilize interfaces e tipos para definir estruturas de dados. Mantenha o código modular e reutilizável. Use async/await para operações assíncronas. Use assertions para verificar tipos e condições. Utilize o padrão de projeto "Module" para organizar o código.

```typescript
interface User {
    id: number;
    name: string;
    email?: string;
}

function getUser(userId: number): Promise<User> {
    return fetch(`/api/users/${userId}`)
        .then(response => response.json())
        .then(data => {
            const user = data as User;
            if (!user.id) {
                throw new Error('User not found');
            }
            return user;
        });
}
```

Gere a api de forma automática com OpenAPI, o comando está no package.json. Utilize o ESLint para linting e Prettier para formatação.

Use default arguments instead of short circuiting or conditionals. Default arguments are often cleaner than short circuiting.

**Bad:**

```ts
function loadPages(count?: number) {
  const loadCount = count !== undefined ? count : 10;
  // ...
}
```

**Good:**

```ts
function loadPages(count: number = 10) {
  // ...
}
```
