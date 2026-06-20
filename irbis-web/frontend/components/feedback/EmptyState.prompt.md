Единый паттерн состояний пусто / ошибка / нет прав.

```jsx
<EmptyState title="Ничего не найдено" description="По запросу «…» записей нет."
  hints={["Уберите часть условий","Включите усечение","Проверьте раскладку"]}
  action={<Button variant="secondary" iconLeft="rotate-ccw">Сбросить</Button>} />
<EmptyState variant="locked" title="Требуется вход" description="Войдите по номеру билета." />
<EmptyState variant="error" title="Каталог недоступен" description="Узел временно не отвечает." />
```
