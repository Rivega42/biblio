Модуль «Поисковые режимы» (§1.10) — выбранный режим выделяется цветом. Состав режимов берётся из конфига базы (`db.modes`).

```jsx
<SearchModes
  modes={db.modes}            // ["simple","advanced","complex"] или ["simple","special"]
  value={mode} onChange={setMode}
  labels={{ special: db.specialTitle }}
/>
```
