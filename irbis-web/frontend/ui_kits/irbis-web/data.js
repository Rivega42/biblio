/* ============================================================
   ИРБИС-Веб — мок-данные и КОНФИГ БАЗ (контракт §9 ТЗ v2).
   Экраны рендерятся ИЗ ЭТОЙ КОНФИГУРАЦИИ, а не из хардкода:
   добавление базы = добавление конфига, не переписывание экранов.
   Спецформы поиска (PLAY «Роли», TUAR «Дата события», GUAR Фонд/Опись)
   тоже описаны декларативно — поле `specialForm`.
   Все данные обезличены (152-ФЗ). Загружается как обычный <script>.
   ============================================================ */
(function () {
  // ---- Группы для иерархического селектора баз (§1.1) ----
  // Группа раскрывается тем же приёмом; у группы свой «выбрать все».
  const groups = {
    ek: { id: "ek", label: "Электронный каталог", icon: "book" },
    libretto: { id: "libretto", label: "Базы Либретто", icon: "music" },
  };

  // ---- Реестр баз (§3). group → принадлежность к раскрываемой группе ----
  const databases = [
    {
      id: "EK", group: "ek", name: "Электронный каталог", short: "Книги",
      icon: "book", description: "Книги — эталонная база", count: 214530,
      layout: "list", typeIcon: "book", simpleLabel: "Я ищу:",
      modes: ["simple", "advanced", "complex"],
      searchFields: [
        { code: "TI", label: "Заглавие" },
        { code: "AU", label: "Автор" },
        { code: "SUB", label: "Предметная рубрика" },
        { code: "KW", label: "Ключевые слова" },
        { code: "PY", label: "Год издания" },
      ],
      // Чекбокс «Только с электронными версиями» — простой режим ЭК (§4)
      simpleExtra: { id: "onlyDigital", label: "Только с электронными версиями" },
      filters: [
        { id: "doctype", label: "Вид документа", options: ["Книга", "Сборник", "Многотомник"] },
        { id: "lang", label: "Язык публикации", options: ["русский", "английский", "французский"] },
      ],
      // Навигаторы-классификаторы (§4) — ленивое дерево с количеством.
      navigators: [
        { id: "grnti", label: "ГРНТИ", tree: [
          { code: "18", label: "Искусство", count: 412, children: [
            { code: "18.45", label: "Театр. Театроведение", count: 230, children: [
              { code: "18.45.09", label: "Драматический театр", count: 142 },
              { code: "18.45.21", label: "Опера. Балет", count: 64 },
            ] },
            { code: "18.41", label: "Музыка", count: 96 },
          ] },
          { code: "17", label: "Литературоведение", count: 318, children: [
            { code: "17.82", label: "Художественная литература", count: 210, children: [
              { code: "17.82.31", label: "Драматургия", count: 88 },
            ] },
          ] },
        ] },
        { id: "udk", label: "УДК", tree: [
          { code: "792", label: "Театр", count: 256, children: [
            { code: "792.2", label: "Драматический театр", count: 130 },
            { code: "792.5", label: "Музыкальный театр", count: 58 },
          ] },
          { code: "82", label: "Литература", count: 402, children: [{ code: "82-2", label: "Драматургия", count: 91 }] },
        ] },
        { id: "bbk", label: "ББК", tree: [
          { code: "85.33", label: "Театр", count: 240, children: [{ code: "85.334", label: "Драматический театр", count: 128 }] },
          { code: "83.3", label: "История литературы", count: 176 },
        ] },
      ],
    },
    {
      id: "PERIO", group: "ek", name: "Периодические издания", short: "Периодика",
      icon: "newspaper", description: "Газеты и журналы", count: 18740,
      layout: "list", typeIcon: "newspaper", simpleLabel: "Я ищу:",
      modes: ["simple", "advanced"],
      searchFields: [
        { code: "TI", label: "Заглавие" }, { code: "KW", label: "Ключевые слова" }, { code: "PY", label: "Год" },
      ],
      filters: [{ id: "kind", label: "Вид", options: ["Журнал", "Газета", "Альманах"] }],
    },
    {
      id: "ARTICLES", group: "ek", name: "Статьи из книг и периодики", short: "Статьи",
      icon: "file-text", description: "Аналитическая роспись", count: 96210,
      layout: "list", typeIcon: "file-text", simpleLabel: "Я ищу:",
      modes: ["simple", "advanced"],
      searchFields: [
        { code: "TI", label: "Заглавие статьи" }, { code: "AU", label: "Автор" }, { code: "SRC", label: "Источник" },
      ],
      filters: [],
    },
    {
      id: "SKETCH", name: "Эскизный фонд", short: "Эскизы",
      icon: "images", description: "Изобразительные материалы · превью", count: 8412,
      layout: "gallery", typeIcon: "image", simpleLabel: "Я ищу:",
      modes: ["simple"],
      searchFields: [
        { code: "TI", label: "Название" }, { code: "AU", label: "Художник" },
        { code: "TECH", label: "Техника" }, { code: "PROD", label: "Постановка" },
      ],
      filters: [
        { id: "tech", label: "Техника", options: ["Акварель", "Карандаш", "Гуашь", "Тушь"] },
        { id: "type", label: "Тип", options: ["Эскиз декорации", "Эскиз костюма", "Афиша"] },
      ],
    },
    {
      id: "HPO", name: "Иллюстративные и историко-бытовые материалы", short: "Иллюстрации",
      icon: "images", description: "Фотографии, открытки, предметы", count: 12305,
      layout: "gallery", typeIcon: "image", simpleLabel: "Я ищу:", modes: ["simple"],
      searchFields: [{ code: "TI", label: "Название" }, { code: "KW", label: "Ключевые слова" }],
      filters: [], stub: true,
    },
    {
      id: "ABOUT", name: "Указатель литературы о СПб ГТБ", short: "О библиотеке",
      icon: "bookmark", description: "Публикации об учреждении", count: 642,
      layout: "list", typeIcon: "book", simpleLabel: "Я ищу:", modes: ["simple"],
      searchFields: [{ code: "TI", label: "Заглавие" }, { code: "AU", label: "Автор" }],
      filters: [], stub: true,
    },
    {
      id: "GUAR", name: "Собрание архивных документов", short: "Архив (GUAR)",
      icon: "archive", description: "Фонд / опись / даты", count: 31980,
      layout: "list", typeIcon: "file-text", simpleLabel: "Я ищу:", dateRange: true,
      modes: ["simple", "special"], specialTitle: "Поиск по архивным документам",
      searchFields: [
        { code: "TI", label: "Заголовок дела" }, { code: "FOND", label: "Фонд" }, { code: "OP", label: "Опись" },
      ],
      filters: [
        { id: "fond", label: "Фонд", options: ["Ф. 1 — Дирекция", "Ф. 2 — Цензура", "Ф. 7 — Труппа"] },
      ],
      // §4 GUAR — спецформа
      specialForm: [
        { kind: "text", id: "kw", label: "Ключевые слова" },
        { kind: "select", id: "allFonds", label: "Все фонды", options: ["— любой —", "Ф. 1 — Дирекция Императорских театров", "Ф. 2 — Драматическая цензура", "Ф. 7 — Труппа"] },
        { kind: "text", id: "fondName", label: "Название фонда" },
        { kind: "text", id: "fondNo", label: "Номер фонда" },
        { kind: "text", id: "opisNo", label: "Номер описи" },
        { kind: "text", id: "person", label: "Персоналия" },
        { kind: "text", id: "org", label: "Организация" },
        { kind: "range", id: "year", label: "Год создания", from: "с…", to: "по…" },
        { kind: "checkbox", id: "ecopy", label: "Электронная копия / полный текст" },
      ],
    },
    {
      id: "PLAY", name: "Аннотированный указатель пьес", short: "Пьесы",
      icon: "drama", description: "Пьесы, роли, жанры", count: 9874,
      layout: "list", typeIcon: "drama", simpleLabel: "Я ищу:",
      modes: ["simple", "special"], specialTitle: "Поиск пьес",
      searchFields: [{ code: "TI", label: "Заглавие" }, { code: "AU", label: "Автор" }, { code: "GEN", label: "Жанр" }],
      filters: [{ id: "genre", label: "Жанр", options: ["Комедия", "Драма", "Трагедия", "Водевиль"] }],
      // §4/§7.1 PLAY — спецформа с областью «Роли» (8 вертикальных полей)
      specialForm: [
        { kind: "text", id: "kw", label: "Ключевые слова" },
        { kind: "text", id: "persons", label: "Персоны" },
        { kind: "text", id: "titles", label: "Заглавия" },
        { kind: "text", id: "genres", label: "Жанры и темы (Тезаурус)" },
        { kind: "text", id: "timeW", label: "Время написания" },
        { kind: "text", id: "placeC", label: "Место создания" },
        { kind: "text", id: "lang", label: "Язык написания" },
        {
          kind: "roles", id: "roles", label: "Роли",
          fields: ["Женские", "Мужские", "Детские", "Куклы", "Животные", "Сказочные персонажи", "Без определения", "Эпизодические"],
        },
        { kind: "text", id: "acts", label: "Количество действий" },
        { kind: "text", id: "timeA", label: "Время действия" },
        { kind: "text", id: "placeA", label: "Место действия" },
      ],
    },
    {
      id: "TUAR", name: "Календарь премьер Петербургских театров", short: "Премьеры",
      icon: "calendar-star", description: "Театральные премьеры и события", count: 5621,
      layout: "list", typeIcon: "calendar", simpleLabel: "Я ищу:",
      modes: ["simple", "special"], specialTitle: "Поиск премьер и событий",
      searchFields: [{ code: "TI", label: "Спектакль" }, { code: "AU", label: "Автор пьесы" }, { code: "THE", label: "Театр" }],
      filters: [{ id: "genre", label: "Жанр", options: ["Драма", "Опера", "Балет", "Комедия"] }],
      // §4/§7.2 TUAR — спецформа с областью «Дата события» и «Библ. источник»
      specialForm: [
        { kind: "text", id: "kw", label: "Ключевые слова" },
        { kind: "text", id: "persons", label: "Персоны" },
        { kind: "text", id: "events", label: "Спектакли / события" },
        { kind: "dateEvent", id: "date", label: "Дата события" },
        { kind: "text", id: "troupe", label: "Коллектив" },
        { kind: "select", id: "etype", label: "Вид и тип события", options: ["— любой —", "Премьера", "Гастроль", "Бенефис", "Юбилей"] },
        { kind: "text", id: "roleP", label: "Роли в представлениях" },
        {
          kind: "sourceArea", id: "src", label: "Библиографический источник",
          fields: [{ id: "srcAuthor", label: "Автор источника" }, { id: "srcTitle", label: "Заглавие источника" }],
        },
        { kind: "checkbox", id: "ecopy", label: "Электронная копия программки" },
      ],
    },
    {
      id: "IMAGE", name: "Хронология театральной жизни 1800–1850", short: "Хронология",
      icon: "calendar", description: "Образы карточек · события", count: 4120,
      layout: "gallery", typeIcon: "image", simpleLabel: "Я ищу:",
      modes: ["simple", "special"], specialTitle: "Поиск по хронологии",
      searchFields: [{ code: "TI", label: "Событие / объект" }, { code: "KW", label: "Ключевые слова" }],
      filters: [],
      // §7.4 IMAGE — область «Дата события»
      specialForm: [
        { kind: "text", id: "kw", label: "Ключевые слова" },
        { kind: "dateEvent", id: "date", label: "Дата события" },
        { kind: "text", id: "obj", label: "Название события / объекта" },
        { kind: "text", id: "city", label: "Город" },
        { kind: "text", id: "country", label: "Страна" },
        { kind: "text", id: "persons", label: "Персоны" },
        { kind: "text", id: "troupe", label: "Коллектив" },
        {
          kind: "sourceArea", id: "src", label: "Библиографический источник",
          fields: [{ id: "srcAuthor", label: "Автор источника" }, { id: "srcTitle", label: "Заглавие источника" }],
        },
      ],
    },
    {
      id: "IMGZENZ", name: "Драматическая цензура", short: "Цензура",
      icon: "stamp", description: "Образы карточек · цензурные дела", count: 3380,
      layout: "gallery", typeIcon: "image", simpleLabel: "Я ищу:", modes: ["simple", "special"],
      specialTitle: "Поиск по драматической цензуре",
      searchFields: [{ code: "TI", label: "Заглавие" }, { code: "AU", label: "Автор" }],
      filters: [],
      specialForm: [
        { kind: "select", id: "sep", label: "Выбор разделителей", options: ["— все —", "По дате", "По цензору", "По театру"] },
        { kind: "text", id: "kw", label: "Ключевые слова" },
        { kind: "text", id: "author", label: "Автор" },
        { kind: "text", id: "title", label: "Заглавие" },
        { kind: "select", id: "lang", label: "Язык", options: ["— любой —", "русский", "французский", "немецкий"] },
      ],
    },
    {
      id: "IMGOPERA", group: "libretto", name: "Либретто опер, оперетт", short: "Либретто опер",
      icon: "music", description: "Образы карточек", count: 2140,
      layout: "gallery", typeIcon: "image", simpleLabel: "Я ищу:", modes: ["simple", "special"],
      specialTitle: "Поиск либретто опер",
      searchFields: [{ code: "TI", label: "Заглавие" }, { code: "AU", label: "Автор" }],
      filters: [], stub: true,
      specialForm: [
        { kind: "select", id: "sep", label: "Выбор разделителей", options: ["— все —", "По композитору", "По театру"] },
        { kind: "text", id: "kw", label: "Ключевые слова" },
        { kind: "text", id: "author", label: "Автор" },
        { kind: "text", id: "title", label: "Заглавие" },
      ],
    },
    {
      id: "IMGBALET", group: "libretto", name: "Либретто балетов", short: "Либретто балетов",
      icon: "music", description: "Образы карточек", count: 1560,
      layout: "gallery", typeIcon: "image", simpleLabel: "Я ищу:", modes: ["simple", "special"],
      specialTitle: "Поиск либретто балетов",
      searchFields: [{ code: "TI", label: "Заглавие" }, { code: "AU", label: "Автор" }],
      filters: [], stub: true,
      specialForm: [
        { kind: "text", id: "kw", label: "Ключевые слова" },
        { kind: "text", id: "author", label: "Автор" },
        { kind: "text", id: "title", label: "Заглавие" },
      ],
    },
  ];

  // ---- Подсказки словаря (автокомплит), по базам ----
  const dictionaries = {
    EK: [
      { term: "Чайка", count: 42 }, { term: "Чехов А. П.", count: 318 },
      { term: "Чайковский П. И.", count: 156 }, { term: "Чацкий", count: 11 },
    ],
    SKETCH: [
      { term: "Чайка — декорация", count: 7 }, { term: "Чистяков П. П.", count: 23 },
      { term: "Чёрное на белом", count: 4 },
    ],
    GUAR: [
      { term: "Чрезвычайная комиссия", count: 9 }, { term: "Часть репертуарная", count: 14 },
    ],
    TUAR: [{ term: "Чайка (1896)", count: 3 }, { term: "Чародейка", count: 2 }],
    PLAY: [{ term: "Чайка", count: 5 }, { term: "Чехов А. П.", count: 28 }],
  };

  // ---- Результаты поиска, по базам (обезличенные примеры) ----
  // У каждой записи sourceDb — для мультибазового поиска (§1.4).
  const results = {
    EK: [
      { mfn: 10567, title: "Чайка: комедия в четырёх действиях", author: "Чехов А. П.", year: "1896", docType: "Книга", availability: "available", hasDigital: true },
      { mfn: 10571, title: "Чайка и другие пьесы", author: "Чехов А. П.", year: "1980", docType: "Сборник", availability: "issued" },
      { mfn: 10588, title: "«Чайка» на сцене: режиссёрские прочтения", author: "Громова М. И.", year: "2014", docType: "Книга", availability: "available", hasDigital: true },
      { mfn: 10592, title: "Поэтика драмы Чехова", author: "Скафтымов А. П.", year: "1972", docType: "Книга", availability: "available" },
      { mfn: 10601, title: "Театр Чехова: комментарии", author: "Бердников Г. П.", year: "1981", docType: "Книга", availability: "unknown" },
      { mfn: 10610, title: "Чайка. Дядя Ваня. Три сестры. Вишнёвый сад", author: "Чехов А. П.", year: "2008", docType: "Сборник", availability: "available", hasDigital: true },
    ],
    SKETCH: [
      { mfn: 50012, title: "Эскиз декорации к спектаклю «Чайка», III акт", author: "Симов В. А.", year: "1898", docType: "Эскиз декорации", availability: "available", fields: [{ label: "Техника", value: "Акварель" }], tint: 18 },
      { mfn: 50018, title: "Эскиз костюма Нины Заречной", author: "Симов В. А.", year: "1898", docType: "Эскиз костюма", availability: "available", fields: [{ label: "Техника", value: "Гуашь" }], tint: 168 },
      { mfn: 50031, title: "Афиша премьеры «Чайки»", author: "—", year: "1898", docType: "Афиша", availability: "issued", fields: [{ label: "Техника", value: "Литография" }], tint: 38 },
      { mfn: 50044, title: "Эскиз декорации: усадебный сад", author: "Симов В. А.", year: "1898", docType: "Эскиз декорации", availability: "available", fields: [{ label: "Техника", value: "Акварель" }], tint: 128 },
      { mfn: 50051, title: "Эскиз грима для роли Тригорина", author: "Неизв.", year: "1898", docType: "Эскиз костюма", availability: "unknown", fields: [{ label: "Техника", value: "Карандаш" }], tint: 268 },
      { mfn: 50060, title: "Эскиз занавеса", author: "Симов В. А.", year: "1902", docType: "Эскиз декорации", availability: "available", fields: [{ label: "Техника", value: "Гуашь" }], tint: 318 },
    ],
    GUAR: [
      { mfn: 70003, title: "Дело о постановке пьесы «Чайка» в сезон 1898/99", author: "—", year: "1898–1899", docType: "Архивное дело", availability: "available", recLevel: "opis", fields: [{ label: "Фонд", value: "Ф. 1, оп. 2" }, { label: "Листов", value: "47" }] },
      { mfn: 70011, title: "Переписка дирекции о репертуаре", author: "—", year: "1897–1900", docType: "Архивное дело", availability: "available", recLevel: "opis", fields: [{ label: "Фонд", value: "Ф. 1, оп. 2" }, { label: "Листов", value: "112" }] },
      { mfn: 70025, title: "Цензурные разрешения на драматические сочинения", author: "—", year: "1895–1898", docType: "Архивное дело", availability: "issued", recLevel: "opis", fields: [{ label: "Фонд", value: "Ф. 2, оп. 1" }, { label: "Листов", value: "203" }] },
      { mfn: 70100, title: "Ф. 1 — Дирекция Императорских театров", author: "—", year: "1842–1917", docType: "Фонд", availability: "available", recLevel: "fond", fields: [{ label: "Описей", value: "6" }, { label: "Дел", value: "1 240" }] },
    ],
    TUAR: [
      { mfn: 90002, title: "«Чайка» — премьера", author: "Чехов А. П.", year: "17 декабря 1898", docType: "Премьера", availability: "available", fields: [{ label: "Театр", value: "Художественный театр" }, { label: "Жанр", value: "Драма" }] },
      { mfn: 90007, title: "«Чародейка» — премьера оперы", author: "Чайковский П. И.", year: "20 октября 1887", docType: "Премьера", availability: "available", fields: [{ label: "Театр", value: "Мариинский театр" }, { label: "Жанр", value: "Опера" }] },
    ],
    PLAY: [
      { mfn: 60001, title: "Чайка: комедия в четырёх действиях", author: "Чехов А. П.", year: "1896", docType: "Пьеса", availability: "available", fields: [{ label: "Жанр", value: "Комедия" }, { label: "Действий", value: "4" }] },
      { mfn: 60004, title: "Вишнёвый сад: комедия в четырёх действиях", author: "Чехов А. П.", year: "1904", docType: "Пьеса", availability: "available", fields: [{ label: "Жанр", value: "Комедия" }, { label: "Действий", value: "4" }] },
    ],
  };

  // ---- Полные карточки записей (по mfn) ----
  // files: §9 контракт (951/955, priority, viewOnly, requiresAuth, kind).
  // links: f488 (Фонд↔Опись GUAR), f390 (цветная ссылка на ЭК), f481 (связь).
  const records = {
    10567: {
      mfn: 10567, db: "EK", title: "Чайка: комедия в четырёх действиях", author: "Чехов А. П.",
      imprint: { publisher: "Типография А. С. Суворина", year: "1896" },
      badges: [{ variant: "accent", text: "Пьеса" }, { variant: "success", text: "Полный текст" }],
      pftHtml:
        '<p><b>Чехов, Антон Павлович</b> (1860–1904).</p>' +
        '<p>Чайка : комедия в четырёх действиях / А. П. Чехов. — Санкт-Петербург : Типография А. С. Суворина, 1896. — 84 с. ; 21 см.</p>' +
        '<dl><dt>Жанр</dt><dd>Драматургия. Комедия.</dd>' +
        '<dt>Язык</dt><dd>Русский</dd>' +
        '<dt>Первая постановка</dt><dd>Александринский театр, 17 октября 1896 г.</dd></dl>' +
        '<p>Премьера в Художественном театре (1898) принесла пьесе признание; чайка стала эмблемой театра.</p>',
      subjects: ["Русская драматургия", "Пьесы", "Чехов А. П.", "Театр"],
      links: { f390: { target: "PLAY", mfn: 60001, label: "Текст пьесы в указателе пьес" }, f481: [10610] },
      files: [
        { field: "955", label: "Электронная версия", kind: "pdf", viewOnly: true, requiresAuth: true, priority: 1, pages: 84 },
        { field: "951", label: "Полный текст", kind: "pdf", viewOnly: true, requiresAuth: false, priority: 2, pages: 84 },
      ],
      holdings: [
        { location: "Основной фонд", inventory: "К-12345", status: "available" },
        { location: "Отдел редкой книги", inventory: "РК-0087", status: "available" },
        { location: "Филиал №2", inventory: "К-12346", status: "issued" },
      ],
      sigla: [
        { code: "СПбГТБ", name: "СПб гос. театральная библиотека", count: 3, here: true },
        { code: "РНБ", name: "Российская национальная библиотека", count: 2 },
        { code: "БАН", name: "Библиотека Академии наук", count: 1 },
      ],
    },
    50012: {
      mfn: 50012, db: "SKETCH", title: "Эскиз декорации к спектаклю «Чайка», III акт", author: "Симов В. А.",
      imprint: { publisher: "—", year: "1898" }, tint: 18,
      badges: [{ variant: "accent", text: "Эскиз декорации" }],
      pftHtml:
        '<p><b>Симов, Виктор Андреевич</b> (1858–1935).</p>' +
        '<p>Эскиз декорации к спектаклю «Чайка», действие III. — 1898. — Бумага, акварель ; 32 × 47 см.</p>' +
        '<dl><dt>Техника</dt><dd>Бумага, акварель</dd>' +
        '<dt>Постановка</dt><dd>Московский Художественный театр, 1898</dd>' +
        '<dt>Размер</dt><dd>32 × 47 см</dd></dl>',
      subjects: ["Сценография", "Симов В. А.", "Чайка (постановка)"],
      files: [
        { field: "955", label: "Изображение эскиза", kind: "image", viewOnly: true, requiresAuth: false, priority: 1, tint: 18 },
      ],
      holdings: [{ location: "Эскизный фонд, папка 12", inventory: "Э-0451", status: "available" }],
    },
    70003: {
      mfn: 70003, db: "GUAR", title: "Дело о постановке пьесы «Чайка» в сезон 1898/99", author: "—",
      imprint: { publisher: "—", year: "1898–1899" }, recLevel: "opis",
      badges: [{ variant: "neutral", text: "Архивное дело" }],
      pftHtml:
        '<dl><dt>Фонд</dt><dd>Ф. 1 — Дирекция Императорских театров</dd>' +
        '<dt>Опись</dt><dd>оп. 2</dd><dt>Дело</dt><dd>№ 314</dd>' +
        '<dt>Крайние даты</dt><dd>1898 — 1899</dd><dt>Объём</dt><dd>47 листов</dd></dl>' +
        '<p>Переписка, сметы и распоряжения по постановке. Машинопись и рукопись.</p>',
      subjects: ["Дирекция театров", "Репертуар", "1898"],
      links: { f488: { label: "Перейти к фонду", mfn: 70100, level: "fond" } },
      files: [{ field: "951", label: "Опись дела", kind: "pdf", viewOnly: true, requiresAuth: false, priority: 1, pages: 12 }],
      holdings: [{ location: "Архивохранилище, ряд 4", inventory: "Ф1-оп2-314", status: "available" }],
    },
    70100: {
      mfn: 70100, db: "GUAR", title: "Ф. 1 — Дирекция Императорских театров", author: "—",
      imprint: { publisher: "—", year: "1842–1917" }, recLevel: "fond",
      badges: [{ variant: "neutral", text: "Фонд" }],
      pftHtml:
        '<dl><dt>Номер фонда</dt><dd>Ф. 1</dd><dt>Название</dt><dd>Дирекция Императорских театров</dd>' +
        '<dt>Крайние даты</dt><dd>1842 — 1917</dd><dt>Описей</dt><dd>6</dd><dt>Дел</dt><dd>1 240</dd></dl>' +
        '<p>Фонд объединяет делопроизводство дирекции: репертуар, труппа, постановки, цензурная переписка.</p>',
      subjects: ["Дирекция театров", "Архивный фонд"],
      links: { f488: { label: "К описи дел сезона 1898/99", mfn: 70003, level: "opis" } },
      files: [],
      holdings: [],
    },
    90002: {
      mfn: 90002, db: "TUAR", title: "«Чайка» — премьера", author: "Чехов А. П.",
      imprint: { publisher: "Художественный театр", year: "1898" },
      badges: [{ variant: "accent", text: "Драма" }],
      pftHtml:
        '<dl><dt>Спектакль</dt><dd>Чайка</dd><dt>Автор</dt><dd>А. П. Чехов</dd>' +
        '<dt>Театр</dt><dd>Московский Художественный театр</dd>' +
        '<dt>Дата премьеры</dt><dd>17 декабря 1898</dd>' +
        '<dt>Режиссёр</dt><dd>К. С. Станиславский, Вл. И. Немирович-Данченко</dd></dl>',
      subjects: ["Премьеры", "МХТ", "Чехов А. П."],
      links: { f390: { target: "PLAY", mfn: 60001, label: "Пьеса в указателе пьес" } },
      files: [{ field: "955", label: "Программка премьеры", kind: "image", viewOnly: true, requiresAuth: false, priority: 1, tint: 38 }],
      holdings: [],
    },
    60001: {
      mfn: 60001, db: "PLAY", title: "Чайка: комедия в четырёх действиях", author: "Чехов А. П.",
      imprint: { publisher: "—", year: "1896" },
      badges: [{ variant: "accent", text: "Комедия" }],
      pftHtml:
        '<dl><dt>Заглавие</dt><dd>Чайка</dd><dt>Автор</dt><dd>А. П. Чехов</dd>' +
        '<dt>Жанр</dt><dd>Комедия</dd><dt>Количество действий</dt><dd>4</dd>' +
        '<dt>Роли</dt><dd>женские — 3, мужские — 6, эпизодические — 4</dd>' +
        '<dt>Время действия</dt><dd>конец XIX века</dd></dl>',
      subjects: ["Русская драматургия", "Комедия", "Чехов А. П."],
      links: { f390: { target: "EK", mfn: 10567, label: "Издание в электронном каталоге" } },
      files: [{ field: "951", label: "Текст пьесы", kind: "pdf", viewOnly: true, requiresAuth: false, priority: 1, pages: 84 }],
      holdings: [{ location: "Читальный зал", inventory: "П-2210", status: "available" }],
    },
  };

  // ---- Личный кабинет (минимум ПДн, 152-ФЗ) ----
  const account = {
    ticket: "00012345", lastName: "Читатель", displayName: "И. О.",
    loans: [
      { title: "Чайка и другие пьесы", due: "01.07.2026", location: "Филиал №2", renewable: true },
      { title: "Поэтика драмы Чехова", due: "10.07.2026", location: "Основной фонд", renewable: true },
      { title: "Театр Чехова: комментарии", due: "24.06.2026", location: "Основной фонд", renewable: false, overdueSoon: true },
    ],
    orders: [],
    bookmarks: [
      { mfn: 10567, db: "EK", title: "Чайка: комедия в четырёх действиях", author: "Чехов А. П." },
      { mfn: 50012, db: "SKETCH", title: "Эскиз декорации к спектаклю «Чайка», III акт", author: "Симов В. А." },
    ],
    savedQueries: [
      { id: "q1", label: "Чехов А. П.", db: "Электронный каталог", fresh: 3 },
      { id: "q2", label: "эскиз костюма", db: "Эскизный фонд", fresh: 0 },
    ],
    notifications: [
      { id: "n1", icon: "clock", tone: "issued", title: "Скоро срок возврата", text: "«Театр Чехова: комментарии» — вернуть до 24.06.2026.", unread: true },
      { id: "n2", icon: "check-circle", tone: "available", title: "Заказ готов к выдаче", text: "«Чайка и другие пьесы» ждёт на бронеполке, Филиал №2.", unread: true },
      { id: "n3", icon: "bell", tone: "neutral", title: "Новое в постоянном запросе", text: "По запросу «Чехов А. П.» — 3 новые записи.", unread: false },
    ],
    fines: [
      { id: "f1", reason: "Просрочка возврата (5 дн.)", amount: 50, date: "18.06.2026" },
      { id: "f2", reason: "Просрочка возврата (2 дн.)", amount: 20, date: "11.06.2026" },
    ],
  };

  // ---- Сотрудник: гранты по доменам (ACCESS_MODEL §3) ----
  // Навигация собирается ПО ГРАНТАМ, а не по АРМам. Уровни: read/write/delete/admin.
  const staff = {
    displayName: "Сотрудник",
    role: "Каталогизатор-библиотекарь",
    // Гранты текущей учётки (демо: совмещает несколько доменов).
    grants: {
      catalog: "read",
      cataloging: "write",
      circulation: "write",
      acquisition: "read",
      inventory: "write",
      analytics: "read",
      admin: "none",
    },
    // Каталог задач по доменам — показываем только разрешённое.
    domains: [
      { id: "cataloging", label: "Каталогизация", icon: "edit", desc: "Рабочие листы, ФЛК, импорт", need: "write",
        tasks: [
          { id: "cat-new", label: "Новая запись", icon: "plus" },
          { id: "cat-list", label: "Поиск и правка", icon: "search" },
          { id: "cat-global", label: "Глобальная корректировка", icon: "sliders" },
          { id: "cat-import", label: "Импорт (copy-cataloging)", icon: "download" },
        ] },
      { id: "circulation", label: "Книговыдача", icon: "scan-line", desc: "Выдача, возврат, очередь, бронеполка", need: "write",
        tasks: [
          { id: "circ-issue", label: "Выдача / возврат", icon: "scan-line" },
          { id: "circ-queue", label: "Очередь заказов", icon: "clock", badge: 7 },
          { id: "circ-shelf", label: "Бронеполка", icon: "bookmark" },
          { id: "circ-debt", label: "Должники", icon: "alert-triangle", badge: 3 },
        ] },
      { id: "acquisition", label: "Комплектование", icon: "package", desc: "Заказ → поступление → КСУ → списание", need: "read",
        tasks: [
          { id: "acq-order", label: "Заказы поставщикам", icon: "package" },
          { id: "acq-ksu", label: "КСУ", icon: "file-text" },
        ] },
      { id: "inventory", label: "Инвентаризация", icon: "clipboard-check", desc: "Онлайн-сверка с ТСД/сканера", need: "write",
        tasks: [
          { id: "inv-session", label: "Сессия сверки (ТСД)", icon: "scan-line" },
          { id: "inv-report", label: "Отчёт расхождений", icon: "file-text" },
        ] },
      { id: "analytics", label: "Аналитика", icon: "bar-chart", desc: "BI-дашборды фонда и выдачи", need: "read",
        tasks: [
          { id: "an-dash", label: "Дашборд", icon: "bar-chart" },
        ] },
      { id: "admin", label: "Администрирование", icon: "shield", desc: "Учётки, гранты, аудит", need: "admin",
        tasks: [] },
    ],
    // Сводка рабочего стола
    summary: [
      { label: "Заказов в очереди", value: 7, icon: "clock", tone: "issued" },
      { label: "На бронеполке", value: 12, icon: "bookmark", tone: "available" },
      { label: "Должников", value: 3, icon: "alert-triangle", tone: "danger" },
      { label: "Черновиков записей", value: 4, icon: "edit", tone: "neutral" },
    ],
  };

  // ---- Профиль каталогизации (рабочий лист) для базы «Книги» ----
  // Источник по типам ввода — FIELD_CATALOG (демо-срез). Поля рендерит DynamicField.
  const catalogingProfiles = {
    EK: {
      db: "EK", dbName: "Электронный каталог (книги)",
      pages: [
        {
          id: "main", label: "Основное описание",
          fields: [
            { code: "200^a", label: "Заглавие", type: "text", required: true, placeholder: "Основное заглавие" },
            { code: "200^e", label: "Сведения, относящиеся к заглавию", type: "text", placeholder: "подзаголовочные данные" },
            { code: "700", label: "Первый автор", type: "text", repeatable: false,
              subfields: [
                { code: "a", label: "Фамилия", type: "dict", dictionary: [{ term: "Чехов А. П.", count: 318 }, { term: "Чайковский П. И.", count: 156 }] },
                { code: "b", label: "Инициалы", type: "text" },
                { code: "4", label: "Роль", type: "menu", options: ["Автор", "Редактор", "Переводчик", "Составитель"] },
              ] },
            { code: "701", label: "Прочие авторы", type: "text", repeatable: true,
              subfields: [
                { code: "a", label: "Фамилия", type: "dict", dictionary: [{ term: "Громова М. И." }, { term: "Скафтымов А. П." }] },
                { code: "b", label: "Инициалы", type: "text" },
              ] },
            { code: "900", label: "Вид документа", type: "menu", required: true, options: ["Книга", "Сборник", "Многотомник", "Продолжающееся издание"] },
            { code: "101^a", label: "Язык текста", type: "menu", options: ["rus — русский", "eng — английский", "fre — французский", "ger — немецкий"] },
          ],
        },
        {
          id: "imprint", label: "Выходные данные",
          fields: [
            { code: "210^a", label: "Место издания", type: "text", placeholder: "Санкт-Петербург" },
            { code: "210^c", label: "Издательство", type: "authority", authority: [{ term: "Типография А. С. Суворина", code: "PUB-014" }, { term: "Academia", code: "PUB-220" }] },
            { code: "210^d", label: "Год издания", type: "date", required: true, placeholder: "ГГГГ", hint: "Формат: 4 цифры года" },
            { code: "215^a", label: "Объём (с.)", type: "text", placeholder: "84 с." },
          ],
        },
        {
          id: "subjects", label: "Содержание и рубрики",
          fields: [
            { code: "606", label: "Рубрика ГРНТИ", type: "tree",
              tree: [
                { code: "18", label: "Искусство. Искусствоведение", children: [
                  { code: "18.45", label: "Театр. Театроведение", children: [
                    { code: "18.45.09", label: "Драматический театр" },
                    { code: "18.45.21", label: "Музыкальный театр. Опера. Балет" },
                  ] },
                  { code: "18.41", label: "Музыка" },
                ] },
                { code: "17", label: "Литература. Литературоведение", children: [
                  { code: "17.07", label: "Теория литературы" },
                  { code: "17.82", label: "Художественная литература", children: [{ code: "17.82.31", label: "Драматургия" }] },
                ] },
              ] },
            { code: "601", label: "Предметная рубрика", type: "authority", repeatable: true,
              authority: [{ term: "Русская драматургия", code: "AU-1042" }, { term: "Театр — История", code: "AU-2087" }, { term: "Пьесы", code: "AU-3310" }] },
            { code: "610", label: "Ключевые слова", type: "text", repeatable: true, placeholder: "термин" },
            { code: "330^a", label: "Аннотация", type: "text", placeholder: "краткое содержание" },
          ],
        },
        {
          id: "holdings", label: "Экземпляры",
          fields: [
            { code: "910", label: "Экземпляр", type: "text", repeatable: true,
              subfields: [
                { code: "a", label: "Статус", type: "menu", options: ["0 — доступен", "1 — выдан", "5 — в обработке"] },
                { code: "b", label: "Инв. номер", type: "text" },
                { code: "d", label: "Место хранения", type: "menu", options: ["Основной фонд", "Отдел редкой книги", "Филиал №2", "Читальный зал"] },
                { code: "e", label: "Полка / ячейка", type: "text" },
              ] },
            { code: "905", label: "Есть электронная версия", type: "bool", options: ["Да", "Нет"] },
          ],
        },
      ],
    },
  };

  // ---- Книговыдача / Инвентаризация / Аналитика (демо) ----
  const staffData = {
    // Карточка читателя при сканировании билета
    reader: {
      ticket: "00012345", display: "Читатель И. О.", category: "Студент", valid: "до 31.12.2026",
      onHand: 3, debt: 0, overdue: 1,
      items: [
        { title: "Чайка и другие пьесы", inv: "К-12346", due: "01.07.2026", status: "ok" },
        { title: "Поэтика драмы Чехова", inv: "К-19022", due: "10.07.2026", status: "ok" },
        { title: "Театр Чехова: комментарии", inv: "К-10711", due: "24.06.2026", status: "overdue" },
      ],
    },
    queue: [
      { ticket: "00012345", reader: "Читатель И. О.", title: "Чайка: комедия в четырёх действиях", inv: "К-12345", placed: "18.06", status: "ready", location: "Основной фонд" },
      { ticket: "00033120", reader: "Читатель А. С.", title: "Вишнёвый сад", inv: "К-22019", placed: "19.06", status: "queued", location: "Филиал №2" },
      { ticket: "00041255", reader: "Читатель М. П.", title: "Эскиз декорации к «Чайке»", inv: "Э-0451", placed: "19.06", status: "queued", location: "Эскизный фонд" },
    ],
    shelf: [
      { cell: "Б-01", title: "Чайка: комедия в четырёх действиях", reader: "Читатель И. О.", hold: "до 23.06" },
      { cell: "Б-02", title: "Три сестры", reader: "Читатель Н. К.", hold: "до 22.06" },
      { cell: "Б-05", title: "Дядя Ваня", reader: "Читатель Д. Е.", hold: "до 24.06" },
    ],
    // Инвентаризация — сессия сверки с ТСД
    inventory: {
      session: "ИНВ-2026-07", location: "Основной фонд, ряд 4", total: 1240, scanned: 0,
      expected: [
        { inv: "К-12345", title: "Чайка: комедия в четырёх действиях" },
        { inv: "К-12346", title: "Чайка и другие пьесы" },
        { inv: "К-10711", title: "Театр Чехова: комментарии" },
        { inv: "К-19022", title: "Поэтика драмы Чехова" },
        { inv: "К-22019", title: "Вишнёвый сад" },
        { inv: "К-30015", title: "Драматургия Серебряного века" },
      ],
    },
    // BI-дашборд
    dashboard: {
      kpis: [
        { label: "Выдач за месяц", value: "4 218", delta: "+8%", tone: "available" },
        { label: "Возвратов", value: "3 960", delta: "+5%", tone: "available" },
        { label: "Новых читателей", value: "112", delta: "+14%", tone: "available" },
        { label: "Просрочки", value: "37", delta: "−6%", tone: "issued" },
      ],
      monthly: [
        { m: "Янв", v: 60 }, { m: "Фев", v: 72 }, { m: "Мар", v: 95 },
        { m: "Апр", v: 88 }, { m: "Май", v: 76 }, { m: "Июн", v: 100 },
      ],
      topDb: [
        { label: "Электронный каталог", pct: 64 },
        { label: "Эскизный фонд", pct: 16 },
        { label: "Указатель пьес", pct: 11 },
        { label: "Архив (GUAR)", pct: 9 },
      ],
    },
  };

  // ---- Профили библиотек: у КАЖДОЙ свой скин (тема) + бренд (§9) ----
  // Конфигурируется декларативно: добавить библиотеку = добавить запись,
  // без правки кода. Текущая библиотека задаёт название в шапке и скин по умолчанию.
  const libraries = [
    {
      id: "spbgtb", theme: "theatrical",
      name: "Санкт-Петербургская государственная театральная библиотека",
      short: "Театральная библиотека", monogram: "ТБ",
      tagline: "электронный каталог", city: "Санкт-Петербург",
    },
    {
      id: "nauchka", theme: "azure",
      name: "Научная библиотека университета",
      short: "Научная библиотека", monogram: "НБ",
      tagline: "электронный каталог и базы данных", city: "—",
    },
    {
      id: "publichka", theme: "pine",
      name: "Центральная городская публичная библиотека",
      short: "Городская библиотека", monogram: "ГБ",
      tagline: "каталог и читательские сервисы", city: "—",
    },
    {
      id: "neutral", theme: "working",
      name: "Библиотечный электронный каталог",
      short: "Электронный каталог", monogram: "ЭК",
      tagline: "поиск по базам данных", city: "—",
    },
  ];

  window.IRBIS_DATA = { groups, databases, dictionaries, results, records, account, staff, catalogingProfiles, staffData, libraries };
})();
