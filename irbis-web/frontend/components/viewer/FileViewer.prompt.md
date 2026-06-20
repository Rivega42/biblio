Просмотрщик файла/изображения — строго **view-only** (§1.7): нет скачивания и путей к файлу, контекстное меню по правой кнопке заблокировано, drag изображения отключён. PDF → подпись «документ pdf-формата» + постраничная навигация. Приоритет поля 955 над 951 выбирает вызывающая сторона.

```jsx
// файл выбираем по приоритету: 955 раньше 951
const file = [...record.files].sort((a,b)=>a.priority-b.priority)[0];
<FileViewer
  open={viewerOpen}
  file={file}
  canView={!file.requiresAuth || account.loggedIn}
  onClose={() => setViewerOpen(false)}
/>
```

- `canView=false` → состояние «нужен вход по билету».
- `kind`: "pdf" | "image" | "djvu".
