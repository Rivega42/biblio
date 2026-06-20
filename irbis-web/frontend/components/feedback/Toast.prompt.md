Всплывающие уведомления. `ToastViewport` рендерит стопку в правом нижнем углу.

```jsx
const [toasts, setToasts] = useState([]);
// push: setToasts(t => [...t, {id:Date.now(), variant:"success", title:"Заказ принят", message:"Экземпляр в очереди"}])
<ToastViewport toasts={toasts} onDismiss={id=>setToasts(t=>t.filter(x=>x.id!==id))} />
```
