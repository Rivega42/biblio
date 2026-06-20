Вкладки (контролируемые). `underline` — для разделов карточки/ЛК; `pill` — для компактных переключателей.

```jsx
<Tabs value={tab} onChange={setTab}
  tabs={[{id:"loans",label:"Выдачи",count:3},{id:"orders",label:"Заказы",count:1},{id:"history",label:"История"}]} />
<Tabs variant="pill" value={view} onChange={setView}
  tabs={[{id:"list",label:"Список",icon:"list"},{id:"grid",label:"Галерея",icon:"grid"}]} />
```
