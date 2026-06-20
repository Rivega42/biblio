Выпадающий список (нативный select в стилизованной обёртке).

```jsx
<Select label="Сортировка" options={["По релевантности","По году ↓","По году ↑","По автору"]} />
<Select options={[{value:"contains",label:"содержит"},{value:"starts",label:"начинается с"}]} />
```

Передайте `options` (строки или `{value,label}`) ИЛИ собственные `<option>` через children.
