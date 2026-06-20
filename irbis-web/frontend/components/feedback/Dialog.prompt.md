Модальное окно. ESC и клик по подложке закрывают. Используется для потока заказа.

```jsx
<Dialog open={open} onClose={close} title="Заказ издания" size="md"
  footer={<><Button variant="secondary" onClick={close}>Отмена</Button><Button onClick={confirm}>Подтвердить</Button></>}>
  …выбор экземпляра…
</Dialog>
```
