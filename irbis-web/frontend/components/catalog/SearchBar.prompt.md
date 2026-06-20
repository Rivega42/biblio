Поисковая строка простого режима: поле + автокомплит словаря + «Найти», опц. ссылка на расширенный поиск.

```jsx
<SearchBar
  value={q} onChange={setQ} onSearch={runSearch}
  suggestions={[{term:"Чайка", count:42}, {term:"Чехов", count:318}]}
  onAdvanced={()=>goAdvanced()}
/>
```

Клавиатура: ↑/↓ — по подсказкам, Enter — поиск или выбор подсказки.
