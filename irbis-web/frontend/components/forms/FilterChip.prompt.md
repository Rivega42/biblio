Чип-фильтр в двух режимах.

```jsx
// Активный фильтр (снимаемый)
<FilterChip group="Язык" label="русский" onRemove={()=>drop("lang")} />
// Выбор фильтра / словарный термин (переключатель со счётчиком)
<FilterChip label="Книга" count={128} pressed={on} onToggle={()=>toggle()} />
```

`onRemove` → крестик; `onToggle`+`pressed` → кнопка-переключатель. `plain` — нейтральный серый вид.
