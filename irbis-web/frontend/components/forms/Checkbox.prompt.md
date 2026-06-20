Флажок с подписью; поддерживает промежуточное состояние для «выбрать все».

```jsx
<Checkbox label="Отметить запись" checked={on} onChange={e=>setOn(e.target.checked)} />
<Checkbox label="Все на странице" indeterminate={some} checked={all} />
```
