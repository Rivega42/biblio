Таблица экземпляров (910): место хранения / инвентарный № / статус. На узких экранах — карточки. RFID и служебные id читателю не показываем.

```jsx
<HoldingsTable
  holdings={[
    {location:"Осн. фонд", inventory:"К-12345", status:"available"},
    {location:"Филиал №2", inventory:"К-12346", status:"issued"},
  ]}
  onOrder={(h)=>order(h)}
/>
```
