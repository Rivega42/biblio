Карточка результата — плотная и сканируемая. Универсальна: книжная строка или изобразительная (с превью), доп. поля из конфига базы.

```jsx
<ResultCard
  item={{title:"Чайка: комедия в четырёх действиях", author:"Чехов А. П.", year:"1896", docType:"Книга", availability:"available"}}
  checked={marked} onToggleCheck={toggle} onOpen={openRecord}
/>
// Изобразительная база:
<ResultCard showThumb typeIcon="image" item={{title:"Эскиз декорации", thumb:url, docType:"Эскиз", fields:[{label:"Техника", value:"Акварель"}]}} />
```
