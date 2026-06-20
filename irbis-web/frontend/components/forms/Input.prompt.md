Текстовое поле с подписью, подсказкой/ошибкой, опц. иконкой слева и кнопкой очистки.

```jsx
<Input label="Заглавие" placeholder="например, Чайка" iconLeft="search" />
<Input label="Билет" required error="Билет не найден" />
<Input value={q} onChange={e=>setQ(e.target.value)} onClear={()=>setQ("")} />
```

`error` переводит в состояние ошибки и связывает aria-describedby. `onClear` показывает крестик при непустом значении.
