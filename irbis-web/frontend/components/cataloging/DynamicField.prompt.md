«Главный» компонент каталогизации (§6): **тип поля определяет контрол**. Декларативное описание из профиля базы (FIELD_CATALOG) → нужный ввод. Повторяемые поля и подполя поддержаны; ФЛК через `error`.

```jsx
// меню .mnu
<DynamicField field={{ code:"900", label:"Вид документа", type:"menu",
  options:["Книга","Сборник","Многотомник"] }} value={v} onChange={setV} />

// словарь с автодополнением (префикс)
<DynamicField field={{ code:"700^a", label:"Автор", type:"dict",
  dictionary:[{term:"Чехов А. П.", count:318}] }} value={a} onChange={setA} />

// дерево .tre (ГРНТИ/УДК/ББК)
<DynamicField field={{ code:"606", label:"Рубрика ГРНТИ", type:"tree",
  tree:[{code:"18", label:"Искусство", children:[{code:"18.45", label:"Театр"}]}] }} value={r} onChange={setR} />

// повторяемое поле с подполями
<DynamicField field={{ code:"700", label:"Автор", type:"text", repeatable:true,
  subfields:[{code:"a", label:"Фамилия", type:"text"},{code:"b", label:"Инициалы", type:"text"}] }}
  value={authors} onChange={setAuthors} />
```

- `type`: `text | menu | dict | tree | bool | authority | date`.
- `value`: одиночное; для `repeatable` — массив вхождений; вхождение с подполями — объект `{ [code]: value }`.
- `error` рисует сообщение ФЛК под полем.
