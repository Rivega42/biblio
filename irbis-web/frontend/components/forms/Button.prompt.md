Кнопка действия. Главное действие — `primary` (одно на экран), вторичное — `secondary`, малозаметное — `ghost`, опасное/удаление — `danger`.

```jsx
<Button>Найти</Button>
<Button variant="secondary" iconLeft="rotate-ccw">Сброс</Button>
<Button iconLeft="bookmark" variant="ghost" size="sm">Отметить</Button>
<Button loading>Заказываю…</Button>
```

Размеры `sm | md | lg`. `iconLeft` / `iconRight` — имена иконок. `loading` блокирует и показывает спиннер. `block` растягивает на ширину контейнера.
